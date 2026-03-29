# NeuroRag

**NeuroRag** is a **local Retrieval-Augmented Generation (RAG) assistant** for **neuroscience research and computational modeling**.

It is designed for researchers who want to search and query their own scientific literature, notes, and technical documents **locally**, without sending files to external APIs.

The project currently contains two pipelines:

- **v1 baseline:** a simple local PDF-to-FAISS RAG pipeline
- **v2 structured pipeline:** a more advanced workflow using **GROBID**, **structured JSON**, **section-aware retrieval**, and **hybrid search**

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

NeuroRag has evolved from a **minimal but complete local RAG baseline** into a **structured document retrieval prototype**.

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
- dual GROBID parsing:
  - header TEI
  - fulltext TEI
- TEI → structured JSON conversion
- section-aware and abstract-aware document loading
- structured FAISS index
- hybrid retrieval:
  - dense retrieval (FAISS)
  - lexical retrieval (BM25)
  - fusion-based ranking
- section-aware CLI chat with grounded source display

### Current limitations
- metadata extraction is still imperfect for some older PDFs
- year extraction can still be noisy in some cases
- some section titles remain messy depending on the source PDF
- answer quality is already better than v1, but still needs further evaluation and refinement
- no web UI yet
- no formal benchmark/evaluation set yet

---

## Key Features

- **Local-first architecture**  
  All parsing, indexing, retrieval, and generation run locally.

- **Private research corpus**  
  Your PDFs, extracted text, parsed XML, JSON, and indexes stay on your machine.

- **Two-level architecture**
  - baseline flat RAG
  - structured scientific-document RAG

- **Scientific document parsing**  
  Uses GROBID to extract structured content from papers.

- **Section-aware retrieval**  
  Retrieval is no longer limited to flat chunks; v2 works with abstracts and structured sections.

- **Hybrid retrieval**  
  Combines semantic retrieval and lexical retrieval.

- **Local LLM integration via Ollama**

- **Grounded answers with source IDs**

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
Hybrid retrieval / fusion
      │
      ▼
Ollama
      │
      ▼
Grounded answer with section-aware sources
```

---

## Repository Structure

```text
NeuroRag/
│
├── src/
│   ├── extract_pdfs.py
│   ├── create_metadata.py
│   ├── load_documents.py
│   ├── build_index.py
│   ├── test_retrieval.py
│   ├── chat_ollama.py
│   │
│   ├── parsing/
│   │   ├── run_grobid.py
│   │   ├── run_grobid_dual.py
│   │   └── tei_to_json.py
│   │
│   └── v2/
│       ├── load_structured_documents.py
│       ├── build_structured_index.py
│       ├── test_structured_retrieval.py
│       ├── test_hybrid_retrieval.py
│       └── chat_structured_ollama.py
│
├── data/                  # ignored by git
│   ├── raw/
│   ├── processed/
│   └── interim/
│       ├── tei_xml/
│       ├── header_tei_xml/
│       └── structured_json/
│
├── storage/               # ignored by git
│   ├── faiss_index/
│   └── faiss_index_v2_structured/
│
├── requirements.txt
├── .gitignore
└── README.md
```

---

## v1 Baseline Components

### 1. PDF extraction

`src/extract_pdfs.py`

- reads PDFs from `data/raw/`
- extracts page text using `pypdf`
- writes `.txt` files into `data/processed/`

### 2. Metadata generation

`src/create_metadata.py`

Creates:

- `data/interim/paper_metadata.csv`

Baseline fields:

- filename
- relative path
- year
- first author
- category

### 3. Flat document loading

`src/load_documents.py`

Loads processed text plus metadata into LangChain documents.

### 4. Baseline index

`src/build_index.py`

- chunking with `RecursiveCharacterTextSplitter`
- embeddings with `sentence-transformers/all-MiniLM-L6-v2`
- FAISS storage in `storage/faiss_index/`

### 5. Retrieval smoke test

`src/test_retrieval.py`

### 6. Baseline chat

`src/chat_ollama.py`

Simple local CLI RAG over the v1 index.

---

## v2 Structured Pipeline Components

### 1. GROBID parsing

- `src/parsing/run_grobid.py`
- `src/parsing/run_grobid_dual.py`

The structured pipeline uses GROBID to produce:

- fulltext TEI XML
- header TEI XML

Outputs are stored under:

- `data/interim/tei_xml/`
- `data/interim/header_tei_xml/`

### 2. TEI → JSON conversion

`src/parsing/tei_to_json.py`

Builds one structured JSON record per paper in:

- `data/interim/structured_json/`

Each paper JSON contains:

- paper-level metadata
- abstract
- section-aware body content
- source paths

### 3. Structured document loading

`src/v2/load_structured_documents.py`

Creates LangChain documents from:

- abstract
- section-level text

while preserving metadata such as:

- paper ID
- title
- year
- DOI
- keywords
- section title
- section type

### 4. Structured index

`src/v2/build_structured_index.py`

Builds a separate FAISS index:

- `storage/faiss_index_v2_structured/`

### 5. Structured retrieval inspection

- `src/v2/test_structured_retrieval.py`
- `src/v2/test_hybrid_retrieval.py`

Used to inspect:

- dense retrieval
- hybrid retrieval
- section-aware evidence quality

### 6. Structured chat

`src/v2/chat_structured_ollama.py`

Uses:

- FAISS dense retrieval
- BM25 lexical retrieval
- fusion-based ranking
- section-aware source display
- local Ollama generation

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
pip install -r requirements.txt
```

