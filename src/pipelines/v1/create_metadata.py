from pathlib import Path
import re
import pandas as pd

BASE_DIR = Path(__file__).resolve().parents[3]
RAW_DIR = BASE_DIR / "data" / "raw"
OUT_FILE = BASE_DIR / "data" / "interim" / "paper_metadata.csv"

records = []

for pdf in RAW_DIR.rglob("*.pdf"):

    filename = pdf.name
    rel_path = pdf.relative_to(BASE_DIR)

    folder = pdf.parent.name

    stem = pdf.stem

    # Find a 4-digit year anywhere in the filename, not just the first token,
    # so both "2020_Smith_..." and "Smith_2020_..." are handled.
    year_match = re.search(r"(?:19|20)\d{2}", stem)
    year = year_match.group(0) if year_match else ""

    parts = [p for p in stem.split("_") if p and p != year]
    first_author = parts[0] if parts else ""

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