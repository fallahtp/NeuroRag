from pathlib import Path
import re
import pandas as pd

BASE_DIR = Path(__file__).resolve().parents[3]
RAW_DIR = BASE_DIR / "data" / "raw"
OUT_FILE = BASE_DIR / "data" / "interim" / "paper_metadata.csv"


def parse_filename_metadata(stem: str) -> tuple[str, str]:
    """Extract ``(year, first_author)`` from a PDF filename stem.

    The year is the first 4-digit value found anywhere in the stem, so both
    ``2020_Smith_...`` and ``Smith_2020_...`` are handled. The first author is
    the first underscore-separated token that is not the year.
    """
    year_match = re.search(r"(?:19|20)\d{2}", stem)
    year = year_match.group(0) if year_match else ""
    parts = [p for p in stem.split("_") if p and p != year]
    first_author = parts[0] if parts else ""
    return year, first_author


def build_metadata(raw_dir: Path = RAW_DIR, base_dir: Path = BASE_DIR) -> pd.DataFrame:
    """Scan ``raw_dir`` for PDFs and return a metadata DataFrame."""
    records = []
    for pdf in raw_dir.rglob("*.pdf"):
        year, first_author = parse_filename_metadata(pdf.stem)
        records.append(
            {
                "filename": pdf.name,
                "relative_path": str(pdf.relative_to(base_dir)),
                "year": year,
                "first_author": first_author,
                "category": pdf.parent.name,
            }
        )
    return pd.DataFrame(records)


def main() -> None:
    df = build_metadata()
    OUT_FILE.parent.mkdir(parents=True, exist_ok=True)
    df.to_csv(OUT_FILE, index=False)
    print(f"Metadata file created: {OUT_FILE}")
    print(f"Total papers: {len(df)}")


if __name__ == "__main__":
    main()
