# NeuroRag

**NeuroRag** is a local Retrieval-Augmented Generation (RAG) assistant for neuroscience research and computational modeling. It is designed for researchers who want to search and query their own scientific literature locally, without sending files to external APIs.

> **Goal:** A personal AI research assistant grounded in private, domain-specific literature — built for neuroscience, ion channel research, spiral ganglion neuron modeling, and NEURON/Python workflows.

---

## Key Features

- **Local-first** — all parsing, indexing, retrieval, and generation run on your machine
- **Private corpus** — your PDFs, extracted text, parsed XML, and indexes never leave your computer
- **Three pipeline generations** — a flat baseline (v1), a structured section-aware pipeline (v2), and a cross-encoder reranked pipeline (v3)
- **Hybrid retrieval** — dense semantic search (FAISS) combined with lexical search (BM25) and RRF fusion
- **Cross-encoder reranking** — v3 adds a learned `(query, document)` relevance model on top of hybrid retrieval
- **Section-aware retrieval** — v2 and v3 work at the level of abstract, results, methods, and discussion sections, not just flat chunks
- **Grounded answers** — responses cite source IDs from retrieved context; the LLM is instructed not to fabricate
- **Evaluated** — a 63-question domain benchmark across 15 papers tracks paper-level and section-level retrieval quality across all pipelines

---

## Retrieval Benchmark Results

Evaluated on **63 questions across 15 papers** covering spiral ganglion neuron morphometry and ultrastructure, HCN channel expression and biophysics, cochlear implant FEM modeling, and NEURON simulation frameworks.

| Pipeline | Paper Hit@1 | Paper Hit@3 | Paper Hit@5 | Paper MRR | Section Hit@3 | Section Hit@5 |
|---|---:|---:|---:|---:|---:|---:|
| v1 baseline    | 82.5%      | 92.1%      | 92.1%       | 0.865     | 66.7%      | 73.0%      |
| v2 dense       | 90.5%      | 95.2%      | 96.8%       | 0.926     | 81.0%      | 88.9%      |
| v2 hybrid      | 88.9%      | 96.8%      | 98.4%       | 0.927     | 71.4%      | 74.6%      |
| **v3 reranked**| **95.2%**  | **98.4%**  | **100.0%**  | **0.971** | **85.7%**  | 87.3%      |

### Findings

**v3 reranking is the strongest pipeline overall.** It improves Paper Hit@1 by 4.8 pp over v2 dense and reaches 100% Paper Hit@5 — meaning the correct paper appears in the top-5 results for every benchmark question. Across all 63 questions, v3 produces a strictly better paper rank than v2 dense in 5 cases, a worse rank in 2, and a tied rank in 56.

**Hybrid retrieval is not strictly an upgrade.** v2 hybrid (BM25 + FAISS via RRF fusion) improves over v2 dense on Paper Hit@5 but **degrades Section Hit@3 from 81.0% to 71.4%** — adding lexical retrieval surfaces wrong-section chunks more often than dense retrieval alone. Only the cross-encoder reranker recovers section-level accuracy: v3 lifts Section Hit@3 to 85.7%, +14.3 pp above v2 hybrid.

This means the cross-encoder reranker isn't merely additive on top of hybrid retrieval — it's what makes hybrid retrieval safe.

---

## Architecture Overview

### v1 — Flat Baseline Pipeline

```
PDFs → pypdf extraction → metadata CSV → LangChain Documents
     → RecursiveCharacterTextSplitter → sentence-transformer embeddings
     → FAISS index → similarity search → Ollama (phi3:mini) → answer
```

### v2 — Structured Pipeline

```
PDFs → GROBID (header + fulltext TEI XML) → structured JSON per paper
     → abstract + section-aware document loading
     → metadata-enriched chunking → FAISS dense index
     → hybrid retrieval: FAISS + BM25 + RRF fusion
     → evidence sentence selection → Ollama (phi3:mini) → grounded answer
```

### v3 — Reranked Pipeline

```
query → v2 hybrid retrieval (FAISS + BM25 + RRF fusion) → top-N candidate pool
     → cross-encoder rerank (ms-marco-MiniLM-L-6-v2)
     → per-paper diversity cap → final top-K
```

---

## Repository Structure

```
NeuroRag/
│
├── src/
│   ├── pipelines/
│   │   ├── v1/                        # Flat baseline pipeline
│   │   │   ├── extract_pdfs.py
│   │   │   ├── create_metadata.py
│   │   │   ├── load_documents.py
│   │   │   ├── build_index.py
│   │   │   ├── test_retrieval.py
│   │   │   └── chat_ollama.py
│   │   │
│   │   ├── v2/                        # Structured pipeline
│   │   │   ├── parsing/
│   │   │   │   ├── run_grobid_dual.py
│   │   │   │   └── tei_to_json.py
│   │   │   ├── load_structured_documents.py
│   │   │   ├── build_structured_index.py
│   │   │   ├── test_structured_retrieval.py
│   │   │   ├── test_hybrid_retrieval.py
│   │   │   └── chat_structured_ollama.py
│   │   │
│   │   └── v3/                        # Cross-encoder reranking
│   │       └── rerank.py
│   │
│   └── eval/
│       └── run_retrieval_eval.py      # Evaluation harness (all pipelines)
│
├── benchmarks/
│   └── retrieval_eval_questions.jsonl # 63-question domain benchmark
│
├── results/
│   └── retrieval_eval_summary.md      # Latest benchmark results
│
├── data/                              # gitignored — stays local
├── storage/                           # gitignored — stays local
├── requirements.txt
└── README.md
```

