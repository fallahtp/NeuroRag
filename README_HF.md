---
title: NeuroRag
emoji: 🧠
colorFrom: indigo
colorTo: blue
sdk: streamlit
sdk_version: 1.57.0
app_file: app_space.py
pinned: false
license: mit
---

# NeuroRag — live demo

Local-first Retrieval-Augmented Generation over neuroscience literature, with
three retrieval pipelines (baseline → hybrid → reranked) and a real evaluation
harness. Pick a pipeline in the sidebar, ask a question, and see the grounded
answer alongside the retrieved sources and their ranking signals.

For this hosted demo, generation runs on Gemini (`NEURORAG_LLM_BACKEND=gemini`)
instead of a local Ollama model. Full code, README, and the case study:
https://github.com/fallahtp/NeuroRag

> **Deployment note:** the YAML front-matter above is what Hugging Face Spaces
> reads — copy it to the Space repo's `README.md`. The Space also needs the
> prebuilt sample indexes committed and `GEMINI_API_KEY` set as a secret. See
> `DEPLOY_DEMO.md` in the main repo for the full runbook.
