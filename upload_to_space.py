"""
One-shot uploader: push the NeuroRag demo to its Hugging Face Space.

Uploads code + the public sample corpus + prebuilt indexes, skips the private
corpus and local cruft, and sets the Space's README.md from README_HF.md (which
carries the Docker/Streamlit Space config). Large files (PDFs, FAISS indexes)
are handled automatically via the Hub — no manual git-LFS needed.

Usage (PowerShell), with a WRITE token from https://huggingface.co/settings/tokens:

    pip install -U huggingface_hub
    $env:HF_TOKEN = "hf_your_write_token"
    python upload_to_space.py
"""

import os
from pathlib import Path

from huggingface_hub import HfApi

REPO_ID = "fallahtp/NeuroRag"
ROOT = Path(__file__).resolve().parent

token = os.environ.get("HF_TOKEN")
if not token:
    raise SystemExit(
        'Set a write token first:  $env:HF_TOKEN = "hf_..."  '
        "(create one at https://huggingface.co/settings/tokens)"
    )

api = HfApi(token=token)

# Everything that must NOT be uploaded: the private corpus/indexes and local cruft.
IGNORE = [
    ".git/*", ".git*",
    ".venv/*", "venv/*",
    "__pycache__/*", "*/__pycache__/*", "*.pyc",
    ".pytest_cache/*", ".ruff_cache/*",
    "data/raw/*",                       # private PDFs
    "data/processed/*",                 # private extracted text
    "data/interim/*",                   # private TEI/JSON (NOT data/sample/interim)
    "storage/faiss_index/*",            # private v1 index
    "storage/faiss_index_v2_structured/*",  # private v2 index
    "storage/qdrant/*",
    "README.md",                        # Space README is set from README_HF.md below
    "upload_to_space.py",
]

print(f"Uploading to https://huggingface.co/spaces/{REPO_ID} …")
api.upload_folder(
    folder_path=str(ROOT),
    repo_id=REPO_ID,
    repo_type="space",
    commit_message="Deploy NeuroRag demo (code + sample corpus + prebuilt indexes)",
    ignore_patterns=IGNORE,
)

# Set the Space landing page / config from README_HF.md (Docker SDK, app_port).
api.upload_file(
    path_or_fileobj=str(ROOT / "README_HF.md"),
    path_in_repo="README.md",
    repo_id=REPO_ID,
    repo_type="space",
    commit_message="Set Space README (Docker SDK config)",
)

print(f"Done → https://huggingface.co/spaces/{REPO_ID}")
print("Next: add GEMINI_API_KEY as a Space secret, then it will build and go live.")
