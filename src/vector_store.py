"""
Vector-store backend abstraction for the structured (v2/v3) index.

NeuroRag indexes embeddings in FAISS by default — zero setup, fully local.
Setting ``NEURORAG_VECTOR_STORE=qdrant`` switches the structured index to
Qdrant instead, a vector database recognised across production RAG stacks,
while still running locally: ``langchain-qdrant`` uses an embedded on-disk
Qdrant store, so no separate server or Docker container is required.

    build_dense_index(docs, embeddings, faiss_dir)  -> build + persist
    load_dense_index(embeddings, faiss_dir)         -> load for querying

Both functions branch on ``settings.vector_store``. FAISS stays the default,
so existing setups are unaffected. Install the optional dependencies before
selecting Qdrant::

    pip install -r requirements-optional.txt
"""

from __future__ import annotations

from pathlib import Path

from config import settings

QDRANT_COLLECTION = "neurorag_structured"


def _qdrant_store(embeddings, *, recreate: bool):
    """Open (or recreate) the embedded on-disk Qdrant collection."""
    from langchain_qdrant import QdrantVectorStore
    from qdrant_client import QdrantClient
    from qdrant_client.models import Distance, VectorParams

    settings.qdrant_path.mkdir(parents=True, exist_ok=True)
    client = QdrantClient(path=str(settings.qdrant_path))

    if recreate:
        if client.collection_exists(QDRANT_COLLECTION):
            client.delete_collection(QDRANT_COLLECTION)
        dim = len(embeddings.embed_query("dimension probe"))
        client.create_collection(
            collection_name=QDRANT_COLLECTION,
            vectors_config=VectorParams(size=dim, distance=Distance.COSINE),
        )

    return QdrantVectorStore(
        client=client,
        collection_name=QDRANT_COLLECTION,
        embedding=embeddings,
    )


def build_dense_index(docs, embeddings, faiss_dir: Path):
    """Build and persist the dense index using the configured backend."""
    if settings.vector_store == "qdrant":
        store = _qdrant_store(embeddings, recreate=True)
        store.add_documents(list(docs))
        return store

    from langchain_community.vectorstores import FAISS

    db = FAISS.from_documents(docs, embeddings)
    faiss_dir.mkdir(parents=True, exist_ok=True)
    db.save_local(str(faiss_dir))
    return db


def load_dense_index(embeddings, faiss_dir: Path):
    """Load the persisted dense index using the configured backend."""
    if settings.vector_store == "qdrant":
        return _qdrant_store(embeddings, recreate=False)

    from langchain_community.vectorstores import FAISS

    return FAISS.load_local(
        str(faiss_dir),
        embeddings,
        allow_dangerous_deserialization=True,
    )
