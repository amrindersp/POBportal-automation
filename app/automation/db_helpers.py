from app.database import SessionLocal
from app.models import AutomationRun, AutomationFile


def create_run(user, vessel):
    db = SessionLocal()
    run = AutomationRun(
        user=user,
        vessel=vessel,
        step="INITIALIZED",
        status="RUNNING",
        progress=0
    )
    db.add(run)
    db.commit()
    db.refresh(run)
    db.close()
    return run.id


def update_run(run_id, **fields):
    db = SessionLocal()
    run = db.get(AutomationRun, run_id)
    if run:
        for k, v in fields.items():
            setattr(run, k, v)
        db.commit()
    db.close()


def add_files(run_id, files):
    db = SessionLocal()
    for f in files:
        db.add(AutomationFile(
            run_id=run_id,
            file_name=f["name"],
            file_path=f["path"]
        ))
    db.commit()
    db.close()
