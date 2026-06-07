"""
Central configuration for NeuroRag.

Every tunable knob the pipelines and eval harnesses use lives here, so they
can be changed in one place or overridden per-run via environment variables
(all prefixed ``NEURORAG_``) without editing source.

Usage from any module under ``src/``::

    import sys
    from pathlib import Path
    sys.path.insert(0, str(Path(__file__).resolve().parents[N]))  # path to src/
    from config import settings

    model = settings.v2_ollama_model
"""

from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path

# Repository root: this file lives at <root>/src/config.py
BASE_DIR = Path(__file__).resolve().parents[1]


def _env_str(key: str, default: str) -> str:
    return os.environ.get(key, default)


def _env_int(key: str, default: int) -> int:
    raw = os.environ.get(key)
    if raw is None or raw.strip() == "":
        return default
    try:
        return int(raw)
    except ValueError:
        return default


def _env_path(key: str, default: Path) -> Path:
    raw = os.environ.get(key)
    return Path(raw).expanduser() if raw else default


@dataclass(frozen=True)
class Settings:
    """Resolved configuration. Instantiate once as ``settings`` below."""

    # --- Paths -------------------------------------------------------
    base_dir: Path = BASE_DIR
    data_dir: Path = BASE_DIR / "data"
    # Corpus + index locations are env-overridable so a separate sample corpus
    # (for the public demo) can be built without touching a private corpus.
    raw_dir: Path = _env_path("NEURORAG_RAW_DIR", BASE_DIR / "data" / "raw")
    processed_dir: Path = _env_path("NEURORAG_PROCESSED_DIR", BASE_DIR / "data" / "processed")
    interim_dir: Path = _env_path("NEURORAG_INTERIM_DIR", BASE_DIR / "data" / "interim")
    storage_dir: Path = BASE_DIR / "storage"
    v1_index_dir: Path = _env_path("NEURORAG_V1_INDEX_DIR", BASE_DIR / "storage" / "faiss_index")
    v2_index_dir: Path = _env_path(
        "NEURORAG_V2_INDEX_DIR", BASE_DIR / "storage" / "faiss_index_v2_structured"
    )

    # --- Models ------------------------------------------------------
    embedding_model: str = _env_str(
        "NEURORAG_EMBEDDING_MODEL", "sentence-transformers/all-MiniLM-L6-v2"
    )
    v1_ollama_model: str = _env_str("NEURORAG_V1_OLLAMA_MODEL", "phi3:mini")
    v2_ollama_model: str = _env_str("NEURORAG_V2_OLLAMA_MODEL", "qwen2.5:7b-instruct")
    reranker_model: str = _env_str(
        "NEURORAG_RERANKER_MODEL", "cross-encoder/ms-marco-MiniLM-L-6-v2"
    )
    judge_model: str = _env_str("NEURORAG_JUDGE_MODEL", "gemini-2.5-flash")

    # --- Generation backend ------------------------------------------
    # "ollama" (default, fully local) or "gemini" (hosted — used for the
    # public demo). When "gemini", set GEMINI_API_KEY; the generation model
    # is NEURORAG_GEMINI_GEN_MODEL (defaults to gemini-2.5-flash).
    llm_backend: str = _env_str("NEURORAG_LLM_BACKEND", "ollama").lower()
    gemini_gen_model: str = _env_str("NEURORAG_GEMINI_GEN_MODEL", "gemini-2.5-flash")

    # --- Chunking ----------------------------------------------------
    chunk_size: int = _env_int("NEURORAG_CHUNK_SIZE", 1000)
    chunk_overlap: int = _env_int("NEURORAG_CHUNK_OVERLAP", 200)

    # --- Retrieval ---------------------------------------------------
    top_k_fetch: int = _env_int("NEURORAG_TOP_K_FETCH", 12)
    top_k_final: int = _env_int("NEURORAG_TOP_K_FINAL", 6)
    max_chunks_per_paper: int = _env_int("NEURORAG_MAX_CHUNKS_PER_PAPER", 2)
    rrf_k: int = _env_int("NEURORAG_RRF_K", 60)
    # Number of top fused candidates the v3 cross-encoder rescores before
    # the per-paper diversity cap is applied.
    rerank_pool_size: int = _env_int("NEURORAG_RERANK_POOL_SIZE", 16)

    # --- Vector store ------------------------------------------------
    # "faiss" (default, zero setup) or "qdrant" (optional, recognised in
    # production stacks; runs as an embedded on-disk store, no server needed).
    vector_store: str = _env_str("NEURORAG_VECTOR_STORE", "faiss").lower()
    qdrant_path: Path = _env_path(
        "NEURORAG_QDRANT_PATH", BASE_DIR / "storage" / "qdrant"
    )

    # --- GROBID ------------------------------------------------------
    grobid_url: str = _env_str("GROBID_URL", "http://localhost:8070").rstrip("/")

    # --- LLM-as-judge ------------------------------------------------
    judge_cache_dir: Path = _env_path(
        "NEURORAG_JUDGE_CACHE_DIR", Path.home() / ".cache" / "neurorag_judge"
    )


settings = Settings()
