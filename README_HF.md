---
title: NeuroRag
emoji: 🧠
colorFrom: indigo
colorTo: blue
sdk: docker
app_port: 8501
pinned: false
license: mit
short_description: Grounded, source-cited RAG over neuroscience literature
---

# NeuroRag — live demo

Local-first Retrieval-Augmented Generation over neuroscience literature, with
three retrieval pipelines (baseline → hybrid → reranked) and a measured
evaluation harness. Pick a pipeline in the sidebar, ask a question, and see the
grounded answer alongside the retrieved sources and their ranking signals.

This hosted demo runs over a small **public sample corpus** (5 open-access
papers on spiral ganglion neurons / auditory nerve modeling) and uses **Gemini**
for generation. Full code, the complete README, and the case study:
https://github.com/fallahtp/NeuroRag

> **Deployment note:** this file's YAML front-matter is the Space config (Docker
> SDK, Streamlit served on port 8501 via the repo `Dockerfile`). The Space needs
> `GEMINI_API_KEY` set as a secret. See `DEPLOY_DEMO.md` in the main repo.
