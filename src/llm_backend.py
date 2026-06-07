"""
Pluggable LLM text-generation backend for NeuroRag.

The retrieval pipelines call ``generate(prompt)`` instead of talking to a
specific provider directly, so the *same* pipeline can run:

  - locally on Ollama (default), or
  - on a hosted API such as Gemini for the public demo,

selected entirely by the ``NEURORAG_LLM_BACKEND`` environment variable
("ollama" or "gemini"). Provider client libraries are imported lazily inside
each helper, so a deployment that only uses one backend never needs the other
installed at call time.
"""

from __future__ import annotations

import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))  # src/
from config import settings  # noqa: E402


def generate(prompt: str, *, ollama_model: str | None = None) -> str:
    """Generate text for ``prompt`` using the configured backend.

    ``ollama_model`` lets a caller pin the local model (the v1 pipeline uses a
    smaller model than v2). It is ignored by non-Ollama backends, which use
    their own configured model name.
    """
    backend = settings.llm_backend
    if backend == "ollama":
        return _ollama_generate(prompt, ollama_model or settings.v2_ollama_model)
    if backend == "gemini":
        return _gemini_generate(prompt, settings.gemini_gen_model)
    raise ValueError(
        f"Unknown NEURORAG_LLM_BACKEND={backend!r}. Expected 'ollama' or 'gemini'."
    )


def _ollama_generate(prompt: str, model: str) -> str:
    import ollama

    response = ollama.chat(
        model=model,
        messages=[{"role": "user", "content": prompt}],
    )
    return response["message"]["content"]


def _gemini_generate(prompt: str, model: str) -> str:
    api_key = os.environ.get("GEMINI_API_KEY")
    if not api_key:
        raise RuntimeError(
            "NEURORAG_LLM_BACKEND=gemini but GEMINI_API_KEY is not set. "
            "Set it in your environment (or, on Hugging Face Spaces, as a secret)."
        )

    from google import genai

    client = genai.Client(api_key=api_key)
    response = client.models.generate_content(model=model, contents=prompt)
    return (response.text or "").strip()
