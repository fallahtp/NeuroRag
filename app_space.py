"""
Hugging Face Spaces entry point for the public NeuroRag demo.

This wrapper bakes in the demo configuration so the Space needs only ONE secret
(GEMINI_API_KEY): it points the pipelines at the committed *sample* corpus and
indexes, and selects the hosted Gemini generation backend. Then it runs the
normal Streamlit app (app.py) unchanged.

Locally, none of this matters — run `streamlit run app.py` as usual. This file
is only referenced by the Space (see README_HF.md `app_file: app_space.py`).

`setdefault` is used throughout so an explicitly-set environment variable always
wins over these demo defaults.
"""

import os
import runpy
from pathlib import Path

ROOT = Path(__file__).resolve().parent

# Hosted generation for the demo (local stays on Ollama by default).
os.environ.setdefault("NEURORAG_LLM_BACKEND", "gemini")

# Point the pipelines at the committed sample corpus + indexes (absolute paths,
# so this is robust regardless of the Space's working directory).
os.environ.setdefault("NEURORAG_RAW_DIR", str(ROOT / "data" / "sample" / "raw"))
os.environ.setdefault("NEURORAG_INTERIM_DIR", str(ROOT / "data" / "sample" / "interim"))
os.environ.setdefault("NEURORAG_V1_INDEX_DIR", str(ROOT / "storage" / "sample" / "faiss_index"))
os.environ.setdefault(
    "NEURORAG_V2_INDEX_DIR", str(ROOT / "storage" / "sample" / "faiss_index_v2_structured")
)

# Run the real Streamlit app as if it were invoked directly.
runpy.run_path(str(ROOT / "app.py"), run_name="__main__")
