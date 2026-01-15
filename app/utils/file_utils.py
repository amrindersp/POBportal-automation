from pathlib import Path
from datetime import date
from app.config import DATA_DIR

def vessel_dir(vessel: str) -> Path:
    p = DATA_DIR / vessel
    p.mkdir(parents=True, exist_ok=True)
    return p

def today() -> str:
    return date.today().isoformat()

def filename(vessel: str, kind: str) -> str:
    m = {
        "MAIL_POB": f"{vessel}_{today()}_POB.xlsx",
        "PORTAL_POB": f"{vessel}_Portal_POB.xlsx",
        "DUMMY_RFM": "Dummy_RFM.xlsx",
        "MANIFEST": f"{vessel}_Manifest.xlsx",
        "DUMMY_RETURN": "Dummy_Return_Manifest.xlsx",
        "FINAL_RFM": f"{vessel}_RFM.xlsx",
        "FINAL_RETURN": f"{vessel}_Return_Manifest.xlsx",
    }
    return m[kind]
