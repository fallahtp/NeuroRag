from __future__ import annotations

from pathlib import Path

from langchain_community.vectorstores import FAISS
from langchain_text_splitters import RecursiveCharacterTextSplitter

try:
    from langchain_huggingface import HuggingFaceEmbeddings
except ImportError:
    from langchain_community.embeddings import HuggingFaceEmbeddings

from load_structured_documents import load_structured_documents

BASE_DIR = Path(__file__).resolve().parent.parent.parent
INDEX_DIR = BASE_DIR / "storage" / "faiss_index_v2_structured"

CHUNK_SIZE = 900
CHUNK_OVERLAP = 120
EMBEDDING_MODEL = "sentence-transformers/all-MiniLM-L6-v2"


def create_embeddings():
    return HuggingFaceEmbeddings(model_name=EMBEDDING_MODEL)


def enrich_document_text(doc):
    meta = doc.metadata

    title = meta.get("title", "")
    section_title = meta.get("section_title", "")
    section_type = meta.get("section_type", "")
    keywords = meta.get("keywords", "")
    year = meta.get("year", "")

    prefix_parts = []
    if title:
        prefix_parts.append(f"Title: {title}")
    if year:
        prefix_parts.append(f"Year: {year}")
    if section_title:
        prefix_parts.append(f"Section title: {section_title}")
    if section_type:
        prefix_parts.append(f"Section type: {section_type}")
    if keywords:
        prefix_parts.append(f"Keywords: {keywords}")

    prefix = "\n".join(prefix_parts).strip()
    if prefix:
        doc.page_content = f"{prefix}\n\n{doc.page_content}"

    return doc


def split_documents(docs):
    splitter = RecursiveCharacterTextSplitter(
        chunk_size=CHUNK_SIZE,
        chunk_overlap=CHUNK_OVERLAP,
        separators=["\n\n", "\n", ". ", " ", ""],
    )

    enriched_docs = [enrich_document_text(doc) for doc in docs]
    chunks = splitter.split_documents(enriched_docs)

    for i, chunk in enumerate(chunks, start=1):
        chunk.metadata["chunk_id"] = i
        chunk.metadata["chunk_chars"] = len(chunk.page_content)

    return chunks


def build_faiss_index(chunks):
    embeddings = create_embeddings()
    db = FAISS.from_documents(chunks, embeddings)
    INDEX_DIR.mkdir(parents=True, exist_ok=True)
    db.save_local(str(INDEX_DIR))
    return db


if __name__ == "__main__":
    docs = load_structured_documents()
    chunks = split_documents(docs)

    print(f"Structured documents: {len(docs)}")
    print(f"Chunks: {len(chunks)}")

    if docs:
        print("\nSample original metadata:")
        print(docs[0].metadata)

    if chunks:
        print("\nSample chunk metadata:")
        print(chunks[0].metadata)

        print("\nSample chunk preview:")
        print(chunks[0].page_content[:700])

    build_faiss_index(chunks)
    print(f"\nSaved structured index to: {INDEX_DIR}")