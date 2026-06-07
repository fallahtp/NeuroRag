# Deploying a clickable NeuroRag demo (Hugging Face Spaces)

The goal: a single public URL a client can click and *try*, with no clone, no
Ollama, no Docker, no GROBID. This is the highest-ROI portfolio move — a working
link beats a README in every proposal.

## Why the current app can't be deployed as-is

`app.py` assumes three things a free public host doesn't have:

1. **Ollama running locally** with a 7B model — Spaces free tier (2 vCPU, 16 GB,
   no GPU) can't serve `qwen2.5:7b` at usable speed.
2. **Prebuilt FAISS indexes on disk** — these are git-ignored, so a fresh clone
   has nothing to retrieve from.
3. **A private PDF corpus + GROBID** — we can't (and shouldn't) ship private papers.

So a demo needs three changes. None are large.

## The three changes

### 1. Ship a tiny *public* sample corpus + prebuilt indexes

Pick **3–5 open-access papers** (e.g. PLOS / Frontiers / arXiv, CC-BY) in your
domain. Run your existing pipeline on them locally to produce:

- `data/sample/structured_json/` — the GROBID→JSON output (so the Space never runs
  GROBID)
- `storage/faiss_index/` and `storage/faiss_index_v2_structured/` — prebuilt indexes

Commit **only these sample artifacts** (add a `!data/sample/` / `!storage/` exception
to `.gitignore`). They contain no private data and let the Space retrieve immediately.
This also finally delivers the "small shareable sample corpus" already on your roadmap.

### 2. Make generation pluggable: Ollama (local) **or** a hosted API (demo)

Add a thin `generate(prompt) -> str` indirection so the LLM call is swappable by an
env var, e.g. `NEURORAG_LLM_BACKEND=ollama|gemini|hf`. On Spaces you'd set it to a
free hosted option:

- **Gemini `2.5-flash-lite`** — you already use Gemini for the judge; reuse the key.
  Generous free tier, fast.
- **Hugging Face Inference API** — native to Spaces, free tier for small models.

Local behaviour is unchanged when the env var is unset (defaults to Ollama). *This is
the one code change I'll implement for you once you pick the backend — it touches the
generation function in `chat_structured_ollama.py`.*

### 3. Add the Spaces config

A Space is just a git repo with a config header. Create `README_HF.md` (or set the
header on a Spaces-specific README) with front-matter:

```yaml
---
title: NeuroRag
emoji: 🧠
colorFrom: indigo
colorTo: blue
sdk: streamlit
app_file: app.py
pinned: false
---
```

And a slim `requirements-spaces.txt` (no Ollama, no GROBID, no Qdrant) — just
streamlit, langchain, faiss-cpu, sentence-transformers, rank-bm25, the cross-encoder
deps, and your chosen LLM client.

## Deploy steps (≈15 min once the three changes are in)

1. Create a free account at huggingface.co, then **New Space** → SDK **Streamlit**.
   *(Account creation is yours to do — I can't create accounts or log in for you.)*
2. Add the Space as a git remote and push (or upload via the web UI):
   ```bash
   git remote add space https://huggingface.co/spaces/<you>/NeuroRag
   git push space main
   ```
3. In the Space **Settings → Variables and secrets**, add your LLM key
   (e.g. `GEMINI_API_KEY`) as a **secret**, and set `NEURORAG_LLM_BACKEND=gemini`.
4. The Space builds and gives you a public URL. Put it at the top of your README,
   your Upwork profile, and every relevant proposal.

## What I can do next, on your say-so

- **Implement change #2** (the pluggable `generate()` backend) — the only code edit.
- **Write `requirements-spaces.txt`** and the Spaces README front-matter.
- **Add the `.gitignore` exceptions** for the sample corpus and indexes.
- Draft a short **"Try the live demo"** README section once the URL exists.

You handle: creating the HF account, choosing the 3–5 sample papers, and adding the
secret key (never share keys with me — set them yourself in the Space settings).