---

## External Requirements

### Ollama

NeuroRag uses a local Ollama model for answer generation.

Make sure Ollama is installed and running.

Example model used in the project:

```text
phi3:mini
```

### Docker + GROBID

The structured v2 pipeline uses GROBID through Docker.

Typical workflow:

- install Docker Desktop
- run a local GROBID container
- send PDFs to the local GROBID API from Python

---

## Running the v1 Pipeline

### 1. Put PDFs in

```text
data/raw/
```

### 2. Extract text

```bash
python src/extract_pdfs.py
```

### 3. Create metadata

```bash
python src/create_metadata.py
```

### 4. Build the baseline index

```bash
python src/build_index.py
```

### 5. Test retrieval

```bash
python src/test_retrieval.py
```

### 6. Start baseline chat

```bash
python src/chat_ollama.py
```

---

## Running the v2 Structured Pipeline

### 1. Start GROBID

Run GROBID locally through Docker.

### 2. Parse PDFs with GROBID

```bash
python src/parsing/run_grobid_dual.py
```

### 3. Convert TEI to structured JSON

```bash
python src/parsing/tei_to_json.py
```

### 4. Load structured documents

```bash
python src/v2/load_structured_documents.py
```

### 5. Build structured index

```bash
python src/v2/build_structured_index.py
```

### 6. Test structured retrieval

```bash
python src/v2/test_structured_retrieval.py
python src/v2/test_hybrid_retrieval.py
```

### 7. Start structured chat

```bash
python src/v2/chat_structured_ollama.py
```

---

## Data and Privacy

This repository does not include:

- private PDFs
- extracted text files
- TEI XML outputs
- structured JSON outputs
- FAISS vector indexes
- local virtual environments

These remain local and are excluded via `.gitignore`.

This keeps the repository:

- private
- lightweight
- easier to share publicly as a portfolio project

---

## Why this project matters

NeuroRag is not meant to be just a generic “chat with PDFs” demo.

The goal is to build a domain-specific local research assistant for:

- neuroscience literature
- ion channel questions
- spiral ganglion neuron research
- computational modeling
- NEURON / Python-related workflows

The most important direction is not flashy UI, but:

- better retrieval quality
- better grounding
- better trustworthiness
- better domain specialization

---

## Roadmap

### Near-term
- metadata cleanup
- better retrieval ranking
- evaluation set for neuroscience questions
- cleaner structured source display
- improved README and project presentation

### Next phase
- reranking
- better scientific table/caption extraction
- web interface
- richer metadata-aware filtering
- benchmarking and retrieval metrics
- domain-specific prompt modes for neuroscience / NEURON workflows

---

## Tech Stack

- Python
- LangChain
- FAISS
- HuggingFace sentence-transformer embeddings
- BM25 / lexical retrieval
- Ollama
- PyPDF
- GROBID
- Docker

---

## Author

**Mahdi Fallahtaherpazir**  
PhD Researcher — Neuroscience  
Medical University of Innsbruck

---

## License

MIT License