---

## Installation

```bash
git clone https://github.com/fallahtp/NeuroRag.git
cd NeuroRag
python -m venv .venv
.venv\Scripts\activate        # Windows
# source .venv/bin/activate   # macOS/Linux
pip install -r requirements.txt
```

### External Requirements

**Ollama** — local LLM inference. Install from [ollama.com](https://ollama.com) and pull a model:

```bash
ollama pull phi3:mini
```

**Docker + GROBID** — required for the v2 and v3 structured pipelines only. Run a local GROBID container:

```bash
docker run --rm -p 8070:8070 lfoppiano/grobid:0.8.0
```

---

## Running v1 (Flat Baseline)

```bash
# 1. Place PDFs in data/raw/
python src/pipelines/v1/extract_pdfs.py
python src/pipelines/v1/create_metadata.py
python src/pipelines/v1/build_index.py
python src/pipelines/v1/test_retrieval.py   # optional smoke test
python src/pipelines/v1/chat_ollama.py      # interactive CLI chat
```

## Running v2 (Structured Pipeline)

```bash
# 1. Start GROBID via Docker (see above)

# 2. Parse PDFs
python src/pipelines/v2/parsing/run_grobid_dual.py

# 3. Convert TEI XML to structured JSON
python src/pipelines/v2/parsing/tei_to_json.py

# 4. Build the structured FAISS index
python src/pipelines/v2/build_structured_index.py

# 5. Optional: inspect retrieval quality
python src/pipelines/v2/test_structured_retrieval.py
python src/pipelines/v2/test_hybrid_retrieval.py

# 6. Interactive CLI chat
python src/pipelines/v2/chat_structured_ollama.py
```

## Using v3 (Reranked Pipeline)

v3 reuses the v2 structured FAISS index — no separate index build is needed. The cross-encoder reranker is currently integrated into the evaluation harness; an interactive `chat_reranked_ollama.py` is on the roadmap.

```bash
# v3 is evaluated alongside v1 and v2 by the retrieval eval (see below)
python src/eval/run_retrieval_eval.py
```

The first run downloads `cross-encoder/ms-marco-MiniLM-L-6-v2` (~90 MB) from HuggingFace. Subsequent runs load it from the local cache.

---

## Running the Retrieval Evaluation

```bash
python src/eval/run_retrieval_eval.py
```

Evaluates all available pipelines (v1 dense, v2 dense, v2 hybrid, v3 reranked) against `benchmarks/retrieval_eval_questions.jsonl` and writes results to `results/retrieval_eval_summary.md`. Runtime is roughly 2–4 minutes on CPU.

The evaluation harness reports paper-level Hit@K and MRR, section-level Hit@K, and an automated weak-case analysis identifying which questions each pipeline failed on.

---

## Tech Stack

| Component | Library / Tool |
|---|---|
| PDF parsing | pypdf, GROBID |
| XML parsing | xml.etree.ElementTree |
| Document loading | LangChain |
| Embeddings | sentence-transformers/all-MiniLM-L6-v2 |
| Dense index | FAISS |
| Lexical retrieval | BM25 (rank-bm25) |
| Fusion ranking | Reciprocal Rank Fusion (RRF) |
| Reranker | cross-encoder/ms-marco-MiniLM-L-6-v2 |
| Local LLM | Ollama (phi3:mini) |
| Evaluation | Custom harness (run_retrieval_eval.py) |

---

## What Is Not Included

This repository does not contain:

- Private PDFs or extracted text files
- TEI XML outputs or structured JSON outputs
- FAISS vector indexes
- Local virtual environments

These stay on your machine and are excluded via `.gitignore`. This keeps the repository lightweight and shareable as a portfolio project.

---

## Roadmap

- [x] Cross-encoder reranker (v3)
- [x] Expanded retrieval benchmark (63 questions, 15 papers)
- [ ] v3 chat integration (`chat_reranked_ollama.py`)
- [ ] Automated answer-quality (faithfulness) evaluation
- [ ] Web UI (Streamlit)
- [ ] Richer metadata filtering (year, author, category)
- [ ] Table and figure caption extraction
- [ ] Multi-hop and cross-paper benchmark questions
- [ ] Comparison against larger rerankers (`bge-reranker-base`, `bge-reranker-large`)

---

## Author

**Mahdi Fallahtaherpazir**  
PhD Researcher — Neuroscience  
Medical University of Innsbruck

---

## License

MIT License