import pandas as pd
from pathlib import Path
from datetime import datetime


def generate_outputs(vessel: str) -> list[Path]:
    """
    Generates INTERNAL Excel outputs:
    - FINAL_RFM
    - MANIFEST
    - FINAL_RETURN

    Returns list of generated file paths.
    """

    # ✅ Single source of truth for output location
    vdir = Path("data") / vessel
    vdir.mkdir(parents=True, exist_ok=True)

    generated_files: list[Path] = []

    outputs = {
        "FINAL_RFM": f"{vessel}_FINAL_RFM.xlsx",
        "MANIFEST": f"{vessel}_MANIFEST.xlsx",
        "FINAL_RETURN": f"{vessel}_FINAL_RETURN.xlsx",
    }

    for kind, fname in outputs.items():
        file_path = vdir / fname

        df = pd.DataFrame(
            {
                "Vessel": [vessel],
                "File_Type": [kind],
                "Status": ["Generated"],
                "Generated_At": [datetime.utcnow().isoformat()],
            }
        )

        # ✅ Force overwrite (safe & intentional)
        df.to_excel(file_path, index=False)

        # ✅ Verify file actually exists
        if not file_path.exists():
            raise RuntimeError(f"Failed to generate {file_path.name}")

        generated_files.append(file_path)

    # ✅ HARD GUARANTEE: must be exactly 3
    if len(generated_files) != 3:
        raise RuntimeError("Internal automation did not generate all outputs")

    return generated_files
