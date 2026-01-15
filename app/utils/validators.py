from pathlib import Path
import pandas as pd

def assert_file_ok(p: Path):
    if not p.exists():
        raise RuntimeError(f"Missing file: {p}")
    if p.stat().st_size < 1024:
        raise RuntimeError(f"Corrupt/small file: {p}")

def assert_excel_not_empty(p: Path):
    df = pd.read_excel(p)
    if df.empty:
        raise RuntimeError("Excel is empty")
