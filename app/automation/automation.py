from fastapi import APIRouter, HTTPException
from fastapi.responses import FileResponse
from pydantic import BaseModel
from datetime import datetime
import threading
import time
import os
from pathlib import Path

from app.automation.pob_automation import run_pob
from app.automation.internal_automation import generate_outputs

router = APIRouter(prefix="/automation", tags=["automation"])
print("AUTOMATION ROUTER LOADED FROM:", __file__)

# ==========================================================
# IN-MEMORY STATE
# ==========================================================
RUNS: dict[int, dict] = {}
RUN_COUNTER = 0
RUN_LOCK = threading.Lock()

BASE_DATA_DIR = Path("data")
BASE_DATA_DIR.mkdir(exist_ok=True)


# ==========================================================
# REQUEST SCHEMA
# ==========================================================
class AutomationStartRequest(BaseModel):
    mail_username: str
    mail_password: str
    pob_username: str
    pob_password: str
    email_id: str
    vessel: str


# ==========================================================
# BACKGROUND WORKER (PRIMITIVES ONLY)
# ==========================================================
def automation_worker(
    run_id: int,
    vessel: str,
    pob_username: str,
    pob_password: str,
):
    vessel_dir = BASE_DATA_DIR / vessel
    vessel_dir.mkdir(parents=True, exist_ok=True)

    try:
        # ---------------- MAIL STEP ----------------
        with RUN_LOCK:
            RUNS[run_id]["step"] = "MAIL_ATTACHMENTS"
            RUNS[run_id]["progress"] = 20
            RUNS[run_id]["status"] = "RUNNING"
            RUNS[run_id]["updated_at"] = datetime.utcnow()

        time.sleep(1)

        # ---------------- POB STEP ----------------
        with RUN_LOCK:
            RUNS[run_id]["step"] = "POB_EXPORT"
            RUNS[run_id]["progress"] = 40
            RUNS[run_id]["updated_at"] = datetime.utcnow()

        ok, msg = run_pob({
            "pob_username": pob_username,
            "pob_password": pob_password,
            "vessel": vessel,
            "output_dir": str(vessel_dir),
        })

        if not ok:
            raise RuntimeError(msg)

        # ---------------- INTERNAL PROCESS ----------------
        with RUN_LOCK:
            RUNS[run_id]["step"] = "INTERNAL_PROCESS"
            RUNS[run_id]["progress"] = 70
            RUNS[run_id]["updated_at"] = datetime.utcnow()

        files = generate_outputs(vessel)

        if len(files) != 3:
            raise RuntimeError(f"Expected 3 internal files, got {len(files)}")

        with RUN_LOCK:
            RUNS[run_id]["files"] = [
                {
                    "id": i,
                    "name": f.name,
                    "path": str(f.resolve()),
                }
                for i, f in enumerate(files, start=1)
            ]

        # ---------------- COMPLETED ----------------
        with RUN_LOCK:
            RUNS[run_id]["step"] = "COMPLETED"
            RUNS[run_id]["progress"] = 100
            RUNS[run_id]["status"] = "SUCCESS"
            RUNS[run_id]["updated_at"] = datetime.utcnow()

    except Exception as e:
        with RUN_LOCK:
            RUNS[run_id]["status"] = "FAILED"
            RUNS[run_id]["error"] = str(e)
            RUNS[run_id]["updated_at"] = datetime.utcnow()


# ==========================================================
# START AUTOMATION
# ==========================================================
@router.post("/start")
def start_automation(data: AutomationStartRequest):
    global RUN_COUNTER

    with RUN_LOCK:
        RUN_COUNTER += 1
        run_id = RUN_COUNTER

        RUNS[run_id] = {
            "run_id": run_id,
            "user": data.mail_username,
            "vessel": data.vessel,
            "step": "INITIALIZED",
            "status": "RUNNING",
            "progress": 0,
            "error": None,
            "files": [],
            "created_at": datetime.utcnow(),
            "updated_at": datetime.utcnow(),
        }

    # ✅ PASS ONLY PRIMITIVES
    threading.Thread(
        target=automation_worker,
        args=(
            run_id,
            data.vessel,
            data.pob_username,
            data.pob_password,
        ),
        daemon=True,
    ).start()

    return {"run_id": run_id}


# ==========================================================
# STATUS
# ==========================================================
@router.get("/status/{run_id}")
def get_status(run_id: int):
    with RUN_LOCK:
        run = RUNS.get(run_id)

    if not run:
        raise HTTPException(status_code=404, detail="Run not found")

    return run


# ==========================================================
# DOWNLOAD
# ==========================================================
@router.get("/download/{run_id}/{file_id}")
def download_file(run_id: int, file_id: int):
    with RUN_LOCK:
        run = RUNS.get(run_id)

    if not run:
        raise HTTPException(status_code=404, detail="Run not found")

    for f in run["files"]:
        if f["id"] == file_id:
            if not os.path.exists(f["path"]):
                raise HTTPException(status_code=404, detail="File missing")

            return FileResponse(
                path=f["path"],
                filename=f["name"],
                media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            )

    raise HTTPException(status_code=404, detail="File not found")
