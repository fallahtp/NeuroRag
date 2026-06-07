from __future__ import annotations

import sys
from pathlib import Path

from langchain_text_splitters import RecursiveCharacterTextSplitter

try:
    from langchain_huggingface import HuggingFaceEmbeddings
except ImportError:
    from langchain_community.embeddings import HuggingFaceEmbeddings

# Make the v2 package directory and src/ importable regardless of the current
# working directory.
sys.path.insert(0, str(Path(__file__).resolve().parent))
sys.path.insert(0, str(Path(__file__).resolve().parents[2]))  # src/
from load_structured_documents import load_structured_documents
from vector_store import build_dense_index
from config import settings

BASE_DIR = Path(__file__).resolve().parents[3]
INDEX_DIR = settings.v2_index_dir

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


def build_index(chunks):
    """Build the structured dense index with the configured backend.

    FAISS by default; Qdrant when NEURORAG_VECTOR_STORE=qdrant is set.
    """
    embeddings = create_embeddings()
    return build_dense_index(chunks, embeddings, INDEX_DIR)


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

    from config import settings

    build_index(chunks)
    location = settings.qdrant_path if settings.vector_store == "qdrant" else INDEX_DIR
    print(f"\nSaved structured index ({settings.vector_store}) to: {location}")