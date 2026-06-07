# Case Study — NeuroRag: a measured, hallucination-controlled RAG system

> **One line:** I built a local Retrieval-Augmented Generation system for scientific
> literature and proved, on a 63-question benchmark, that adding hybrid retrieval and
> cross-encoder reranking raised judged fact recall from 33.8% → **38.7%**, raised
> citation grounding to **43.7%**, and held numeric hallucinations at **0**.

**Author:** Mahdi Fallahtaherpazir — PhD Researcher, Neuroscience (Medical University of Innsbruck)
**Code:** https://github.com/fallahtp/NeuroRag
**Role:** Sole engineer — architecture, retrieval, evaluation harness, and UI.

---

## The problem

Researchers and technical teams sit on large corpora of dense PDFs — papers, manuals,
specs — and need answers they can *trust and cite*, not plausible-sounding summaries.
Off-the-shelf "chat with your PDF" tools fail two ways that matter in a professional
setting: they **hallucinate numbers** that were never in the source, and they give you
**no way to measure** whether retrieval actually surfaced the right evidence.

The goal of NeuroRag was the opposite of a flashy demo: a system where retrieval
quality, answer grounding, and trustworthiness are **measured first-class metrics**,
and where every document stays **local** (nothing sent to external APIs at inference).

## What I built

Three retrieval pipelines, each a measurable step up from the last, behind one shared
evaluation harness:

| Pipeline | What it does |
|----------|--------------|
| **v1 baseline** | PDF → text → FAISS dense retrieval → local LLM answer |
| **v2 structured** | GROBID-parsed section-aware JSON, hybrid **dense + BM25** retrieval fused with Reciprocal Rank Fusion |
| **v3 reranked** | v2 candidates rescored by a **cross-encoder** before a per-paper diversity cap |

On top of the pipelines, an **evaluation harness** that is treated as a product, not an
afterthought: a 63-question domain benchmark, retrieval metrics (Hit@k, MRR at both
paper and section level), and answer metrics (fact recall, citation validity, citation
grounding, numeric hallucination) scored two independent ways — a transparent strict
substring matcher **and** an LLM-as-judge using a *different model family* (Gemini 2.5
Flash) to avoid self-grading bias, with on-disk caching so reruns are free.

## Results (63-question benchmark)

**Retrieval — does the right paper/section reach the top?**

| Pipeline  | Paper Hit@1 | Paper Hit@5 | Section Hit@3 |
|-----------|------------:|------------:|--------------:|
| v1 dense  | 85.0%       | 90.0%       | 85.0%         |
| v2 dense  | 100.0%      | 100.0%      | 100.0%        |
| v2 hybrid | 100.0%      | 100.0%      | 95.0%         |

**Answer quality — does the generated answer contain the right facts, grounded in real sources?**

| Setup                          | Fact recall (judge) | Citation grounding | Hallucinations |
|--------------------------------|--------------------:|-------------------:|---------------:|
| phi3:mini + v2 hybrid          | 34.8%               | 33.4%              | 7              |
| qwen2.5:7b + v2 hybrid         | 33.8%               | 39.7%              | **0**          |
| **qwen2.5:7b + v3 reranked**   | **38.7%**           | **43.7%**          | **0**          |

Three findings that shaped the system:

1. **Reranking pays off.** v3 cross-encoder reranking added **+5pp** judged fact recall
   and **+4pp** citation grounding over v2. Citation grounding has no LLM in the scoring
   loop, so its gain is the most trustworthy signal that v3 surfaces better evidence.
2. **Honesty ≠ recall.** phi3 and qwen2.5 *tied* on fact recall but diverged sharply on
   honesty: phi3 invented unsupported numbers in several answers; qwen2.5 invented
   **none**. I made qwen2.5 the default generator on that basis — for scientific work,
   a confident wrong number is worse than a miss.
3. **Measure twice.** Strict substring matching systematically *undercounted* by ~10pp
   versus the judge, while preserving the relative ordering of pipelines — which is
   exactly why I report both rather than trusting one number.

## Engineering decisions a client would care about

- **Eval-first, not demo-first.** The harness exists so improvements are *proven*, not
  asserted. This is the difference between a prototype and a system you can put in front
  of users.
- **Hallucination control as a metric.** Fabricated measurements are detected and
  counted, not hand-waved. The chosen configuration ships at zero.
- **Local-first / private by default.** Parsing, indexing, retrieval, and generation run
  on-machine via Ollama; no documents leave the box at inference. Suits regulated,
  confidential, or IP-sensitive corpora.
- **Config-driven, no source edits.** Every knob (models, chunk sizes, top-k, vector
  backend) is overridable via `NEURORAG_*` environment variables.
- **Production-grade hygiene.** Unit tests, ruff lint, and CI on every push; optional
  RAGAS metrics, a Qdrant backend, and LangSmith tracing behind flags.

## What I can deliver for a client

- A **document-QA / RAG system over your own corpus** that cites its sources and is
  tuned against *your* questions, not a generic demo.
- A **retrieval + answer evaluation harness** so quality is measured and regressions are
  caught — the piece most RAG projects skip.
- **Hallucination and grounding controls** for settings where a wrong answer is
  expensive (scientific, legal, medical, technical).
- **Local / private deployment** for confidential data.

## Stack

Python · LangChain · FAISS (+ optional Qdrant) · sentence-transformers (`all-MiniLM-L6-v2`)
· BM25 · cross-encoder reranker (`ms-marco-MiniLM-L-6-v2`) · Ollama (local LLMs) ·
Gemini (LLM-as-judge, eval only) · RAGAS · LangSmith · Streamlit · GROBID · Docker ·
pytest + ruff + GitHub Actions.

---

*Numbers in this case study are reproducible from the committed eval summaries in
[`results/`](results/) and the harness in [`src/eval/`](src/eval/).*
