from __future__ import annotations

from pathlib import Path
import json
import re

from langchain_core.documents import Document

BASE_DIR = Path(__file__).resolve().parents[3]
JSON_DIR = BASE_DIR / "data" / "interim" / "structured_json"

SKIP_SECTION_TYPES = {
    "references",
    "acknowledgements",
    "funding",
}

MIN_TEXT_LEN = 40


def normalize_space(text: str) -> str:
    return re.sub(r"\s+", " ", text).strip()


def find_all_json_files() -> list[Path]:
    files = sorted(JSON_DIR.rglob("*.json"))
    if not files:
        raise FileNotFoundError(f"No structured JSON files found under: {JSON_DIR}")
    return files


def category_from_source_pdf(source_pdf: str) -> str:
    p = Path(source_pdf)
    parts = p.parts
    if len(parts) >= 3 and parts[0] == "data" and parts[1] == "raw":
        return parts[2]
    return ""


def base_metadata(data: dict) -> dict:
    meta = data.get("metadata", {})

    authors = meta.get("authors", [])
    if isinstance(authors, list):
        authors_str = "; ".join(authors)
    else:
        authors_str = str(authors)

    keywords = meta.get("keywords", [])
    if isinstance(keywords, list):
        keywords_str = "; ".join(keywords)
    else:
        keywords_str = str(keywords)

    return {
        "paper_id": data.get("paper_id", ""),
        "title": meta.get("title", ""),
        "authors": authors_str,
        "year": meta.get("year", ""),
        "doi": meta.get("doi", ""),
        "keywords": keywords_str,
        "source_pdf": data.get("source_pdf", ""),
        "source_fulltext_tei": data.get("source_fulltext_tei", ""),
        "source_header_tei": data.get("source_header_tei", ""),
        "category": category_from_source_pdf(data.get("source_pdf", "")),
        "source_type": "structured_json",
    }


def make_abstract_document(data: dict) -> Document | None:
    meta = data.get("metadata", {})
    abstract = normalize_space(meta.get("abstract", ""))

    if len(abstract) < MIN_TEXT_LEN:
        return None

    metadata = {
        **base_metadata(data),
        "unit_type": "abstract",
        "section_id": "abstract",
        "section_title": "Abstract",
        "section_type": "abstract",
    }

    return Document(page_content=abstract, metadata=metadata)


def make_section_documents(data: dict) -> list[Document]:
    docs = []

    for section in data.get("sections", []):
        section_text = normalize_space(section.get("text", ""))
        section_type = section.get("section_type", "section")
        section_title = section.get("section_title", "")
        section_id = section.get("section_id", "")

        if section_type in SKIP_SECTION_TYPES:
            continue

        if len(section_text) < MIN_TEXT_LEN:
            continue

        metadata = {
            **base_metadata(data),
            "unit_type": "section",
            "section_id": section_id,
            "section_title": section_title,
            "section_type": section_type,
        }

        docs.append(Document(page_content=section_text, metadata=metadata))

    return docs


def load_one_json(json_path: Path) -> list[Document]:
    with json_path.open("r", encoding="utf-8") as f:
        data = json.load(f)

    docs = []

    abstract_doc = make_abstract_document(data)
    if abstract_doc is not None:
        docs.append(abstract_doc)

    docs.extend(make_section_documents(data))
    return docs


def load_structured_documents() -> list[Document]:
    all_docs = []

    for json_path in find_all_json_files():
        all_docs.extend(load_one_json(json_path))

    return all_docs


if __name__ == "__main__":
    docs = load_structured_documents()
    print(f"Loaded {len(docs)} structured documents")

    if docs:
        print("\nSample metadata:")
        print(docs[0].metadata)

        print("\nSample text preview:")
        print(docs[0].page_content[:500])