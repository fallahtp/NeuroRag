# NeuroRag

**NeuroRag** is a local Retrieval-Augmented Generation (RAG) assistant for neuroscience research and computational modeling. It is designed for researchers who want to search and query their own scientific literature locally, without sending files to external APIs.

> **Goal:** A personal AI research assistant grounded in private, domain-specific literature — built for neuroscience, ion channel research, spiral ganglion neuron modeling, and NEURON/Python workflows.

---

## Key Features

- **Local-first** — all parsing, indexing, retrieval, and generation run on your machine
- **Private corpus** — your PDFs, extracted text, parsed XML, and indexes never leave your computer
- **Two pipeline generations** — a flat baseline (v1) and a structured, section-aware pipeline (v2)
- **Hybrid retrieval** — dense semantic search (FAISS) combined with lexical search (BM25) and RRF fusion
- **Section-aware retrieval** — v2 works at the level of abstract, results, methods, and discussion sections, not just flat chunks
- **Grounded answers** — responses cite source IDs from retrieved context; the LLM is instructed not to fabricate
- **Evaluated** — a 20-question domain benchmark tracks paper-level and section-level retrieval quality across all pipelines

---

## Retrieval Benchmark Results

Evaluated on 20 neuroscience questions covering spiral ganglion neuron morphometry, HCN channel expression, cochlear implant modeling, and NEURON simulation frameworks.

| Pipeline | Paper Hit@1 | Paper Hit@3 | Paper MRR | Section Hit@3 |
|---|---|---|---|---|
| v1 baseline | 85.0% | 90.0% | 0.867 | 85.0% |
| v2 dense | **100.0%** | **100.0%** | **1.000** | **100.0%** |
| v2 hybrid | **100.0%** | **100.0%** | **1.000** | 95.0% |

v2 dense achieves perfect paper retrieval and perfect section retrieval on this benchmark. v2 hybrid matches on paper retrieval and is strong on section retrieval.

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
│   │   └── v2/                        # Structured pipeline
│   │       ├── parsing/
│   │       │   ├── run_grobid_dual.py
│   │       │   └── tei_to_json.py
│   │       ├── load_structured_documents.py
│   │       ├── build_structured_index.py
│   │       ├── test_structured_retrieval.py
│   │       ├── test_hybrid_retrieval.py
│   │       └── chat_structured_ollama.py
│   │
│   └── eval/
│       └── run_retrieval_eval.py      # Evaluation harness
│
├── benchmarks/
│   └── retrieval_eval_questions.jsonl # 20-question domain benchmark
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

**Docker + GROBID** — required for the v2 structured pipeline only. Run a local GROBID container:

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

---

## Running the Retrieval Evaluation

```bash
python src/eval/run_retrieval_eval.py
```

Evaluates all available pipelines against `benchmarks/retrieval_eval_questions.jsonl` and writes results to `results/retrieval_eval_summary.md`.

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

- [ ] Cross-encoder reranker (v3)
- [ ] Web UI (Streamlit)
- [ ] Richer metadata filtering (year, author, category)
- [ ] Table and figure caption extraction
- [ ] Formal answer quality evaluation (not just retrieval)

---

## Author

**Mahdi Fallahtaherpazir**  
PhD Researcher — Neuroscience  
Medical University of Innsbruck

---

## License

MIT License