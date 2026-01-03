import os
from dotenv import load_dotenv

load_dotenv()

APP_USERNAME = os.getenv("APP_USERNAME", "admin")
APP_PASSWORD = os.getenv("APP_PASSWORD", "password")

POB_USERNAME = os.getenv("POB_USERNAME", "")
POB_PASSWORD = os.getenv("POB_PASSWORD", "")

REDIS_URL = os.getenv("REDIS_URL", "redis://localhost:6379/0")
DATA_DIR = os.getenv("DATA_DIR", "/tmp/pob_jobs")

HEADLESS = os.getenv("HEADLESS", "true").lower() == "true"
