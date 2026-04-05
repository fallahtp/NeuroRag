from pathlib import Path
import pandas as pd

BASE_DIR = Path(__file__).resolve().parents[3]
RAW_DIR = BASE_DIR / "data" / "raw"
OUT_FILE = BASE_DIR / "data" / "interim" / "paper_metadata.csv"

records = []

for pdf in RAW_DIR.rglob("*.pdf"):

    filename = pdf.name
    rel_path = pdf.relative_to(BASE_DIR)

    folder = pdf.parent.name

    parts = pdf.stem.split("_")

    year = parts[0] if parts[0].isdigit() else ""
    first_author = parts[1] if len(parts) > 1 else ""

    records.append({
        "filename": filename,
        "relative_path": str(rel_path),
        "year": year,
        "first_author": first_author,
        "category": folder,
    })

df = pd.DataFrame(records)

OUT_FILE.parent.mkdir(parents=True, exist_ok=True)

df.to_csv(OUT_FILE, index=False)

print(f"Metadata file created: {OUT_FILE}")
print(f"Total papers: {len(df)}")