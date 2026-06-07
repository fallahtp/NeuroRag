import sys
from pathlib import Path

from pypdf import PdfReader

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))  # src/
from config import settings  # noqa: E402

# Corpus + output locations come from config so a separate sample corpus can be
# built via NEURORAG_RAW_DIR / NEURORAG_PROCESSED_DIR without touching a private
# corpus.
RAW_DIR = settings.raw_dir
OUT_DIR = settings.processed_dir

OUT_DIR.mkdir(parents=True, exist_ok=True)

pdfs = list(RAW_DIR.rglob("*.pdf"))

if not pdfs:
    raise SystemExit(f"No PDFs found in: {RAW_DIR}")

for pdf_path in pdfs:
    try:
        reader = PdfReader(str(pdf_path))
        parts = []

        for i, page in enumerate(reader.pages, start=1):
            text = page.extract_text() or ""
            parts.append(f"\n\n===== PAGE {i} =====\n{text}")

        # keep relative folder structure (relative to the raw corpus dir)
        rel_path = pdf_path.relative_to(RAW_DIR).with_suffix(".txt")
        out_path = OUT_DIR / rel_path
        out_path.parent.mkdir(parents=True, exist_ok=True)

        out_path.write_text("".join(parts), encoding="utf-8")
        print(f"Extracted: {pdf_path.name}")

    except Exception as e:
        print(f"Failed: {pdf_path.name} -> {e}")

print("Done.")
