from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent

DB_USER = "root"
DB_PASSWORD = "rootpass123"
DB_HOST = "localhost"
DB_NAME = "automation_db"

DATABASE_URL = f"mysql+pymysql://{DB_USER}:{DB_PASSWORD}@{DB_HOST}/{DB_NAME}"

HEADLESS = True
PLAYWRIGHT_TIMEOUT = 60_000

DATA_DIR = BASE_DIR / "data"
DATA_DIR.mkdir(exist_ok=True)
