import os, uuid, secrets, time
from fastapi import FastAPI, Request, UploadFile, File, Form, HTTPException
from fastapi.responses import HTMLResponse, FileResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates

from redis import Redis
from rq import Queue

from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.schedulers.base import STATE_RUNNING

from app.settings import DATA_DIR, REDIS_URL, APP_USERNAME, APP_PASSWORD
from app.vessels import VESSELS
from app.db import (
    init_db, create_job, get_job, get_job_by_token, delete_job_files_and_row
)
from app.excel_utils import read_headers


# -----------------------
# Config for Option C
# -----------------------
RETENTION_SECONDS = 6 * 3600     # keep files for 6 hours
CLEANUP_EVERY_MINUTES = 10       # run cleanup every 10 minutes


def redis_from_url(url: str) -> Redis:
    import urllib.parse
    u = urllib.parse.urlparse(url)
    db = int((u.path or "/0").replace("/", "") or "0")
    
    # Check if using SSL (rediss://)
    use_ssl = u.scheme == "rediss"
    
    return Redis(
        host=u.hostname or "localhost",
        port=u.port or 6379,
        db=db,
        password=u.password,
        ssl=use_ssl,
        ssl_cert_reqs=None if use_ssl else None,
        decode_responses=False
    )


def require_app_login(username: str, password: str):
    if username != APP_USERNAME or password != APP_PASSWORD:
        raise HTTPException(status_code=401, detail="Invalid app credentials")


def cleanup_old_jobs():
    """
    Delete job folders (and DB rows) older than RETENTION_SECONDS.
    Assumes each job has its own folder: DATA_DIR/<job_id>/
    """
    now = time.time()
    os.makedirs(DATA_DIR, exist_ok=True)

    for name in os.listdir(DATA_DIR):
        if name == "tmp":
            continue

        path = os.path.join(DATA_DIR, name)
        if not os.path.isdir(path):
            continue

        age = now - os.path.getmtime(path)
        if age > RETENTION_SECONDS:
            # Your existing helper should delete files + db row
            delete_job_files_and_row(name)


# -----------------------
# App setup
# -----------------------
app = FastAPI()
app.mount("/static", StaticFiles(directory="app/static"), name="static")
templates = Jinja2Templates(directory="app/templates")

init_db()
os.makedirs(DATA_DIR, exist_ok=True)

r = redis_from_url(REDIS_URL)
q = Queue("pob", connection=r)

scheduler = BackgroundScheduler()
scheduler.add_job(cleanup_old_jobs, trigger="interval", minutes=CLEANUP_EVERY_MINUTES)


@app.on_event("startup")
def on_startup():
    # Start scheduler once
    if scheduler.state != STATE_RUNNING:
        scheduler.start()


@app.on_event("shutdown")
def on_shutdown():
    # Clean shutdown
    if scheduler.state == STATE_RUNNING:
        scheduler.shutdown(wait=False)


# -----------------------
# Routes
# -----------------------
@app.get("/", response_class=HTMLResponse)
def index(request: Request):
    return templates.TemplateResponse("index.html", {"request": request, "vessels": VESSELS})


@app.post("/api/excel/headers")
async def api_headers(
    app_username: str = Form(...),
    app_password: str = Form(...),
    excel: UploadFile = File(...)
):
    require_app_login(app_username, app_password)

    job_dir = os.path.join(DATA_DIR, "tmp")
    os.makedirs(job_dir, exist_ok=True)
    tmp_path = os.path.join(job_dir, f"{uuid.uuid4()}_{excel.filename}")

    with open(tmp_path, "wb") as f:
        f.write(await excel.read())

    headers = read_headers(tmp_path)

    try:
        os.remove(tmp_path)
    except:
        pass

    return {"headers": headers}


@app.post("/api/jobs")
async def create_job_api(
    app_username: str = Form(...),
    app_password: str = Form(...),
    vessel: str = Form(...),
    col1: str = Form(...),
    col2: str = Form(...),
    excel1: UploadFile = File(...),
    excel2: UploadFile = File(...)
):
    require_app_login(app_username, app_password)

    if vessel not in VESSELS:
        raise HTTPException(status_code=400, detail="Invalid vessel")

    job_id = str(uuid.uuid4())
    token = secrets.token_urlsafe(24)

    job_dir = os.path.join(DATA_DIR, job_id)
    os.makedirs(job_dir, exist_ok=True)

    p1 = os.path.join(job_dir, f"return_manifest_{excel1.filename}")
    p2 = os.path.join(job_dir, f"rfm_{excel2.filename}")

    with open(p1, "wb") as f:
        f.write(await excel1.read())
    with open(p2, "wb") as f:
        f.write(await excel2.read())

    create_job(job_id, token, p1, p2, col1, col2, vessel)

    q.enqueue("worker.tasks.run_job", job_id, job_timeout=60 * 30)  # 30 min
    return {"job_id": job_id}


@app.get("/api/jobs/{job_id}")
def job_status(job_id: str, app_username: str, app_password: str):
    require_app_login(app_username, app_password)
    job = get_job(job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Not found")

    safe = {
        "job_id": job["job_id"],
        "status": job["status"],
        "error": job["error"],
        "has_outputs": bool(job.get("out1_path")) and bool(job.get("out2_path")),
        "download_token": job["token"] if job["status"] == "COMPLETED" else None
    }
    return safe


@app.get("/download/{token}/{which}")
def download(token: str, which: str, app_username: str, app_password: str):
    require_app_login(app_username, app_password)

    job = get_job_by_token(token)
    if not job or job["status"] != "COMPLETED":
        raise HTTPException(status_code=404, detail="Not ready")

    if which not in ("excel1", "excel2"):
        raise HTTPException(status_code=400, detail="Invalid file")

    path = job["out1_path"] if which == "excel1" else job["out2_path"]
    if not path or not os.path.exists(path):
        raise HTTPException(status_code=404, detail="Missing output")

    # IMPORTANT: Do NOT delete here. Option C cleanup will delete later.
    return FileResponse(
        path,
        filename=os.path.basename(path),
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    )
