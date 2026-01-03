import os, sqlite3, time
from app.settings import DATA_DIR

os.makedirs(DATA_DIR, exist_ok=True)
DB_PATH = os.path.join(DATA_DIR, "jobs.db")

def init_db():
    with sqlite3.connect(DB_PATH) as con:
        con.execute("""
        CREATE TABLE IF NOT EXISTS jobs (
          job_id TEXT PRIMARY KEY,
          token TEXT NOT NULL,
          status TEXT NOT NULL,
          created_at REAL NOT NULL,
          updated_at REAL NOT NULL,
          error TEXT,
          upload1_path TEXT NOT NULL,
          upload2_path TEXT NOT NULL,
          col1 TEXT NOT NULL,
          col2 TEXT NOT NULL,
          vessel TEXT NOT NULL,
          out1_path TEXT,
          out2_path TEXT
        )
        """)
        con.commit()

def create_job(job_id, token, upload1_path, upload2_path, col1, col2, vessel):
    now = time.time()
    with sqlite3.connect(DB_PATH) as con:
        con.execute("""
        INSERT INTO jobs(job_id, token, status, created_at, updated_at, error,
                         upload1_path, upload2_path, col1, col2, vessel, out1_path, out2_path)
        VALUES(?, ?, 'QUEUED', ?, ?, NULL, ?, ?, ?, ?, ?, NULL, NULL)
        """, (job_id, token, now, now, upload1_path, upload2_path, col1, col2, vessel))
        con.commit()

def update_job(job_id, status=None, error=None, out1_path=None, out2_path=None):
    now = time.time()
    fields, vals = ["updated_at=?"], [now]
    if status is not None:
        fields.append("status=?"); vals.append(status)
    if error is not None:
        fields.append("error=?"); vals.append(error)
    if out1_path is not None:
        fields.append("out1_path=?"); vals.append(out1_path)
    if out2_path is not None:
        fields.append("out2_path=?"); vals.append(out2_path)
    vals.append(job_id)
    with sqlite3.connect(DB_PATH) as con:
        con.execute(f"UPDATE jobs SET {', '.join(fields)} WHERE job_id=?", vals)
        con.commit()

def get_job(job_id):
    with sqlite3.connect(DB_PATH) as con:
        con.row_factory = sqlite3.Row
        row = con.execute("SELECT * FROM jobs WHERE job_id=?", (job_id,)).fetchone()
        return dict(row) if row else None

def get_job_by_token(token):
    with sqlite3.connect(DB_PATH) as con:
        con.row_factory = sqlite3.Row
        row = con.execute("SELECT * FROM jobs WHERE token=?", (token,)).fetchone()
        return dict(row) if row else None

def delete_job_files_and_row(job_id):
    job = get_job(job_id)
    if not job:
        return
    for key in ("upload1_path","upload2_path","out1_path","out2_path"):
        p = job.get(key)
        if p and os.path.exists(p):
            try: os.remove(p)
            except: pass
    with sqlite3.connect(DB_PATH) as con:
        con.execute("DELETE FROM jobs WHERE job_id=?", (job_id,))
        con.commit()
