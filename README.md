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
- **Two evaluation harnesses** — a 63-question retrieval benchmark (paper- and section-level Hit@K and MRR) and a 63-question answer-quality benchmark (fact recall, citation grounding, numeric hallucination)

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

## Answer-Quality Benchmark Results

A separate evaluation harness measures the **generation step** of the v2 hybrid pipeline on the same 63-question benchmark. For each question, the harness runs the full retrieval → prompt → LLM stack and scores the answer on:

- **Fact recall** — whether expected gold-standard tokens appear in the answer (strict substring match)
- **Citation validity** — whether the bracket IDs `[N]` cited by the model are actually in range
- **Citation grounding** — whether the cited evidence chunk contains the expected gold-standard token
- **Numeric hallucination** — whether number-with-unit values in the answer are absent from the retrieved evidence (the most safety-relevant metric for scientific QA)

Two local LLMs were compared as the generation model:

| Metric | phi3:mini (3.8B) | qwen2.5:7b-instruct (7B) |
|---|---:|---:|
| Mean fact recall (strict) | 24.1% | 23.9% |
| Mean citation validity | 97.6% | **100.0%** |
| Mean citation grounding | 33.4% | **39.7%** |
| Answers with at least one citation | 62/63 | **63/63** |
| Answers without numeric hallucination | 59/63 | **63/63** |
| Total fabricated numeric values | 7 | **0** |

**`qwen2.5:7b-instruct` is the default generation model.** It eliminated numeric hallucinations entirely (0 vs 7 across 63 answers), produced no invalid citations, and improved citation grounding by 6 points — without regressing on fact recall.

> Strict-substring fact recall (~24%) is a noisy floor, not a ceiling: 40+ correct answers per model score 0% because they paraphrase ("picoamperes" instead of `pA`, "timing variability" instead of `jitter`). Both models paraphrase at similar rates, so the comparison is undistorted, but the absolute number understates real correctness substantially. The roadmap proposes replacing this with an LLM-as-judge metric using a different model family (e.g. Google Gemini 2.5 Flash) to avoid self-judgment bias.

The full writeup, including per-question failure modes and limitations, is in [`results/model_comparison.md`](results/model_comparison.md).

---

## Architecture Overview

### v1 — Flat Baseline Pipeline

```
PDFs → pypdf extraction → metadata CSV → LangChain Documents
     → RecursiveCharacterTextSplitter → sentence-transformer embeddings
     → FAISS index → similarity search → Ollama (qwen2.5:7b-instruct) → answer
```

### v2 — Structured Pipeline

```
PDFs → GROBID (header + fulltext TEI XML) → structured JSON per paper
     → abstract + section-aware document loading
     → metadata-enriched chunking → FAISS dense index
     → hybrid retrieval: FAISS + BM25 + RRF fusion
     → evidence sentence selection → Ollama (qwen2.5:7b-instruct) → grounded answer
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
│       ├── run_retrieval_eval.py      # Retrieval benchmark harness
│       └── run_answer_eval.py         # Answer-quality benchmark harness
│
├── benchmarks/
│   ├── retrieval_eval_questions.jsonl # 63-question retrieval benchmark
│   └── answer_eval_questions.jsonl    # 63-question answer-quality benchmark
│
├── results/
│   ├── retrieval_eval_summary.md      # Latest retrieval benchmark results
│   ├── answer_eval_summary_qwen2.5_7b_n63.md
│   ├── answer_eval_summary_phi3_mini_n63.md
│   └── model_comparison.md            # Side-by-side answer-quality comparison
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

**Ollama** — local LLM inference. Install from [ollama.com](https://ollama.com) and pull the default generation model:

```bash
ollama pull qwen2.5:7b-instruct
```

To reproduce the model comparison, also pull `phi3:mini`:

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

# 6. Interactive CLI chat (uses qwen2.5:7b-instruct by default)
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

## Running the Evaluations

### Retrieval evaluation

```bash
python src/eval/run_retrieval_eval.py
```

Evaluates all available pipelines (v1 dense, v2 dense, v2 hybrid, v3 reranked) against `benchmarks/retrieval_eval_questions.jsonl` and writes results to `results/retrieval_eval_summary.md`. Runtime is roughly 2–4 minutes on CPU.

### Answer-quality evaluation

```bash
# Default model (qwen2.5:7b-instruct)
python src/eval/run_answer_eval.py

# Or specify a different model
python src/eval/run_answer_eval.py --model phi3:mini
```

Runs the full v2 hybrid retrieval → prompt → LLM stack on each benchmark question and scores the resulting answer on fact recall, citation validity, citation grounding, and numeric hallucination. Writes results to `results/answer_eval_summary.{json,md}`. Runtime is ~10 min on `phi3:mini` and ~25–40 min on `qwen2.5:7b-instruct` (CPU-bound, depends on hardware).

To reproduce the side-by-side model comparison in `results/model_comparison.md`, run both models and rename the outputs in between (see that file's "Reproducing These Numbers" section).

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
| Local LLM (default) | Ollama — `qwen2.5:7b-instruct` |
| Local LLM (compared) | Ollama — `phi3:mini` |
| Retrieval evaluation | Custom harness (`run_retrieval_eval.py`) |
| Answer-quality evaluation | Custom harness (`run_answer_eval.py`) |

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
- [x] Automated answer-quality evaluation (fact recall, citations, hallucination)
- [x] Two-model answer-quality comparison (`phi3:mini` vs `qwen2.5:7b-instruct`)
- [ ] LLM-as-judge fact recall using a different model family (e.g. Google Gemini 2.5 Flash free tier) to avoid self-judgment bias and replace the strict-substring matcher
- [ ] Re-run the answer-quality eval on the v3 reranked pipeline (currently runs on v2 hybrid)
- [ ] v3 chat integration (`chat_reranked_ollama.py`)
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