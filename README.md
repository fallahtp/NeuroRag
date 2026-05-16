# NeuroRag

[![CI](https://github.com/fallahtp/NeuroRag/actions/workflows/ci.yml/badge.svg)](https://github.com/fallahtp/NeuroRag/actions/workflows/ci.yml)
[![License: MIT](https://img.shields.io/badge/License-MIT-blue.svg)](LICENSE)

**NeuroRag** is a **local Retrieval-Augmented Generation (RAG) assistant** for **neuroscience research and computational modeling**.

It is designed for researchers who want to search and query their own scientific literature, notes, and technical documents **locally**, without sending files to external APIs.

The project currently contains three retrieval pipelines and a full evaluation harness:

- **v1 baseline:** a simple local PDF → FAISS RAG pipeline
- **v2 structured pipeline:** GROBID-parsed structured JSON with section-aware retrieval and hybrid (dense + BM25) search
- **v3 reranked pipeline:** v2 candidates rescored by a cross-encoder before the diversity cap
- **eval harness:** retrieval eval (Hit@k, MRR) and answer eval (fact recall, citation validity, citation grounding, numeric hallucination) — with strict substring scoring **and** LLM-as-judge scoring using Gemini 2.5 Flash

### Measured results (63-question benchmark)

| Setup                        | Fact recall (judge) | Citation grounding | Hallucinations |
|------------------------------|--------------------:|-------------------:|---------------:|
| phi3:mini + v2 hybrid        | 34.8%               | 33.4%              | 7              |
| qwen2.5:7b + v2 hybrid       | 33.8%               | 39.7%              | **0**          |
| **qwen2.5:7b + v3 reranked** | **38.7%**           | **43.7%**          | **0**          |

v3 cross-encoder reranking adds +5pp judge fact recall and +4pp citation grounding over v2.

---

## Quick Start

```bash
# 1. Clone and set up the environment
git clone https://github.com/fallahtp/NeuroRag.git
cd NeuroRag
python -m venv .venv
.venv\Scripts\activate          # Windows  (use: source .venv/bin/activate on macOS/Linux)
pip install -r requirements.txt

# 2. Install and start Ollama, then pull a model
ollama pull qwen2.5:7b-instruct

# 3. Add your PDFs to data/raw/, then build the v1 baseline index
python src/pipelines/v1/extract_pdfs.py
python src/pipelines/v1/create_metadata.py
python src/pipelines/v1/build_index.py

# 4. Launch the demo UI
streamlit run app.py
```

The v2/v3 structured pipelines additionally need a local GROBID container — see
[Running the v2 / v3 Structured Pipeline](#running-the-v2--v3-structured-pipeline)
and [Troubleshooting](#troubleshooting).

---

## Why NeuroRag?

Scientific work often involves:

- many PDFs and review papers
- method sections scattered across papers
- domain-specific terminology
- modeling details that are hard to re-find later
- code and documentation that need grounded retrieval

NeuroRag is intended to become a **personal AI research assistant** that helps with:

- literature lookup
- section-aware scientific QA
- neuroscience and ion channel questions
- computational modeling and NEURON-related workflows
- grounded answers from private local documents

---

## Project Status

NeuroRag has evolved from a **minimal local RAG baseline** through a **structured document retrieval prototype** into a **measured, benchmarked, reranked pipeline** with a real evaluation harness.

### Current state

#### v1 baseline
- PDF text extraction using `pypdf`
- metadata CSV generation
- loading documents into LangChain `Document` objects
- semantic chunking
- FAISS vector index
- retrieval smoke test
- local CLI chat with Ollama

#### v2 structured pipeline
- dual GROBID parsing (header TEI + fulltext TEI)
- TEI → structured JSON conversion
- section-aware and abstract-aware document loading
- structured FAISS index
- hybrid retrieval: dense (FAISS) + lexical (BM25) + Reciprocal Rank Fusion
- section-aware CLI chat with grounded source display

#### v3 reranked pipeline
- cross-encoder rerank stage (`cross-encoder/ms-marco-MiniLM-L-6-v2`)
- rerank applied to top-16 fused candidates *before* the per-paper diversity cap
- delivers measurable improvements on fact recall and citation grounding

#### Evaluation harness
- 63-question neuroscience benchmark (`benchmarks/answer_eval_questions.jsonl`)
- retrieval eval: paper-level + section-level Hit@k, MRR, weak-case analysis
- answer eval: fact recall (strict + LLM-judged), citation validity, citation grounding, numeric hallucination
- LLM judge using `gemini-2.5-flash` (different model family from any evaluated generator, mitigates self-judgment bias)
- on-disk judge cache (reruns are free)

### Current limitations
- metadata extraction is still imperfect for some older PDFs
- year extraction can be noisy in some cases
- scientific tables and figure captions are still lost in TEI flattening
- no web UI yet
- some questions remain at 0% fact recall because the right evidence isn't well represented in any current chunk (a chunking problem, not a ranking problem)

---

## Key Features

- **Local-first architecture** — All parsing, indexing, retrieval, and generation run locally
- **Private research corpus** — Your PDFs, extracted text, parsed XML, JSON, and indexes stay on your machine
- **Three-layer architecture** — baseline flat RAG, structured scientific-document RAG, and reranked retrieval
- **Scientific document parsing** — GROBID extracts structured content from papers
- **Section-aware retrieval** — Works with abstracts and structured sections, not just flat chunks
- **Hybrid retrieval** — Combines semantic + lexical signals via RRF
- **Cross-encoder reranking** — v3 pipeline rescores candidates with full query–document attention
- **Local LLM integration via Ollama**
- **Grounded answers with source IDs**
- **Real benchmark + evaluation harness** with strict and LLM-judged metrics

---

## Pipeline Overview

### v1 baseline pipeline

```text
Scientific PDFs
      │
      ▼
PDF Text Extraction
      │
      ▼
Metadata CSV
      │
      ▼
Document Loading
      │
      ▼
Chunking
      │
      ▼
Embeddings
      │
      ▼
FAISS
      │
      ▼
Retriever
      │
      ▼
Ollama
      │
      ▼
Answer with sources
```

### v2 structured pipeline

```text
Scientific PDFs
      │
      ▼
GROBID parsing
(header TEI + fulltext TEI)
      │
      ▼
Structured JSON per paper
      │
      ▼
Abstract/section-aware document loading
      │
      ▼
Chunking
      │
      ▼
Dense index (FAISS) + lexical retrieval (BM25)
      │
      ▼
Hybrid retrieval / fusion (RRF)
      │
      ▼
Per-paper diversity cap
      │
      ▼
Ollama
      │
      ▼
Grounded answer with section-aware sources
```

### v3 reranked pipeline

```text
... [v2 retrieval through hybrid fusion] ...
      │
      ▼
Cross-encoder rerank (top-16 fused candidates)
      │
      ▼
Per-paper diversity cap
      │
      ▼
Ollama
      │
      ▼
Grounded answer with reranked sources
```

---

## Evaluation

NeuroRag has two evaluation harnesses: a **retrieval eval** that measures whether the right paper and section reach the top of the candidate list, and an **answer eval** that measures whether the generated answer actually contains the right facts.

### Retrieval eval (63 questions)

We compare three retrieval pipelines on Hit@1 / Hit@3 / Hit@5 for both paper-level and section-level matching.

| Pipeline  | Paper Hit@1 | Paper Hit@5 | Section Hit@3 |
|-----------|------------:|------------:|--------------:|
| v1 dense  | 85.0%       | 90.0%       | 85.0%         |
| v2 dense  | 100.0%      | 100.0%      | 100.0%        |
| v2 hybrid | 100.0%      | 100.0%      | 95.0%         |

Full breakdown with per-question results and weak-case analysis: [`results/retrieval_eval_summary.md`](results/retrieval_eval_summary.md).

### Answer-quality eval (63 questions)

We score generated answers on four axes: fact recall, citation validity, citation grounding, and numeric hallucination. Fact recall is double-reported: a **strict substring matcher** (transparent but biased against paraphrase) and an **LLM-as-judge** using `gemini-2.5-flash` (a different model family from any generator we evaluate, to mitigate self-judgment bias).

| Setup                            | Fact recall (judge) | Citation grounding | Hallucinations |
|----------------------------------|--------------------:|-------------------:|---------------:|
| phi3:mini + v2 hybrid            | 34.8%               | 33.4%              | 7              |
| qwen2.5:7b + v2 hybrid           | 33.8%               | 39.7%              | **0**          |
| **qwen2.5:7b + v3 reranked**     | **38.7%**           | **43.7%**          | **0**          |

Three observations:

- **Strict substring matching systematically undercounts.** Strict scores all three setups in the 24–27% range; the judge restores ~10pp consistently across runs. This validated the need for the judge — the relative ordering was preserved, only the absolute scale changed.
- **v3 reranking adds +5pp on judge fact recall and +4pp on citation grounding.** Citation grounding has no LLM in the loop, so its improvement is the most trustworthy signal that v3 surfaces better evidence chunks.
- **qwen2.5 beats phi3 on honesty, not on fact recall.** The two models tie on fact recall under both metrics. They diverge sharply on numeric hallucination: phi3 invented unsupported numbers in 4 answers; qwen2.5 invented none. We chose qwen2.5 as the default generator from v2 onward.

Comparison docs:
- [`results/pipeline_comparison.md`](results/pipeline_comparison.md) — v2 hybrid vs v3 reranked head-to-head
- [`results/model_comparison.md`](results/model_comparison.md) — phi3:mini vs qwen2.5:7b head-to-head

### LLM-as-judge

We use `gemini-2.5-flash` to grade fact recall. For each question, the judge labels every expected fact as `present` / `partial` / `absent` against the answer, with a one-sentence rationale. Labels map to 1.0 / 0.5 / 0.0 and average to a per-question score.

The judge is cached on disk by `sha256(question_id + answer + sorted(facts))`, so reruns hit cache and pay zero API cost. Failures fall back to the strict matcher and are tagged `judge_failed=True` for audit.

Full eval implementation: [`src/eval/`](src/eval/).

---

## Repository Structure

```text
NeuroRag/
│
├── app.py                          # Streamlit demo UI
│
├── src/
│   ├── config.py                   # central config (NEURORAG_* env overrides)
│   ├── observability.py            # optional LangSmith tracing (no-op by default)
│   ├── vector_store.py             # FAISS / Qdrant backend switch
│   │
│   ├── pipelines/
│   │   ├── v1/                     # baseline flat RAG
│   │   │   ├── extract_pdfs.py
│   │   │   ├── create_metadata.py
│   │   │   ├── load_documents.py
│   │   │   ├── build_index.py
│   │   │   ├── test_retrieval.py
│   │   │   └── chat_ollama.py
│   │   │
│   │   ├── v2/                     # structured + hybrid RAG
│   │   │   ├── parsing/
│   │   │   │   ├── run_grobid.py
│   │   │   │   ├── run_grobid_dual.py
│   │   │   │   └── tei_to_json.py
│   │   │   ├── load_structured_documents.py
│   │   │   ├── build_structured_index.py
│   │   │   ├── test_structured_retrieval.py
│   │   │   ├── test_hybrid_retrieval.py
│   │   │   └── chat_structured_ollama.py
│   │   │
│   │   └── v3/                     # cross-encoder reranker
│   │       └── rerank.py
│   │
│   └── eval/                       # evaluation harnesses
│       ├── run_retrieval_eval.py
│       ├── run_answer_eval.py
│       ├── run_ragas_eval.py       # optional RAGAS metrics
│       ├── llm_judge.py
│       └── score_existing_runs.py
│
├── tests/                          # pytest suite (pure-logic unit tests)
├── conftest.py
├── .github/workflows/ci.yml        # ruff + pytest on every push / PR
│
├── benchmarks/
│   ├── retrieval_eval_questions.jsonl
│   └── answer_eval_questions.jsonl
│
├── results/                        # curated eval summaries (committed)
│   ├── retrieval_eval_summary.md
│   ├── pipeline_comparison.md
│   └── model_comparison.md
│
├── data/                           # ignored by git
│   └── raw/ processed/ interim/
│
├── storage/                        # ignored by git (FAISS / Qdrant indexes)
│
├── pyproject.toml                  # ruff + pytest config
├── requirements.txt                # core runtime dependencies
├── requirements-dev.txt            # + pytest, ruff
├── requirements-optional.txt       # + RAGAS, Qdrant, LangSmith
├── LICENSE
├── .gitignore
└── README.md
```

---

## v1 Baseline Components

### 1. PDF extraction

`src/pipelines/v1/extract_pdfs.py`

- reads PDFs from `data/raw/`
- extracts page text using `pypdf`
- writes `.txt` files into `data/processed/`

### 2. Metadata generation

`src/pipelines/v1/create_metadata.py`

Creates `data/interim/paper_metadata.csv` with baseline fields: filename, relative path, year, first author, category.

### 3. Flat document loading

`src/pipelines/v1/load_documents.py` — loads processed text plus metadata into LangChain documents.

### 4. Baseline index

`src/pipelines/v1/build_index.py`

- chunking with `RecursiveCharacterTextSplitter`
- embeddings with `sentence-transformers/all-MiniLM-L6-v2`
- FAISS storage in `storage/faiss_index/`

### 5. Retrieval smoke test

`src/pipelines/v1/test_retrieval.py`

### 6. Baseline chat

`src/pipelines/v1/chat_ollama.py` — simple local CLI RAG over the v1 index.

---

## v2 Structured Pipeline Components

### 1. GROBID parsing

- `src/pipelines/v2/parsing/run_grobid.py`
- `src/pipelines/v2/parsing/run_grobid_dual.py`

Produces fulltext TEI XML and header TEI XML under `data/interim/tei_xml/` and `data/interim/header_tei_xml/`.

### 2. TEI → JSON conversion

`src/pipelines/v2/parsing/tei_to_json.py`

Builds one structured JSON record per paper in `data/interim/structured_json/`, containing paper-level metadata, abstract, section-aware body content, and source paths.

### 3. Structured document loading

`src/pipelines/v2/load_structured_documents.py` — creates LangChain documents from abstracts and section-level text while preserving metadata (paper ID, title, year, DOI, keywords, section title, section type).

### 4. Structured index

`src/pipelines/v2/build_structured_index.py` — builds the FAISS index at `storage/faiss_index_v2_structured/`.

### 5. Structured retrieval inspection

- `src/pipelines/v2/test_structured_retrieval.py`
- `src/pipelines/v2/test_hybrid_retrieval.py`

### 6. Structured chat

`src/pipelines/v2/chat_structured_ollama.py` — uses FAISS dense + BM25 lexical retrieval, RRF fusion, section-aware source display, and local Ollama generation.

---

## v3 Reranked Pipeline Components

### Cross-encoder reranker

`src/pipelines/v3/rerank.py`

Wraps a `cross-encoder/ms-marco-MiniLM-L-6-v2` model with a lazy singleton loader. Used by both eval harnesses to rescore the top fused candidates before the diversity cap. Cross-encoders see the full (query, document) pair and routinely catch ordering mistakes a bi-encoder + BM25 fusion makes.

---

## Evaluation Components

### Retrieval eval

`src/eval/run_retrieval_eval.py` — runs all three retrieval pipelines on the benchmark and produces `results/retrieval_eval_summary.{json,md}`.

### Answer eval

`src/eval/run_answer_eval.py` — full retrieval + generation + scoring loop for one (pipeline, model) combination.

Flags:
- `--pipeline {v2_hybrid, v3_reranked}` — which retrieval pipeline to use
- `--model <name>` — Ollama model name
- `--limit N` — first N questions only (smoke test)
- `--output-basename <stem>` — override the auto-generated output filename

### LLM judge

- `src/eval/llm_judge.py` — Gemini-based per-fact judge with on-disk caching
- `src/eval/score_existing_runs.py` — adds judge scores to existing `answer_eval_summary_*.json` files

---

## Installation

Clone the repository:

```bash
git clone https://github.com/fallahtp/NeuroRag.git
cd NeuroRag
```

Create a virtual environment:

```bash
python -m venv .venv
```

Activate it on Windows:

```bash
.venv\Scripts\activate
```

Install dependencies:

```bash
pip install -r requirements.txt              # core runtime
pip install -r requirements-dev.txt          # + pytest and ruff (for development)
pip install -r requirements-optional.txt     # + RAGAS, Qdrant, LangSmith (optional integrations)
```

---

## Demo UI

A Streamlit chat interface is provided for interactive exploration:

```bash
streamlit run app.py
```

Pick a pipeline (v1 baseline / v2 hybrid / v3 reranked) in the sidebar, ask a
question, and the UI shows the grounded answer alongside the retrieved source
chunks and their ranking signals — so the quality progression across pipeline
versions is visible live. The UI needs the indexes built and a local Ollama
service running (see Quick Start).

---

## External Requirements

### Ollama

NeuroRag uses a local Ollama model for answer generation. Install Ollama and pull at least one model:

```bash
ollama pull qwen2.5:7b-instruct   # current default
ollama pull phi3:mini              # smaller fallback
```

### Docker + GROBID

The structured v2/v3 pipelines use GROBID through Docker.

- install Docker Desktop
- run a local GROBID container (port 8070)
- the parser sends PDFs to `http://localhost:8070`

### Gemini API (optional — LLM-as-judge eval only)

The answer-quality eval uses `gemini-2.5-flash` as the grader. This is **optional** — every other part of NeuroRag runs locally with Ollama. The judge is only needed if you want to reproduce the LLM-judged fact recall numbers.

- Get a free key at https://aistudio.google.com/apikey
- Set environment variable `GEMINI_API_KEY`
- `pip install google-genai`

The 189 judge calls needed to reproduce the full benchmark cost roughly $0.05–0.15 on the paid tier (Tier 1 free quota covers it; the free tier daily cap is too low for the full benchmark in one day). Cache makes reruns free.

---

## Running the v1 Pipeline

```bash
# 1. Put PDFs in data/raw/
# 2. Extract text
python src/pipelines/v1/extract_pdfs.py
# 3. Create metadata
python src/pipelines/v1/create_metadata.py
# 4. Build the baseline index
python src/pipelines/v1/build_index.py
# 5. Test retrieval
python src/pipelines/v1/test_retrieval.py
# 6. Start baseline chat
python src/pipelines/v1/chat_ollama.py
```

---

## Running the v2 / v3 Structured Pipeline

```bash
# 1. Start GROBID locally via Docker
# 2. Parse PDFs with GROBID
python src/pipelines/v2/parsing/run_grobid_dual.py
# 3. Convert TEI to structured JSON
python src/pipelines/v2/parsing/tei_to_json.py
# 4. Load structured documents
python src/pipelines/v2/load_structured_documents.py
# 5. Build structured index
python src/pipelines/v2/build_structured_index.py
# 6. Test structured retrieval
python src/pipelines/v2/test_structured_retrieval.py
python src/pipelines/v2/test_hybrid_retrieval.py
# 7. Start structured chat
python src/pipelines/v2/chat_structured_ollama.py
```

---

## Running the Evaluation

### Retrieval eval

```bash
python src/eval/run_retrieval_eval.py
# -> results/retrieval_eval_summary.{json,md}
```

### Answer eval (one pipeline, one model)

```bash
python src/eval/run_answer_eval.py --pipeline v2_hybrid --model qwen2.5:7b-instruct
python src/eval/run_answer_eval.py --pipeline v3_reranked --model qwen2.5:7b-instruct
# -> results/answer_eval_summary_{model}_{pipeline}_n{N}.{json,md}
```

### LLM-judge re-scoring

```bash
# Requires GEMINI_API_KEY env var
python src/eval/score_existing_runs.py results/answer_eval_summary_*.json
# -> results/answer_eval_summary_*_judged.{json,md}
```

---

## Configuration

Every tunable knob lives in [`src/config.py`](src/config.py) as a single
`Settings` dataclass — models, chunk sizes, retrieval `top-k` values, the
GROBID host, the vector-store backend and so on. Each can be overridden per-run
via a `NEURORAG_*` environment variable without editing source. Examples:

```bash
NEURORAG_V2_OLLAMA_MODEL=llama3.1:8b   python src/pipelines/v2/chat_structured_ollama.py
NEURORAG_TOP_K_FINAL=8                 python src/eval/run_answer_eval.py
GROBID_URL=http://192.168.1.50:8070    python src/pipelines/v2/parsing/run_grobid_dual.py
```

---

## Optional integrations

NeuroRag runs **fully locally with no hosted dependencies by default**. Three
optional integrations are available behind config/env flags for teams that use
them — install them first with `pip install -r requirements-optional.txt`.

### RAGAS evaluation

A second-opinion eval using the widely recognised RAGAS metrics (faithfulness,
answer relevancy, context precision/recall). It re-scores an existing
answer-eval run and — to stay local-first — uses the local Ollama model as the
judge and the local sentence-transformer for embeddings:

```bash
python src/eval/run_ragas_eval.py --limit 5     # quick smoke test
python src/eval/run_ragas_eval.py               # full run
```

### Qdrant vector-store backend

The structured (v2/v3) index can be backed by Qdrant — a vector database
recognised across production RAG stacks — instead of FAISS. It runs as an
embedded on-disk store, so it stays local with no server or container:

```bash
NEURORAG_VECTOR_STORE=qdrant python src/pipelines/v2/build_structured_index.py
NEURORAG_VECTOR_STORE=qdrant streamlit run app.py
```

FAISS remains the default; existing setups are unaffected.

### LangSmith tracing

Set `LANGSMITH_TRACING=true` and `LANGSMITH_API_KEY` to emit request traces
(per-stage latency, inputs/outputs) for the `run_query` / `ask_ollama` paths.
When the flag is unset the tracing decorator is a zero-overhead no-op — see
[`src/observability.py`](src/observability.py).

---

## Development & testing

```bash
pip install -r requirements-dev.txt
pytest          # unit tests for the pure retrieval / parsing / config logic
ruff check .    # lint
```

CI runs `ruff` and `pytest` on every push and pull request via
[`.github/workflows/ci.yml`](.github/workflows/ci.yml).

---

## Troubleshooting

| Symptom | Fix |
|---------|-----|
| `pip install` produces garbled output | Ensure you are on the current `requirements.txt` (UTF-8). |
| `Could not reach Ollama` | Start the Ollama service and `ollama pull` the configured model. |
| `Could not reach GROBID at ...` | Start the GROBID Docker container, or set `GROBID_URL` to the right host. |
| `Index not found` in the UI / chat | Build the indexes first (see Quick Start / Running the pipelines). |
| v1 scripts fail to import `load_documents` | Run them with the current code — imports now resolve from any working directory. |
| Qdrant `already accessed by another instance` | The embedded store allows one process at a time; stop other processes using it. |

---

## Data and Privacy

This repository does not include:

- private PDFs
- extracted text files
- TEI XML outputs
- structured JSON outputs
- FAISS vector indexes
- local virtual environments

These remain local and are excluded via `.gitignore`. The repo is kept private, lightweight, and easy to share publicly as a portfolio project.

---

## Why this project matters

NeuroRag is not meant to be just a generic "chat with PDFs" demo.

The goal is to build a domain-specific local research assistant for:

- neuroscience literature
- ion channel questions
- spiral ganglion neuron research
- computational modeling
- NEURON / Python-related workflows

The most important direction is not flashy UI, but **measurable retrieval quality, grounded answers, and trustworthiness in a scientific setting** — which is why the evaluation harness is treated as a first-class component, not an afterthought.

---

## Roadmap

### Done
- ✅ 63-question neuroscience evaluation set (retrieval + answer quality)
- ✅ Retrieval ranking via Reciprocal Rank Fusion (v2 hybrid)
- ✅ Cross-encoder reranking (v3 reranked)
- ✅ Answer-eval harness with strict + LLM-judged fact recall
- ✅ LLM-as-judge with `gemini-2.5-flash` (different model family from generators, on-disk cached)
- ✅ Model comparison: phi3:mini vs qwen2.5:7b-instruct
- ✅ Pipeline comparison: v2 hybrid vs v3 reranked
- ✅ Streamlit demo UI with live pipeline comparison
- ✅ Central configuration module with environment-variable overrides
- ✅ Unit-test suite and CI (ruff + pytest)
- ✅ Optional integrations: RAGAS metrics, Qdrant backend, LangSmith tracing

### Near-term
- Better section-aware chunking to lift the long tail of "retrieval is close but not exact" failures
- Scientific table / figure-caption extraction (currently lost in TEI flattening)
- Judge-based citation grounding (we persist retrieved chunk text in eval JSON; the infrastructure is there, we just need the grading prompt)

### Next phase
- Richer metadata-aware filtering (year ranges, authors, paper-level boolean filters)
- Domain-specific prompt modes for neuroscience / NEURON workflows
- Query reformulation for the questions where retrieval misses entirely
- A small shareable sample corpus so the demo runs on a fresh clone without sourcing PDFs

---

## Tech Stack

- Python
- LangChain
- FAISS (dense vector retrieval) — optional Qdrant backend
- HuggingFace sentence-transformer embeddings (`all-MiniLM-L6-v2`)
- BM25 / lexical retrieval (`rank_bm25` via LangChain)
- Cross-encoder reranker (`cross-encoder/ms-marco-MiniLM-L-6-v2`)
- Ollama (local LLM generation)
- Gemini API (LLM-as-judge, eval only)
- Streamlit (demo UI)
- pytest + ruff + GitHub Actions (tests, lint, CI)
- PyPDF
- GROBID
- Docker
- Optional integrations: RAGAS (eval metrics), Qdrant (vector DB), LangSmith (tracing)

---

## Author

**Mahdi Fallahtaherpazir**
PhD Researcher — Neuroscience
Medical University of Innsbruck

---

## License

MIT License
