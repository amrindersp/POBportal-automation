import os
from app.db import get_job, update_job
from app.settings import DATA_DIR
from worker.automation import run_portal_automation

def run_job(job_id: str):
    job = get_job(job_id)
    if not job:
        return

    update_job(job_id, status="RUNNING")
    try:
        out1, out2 = run_portal_automation(
            job_id=job_id,
            upload1_path=job["upload1_path"],
            upload2_path=job["upload2_path"],
            col1=job["col1"],
            col2=job["col2"],
            vessel=job["vessel"],
        )
        update_job(job_id, status="COMPLETED", out1_path=out1, out2_path=out2)
    except Exception as e:
        update_job(job_id, status="FAILED", error=str(e))
        # Per your requirement: provide nothing on failure (so no partial outputs).
        raise
