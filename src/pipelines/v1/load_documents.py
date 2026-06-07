import sys
from pathlib import Path

import pandas as pd
from langchain_core.documents import Document

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))  # src/
from config import settings  # noqa: E402

# Paths come from config so a separate sample corpus can be built via
# NEURORAG_PROCESSED_DIR / NEURORAG_INTERIM_DIR.
METADATA_FILE = settings.interim_dir / "paper_metadata.csv"
PROCESSED_DIR = settings.processed_dir


def load_metadata(metadata_file: Path) -> pd.DataFrame:
    if not metadata_file.exists():
        raise SystemExit(
            f"Metadata file not found: {metadata_file}\n"
            "Run create_metadata.py first to generate it."
        )
    return pd.read_csv(metadata_file)


def resolve_text_path(relative_pdf_path: str) -> Path:
    # relative_pdf_path is relative to the raw corpus dir (see create_metadata),
    # mirroring the layout extract_pdfs.py writes under the processed dir.
    return PROCESSED_DIR / Path(relative_pdf_path).with_suffix(".txt")


def make_document(row: pd.Series) -> Document | None:
    text_path = resolve_text_path(row["relative_path"])
    if not text_path.exists():
        print(f"Missing text file: {text_path}")
        return None

    text = text_path.read_text(encoding="utf-8")

    return Document(
        page_content=text,
        metadata={
            "paper_id": Path(row["filename"]).stem,
            "filename": row["filename"],
            "relative_path": row["relative_path"],
            "text_path": str(text_path),
            "year": row["year"],
            "first_author": row["first_author"],
            "category": row["category"],
        },
    )


def load_papers() -> list[Document]:
    df = load_metadata(METADATA_FILE)
    docs = []
    for _, row in df.iterrows():
        doc = make_document(row)
        if doc is not None:
            docs.append(doc)
    return docs


if __name__ == "__main__":
    docs = load_papers()
    print(f"Loaded {len(docs)} documents")
    if docs:
        print(docs[0].metadata)
