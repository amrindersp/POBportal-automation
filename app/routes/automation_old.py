from fastapi import APIRouter, HTTPException
from fastapi.responses import FileResponse
from pydantic import BaseModel
from datetime import datetime
import threading
import time
from pathlib import Path
from openpyxl import Workbook
import os

router = APIRouter(prefix="/automation", tags=["automation"])
print("AUTOMATION ROUTER LOADED FROM:", __file__)


# ==========================================================
# IN-MEMORY STORE (TEMPORARY, STABLE)
# ==========================================================
RUNS = {}
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
# BACKGROUND WORKER
# ==========================================================
def automation_worker(run_id: int, vessel: str):
    try:
        vessel_dir = BASE_DATA_DIR / vessel
        vessel_dir.mkdir(parents=True, exist_ok=True)

        steps = [
            ("MAIL_ATTACHMENTS", 20),
            ("POB_EXPORT", 40),
            ("EPECPOB_PROCESS", 70),
            ("COMPLETED", 100),
        ]

        for step, progress in steps:
            with RUN_LOCK:
                RUNS[run_id]["step"] = step
                RUNS[run_id]["progress"] = progress
                RUNS[run_id]["updated_at"] = datetime.utcnow()
            time.sleep(2)

        # --------------------------------------------------
        # CREATE REAL, OPENABLE EXCEL FILES
        # --------------------------------------------------
        files = []

        for idx in range(1, 3):
            wb = Workbook()
            ws = wb.active
            ws.title = "Data"

            ws.append(["Name", "Vessel", "Generated At"])
            ws.append(["Test User", vessel, datetime.utcnow().isoformat()])

            file_path = vessel_dir / f"{vessel}_output_{idx}.xlsx"
            wb.save(file_path)

            files.append({
                "id": idx,  # ✅ simple, clean file id
                "name": file_path.name,
                "path": str(file_path.resolve())
            })

        with RUN_LOCK:
            RUNS[run_id]["files"] = files
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
            "updated_at": datetime.utcnow()
        }

    thread = threading.Thread(
        target=automation_worker,
        args=(run_id, data.vessel),
        daemon=True
    )
    thread.start()

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
# DOWNLOAD FILE (FINAL & WORKING)
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
                raise HTTPException(
                    status_code=404,
                    detail="File missing on disk"
                )

            return FileResponse(
                path=f["path"],
                filename=f["name"],
                media_type=(
                    "application/vnd.openxmlformats-officedocument."
                    "spreadsheetml.sheet"
                )
            )

    raise HTTPException(status_code=404, detail="File not found")
