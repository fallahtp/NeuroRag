"""
NeuroRag — Streamlit demo UI.

A small chat interface over the NeuroRag retrieval pipelines. Pick a pipeline
(v1 baseline, v2 hybrid, or v3 reranked), ask a neuroscience question, and see
the grounded answer alongside the source chunks that were retrieved — so the
quality progression across pipeline versions is visible live.

Run from the project root:

    streamlit run app.py

Requires the indexes to be built first (see the README "Running the pipelines"
section) and a local Ollama service with the configured models pulled.
"""

from __future__ import annotations

import sys
from pathlib import Path

import streamlit as st

ROOT = Path(__file__).resolve().parent
for _rel in ("src", "src/pipelines/v1", "src/pipelines/v2", "src/pipelines/v3"):
    _p = str(ROOT / _rel)
    if _p not in sys.path:
        sys.path.insert(0, _p)

from config import settings  # noqa: E402

PIPELINES = {
    "v1 baseline (flat RAG)": "v1",
    "v2 hybrid (dense + BM25 + RRF)": "v2_hybrid",
    "v3 reranked (cross-encoder)": "v3_reranked",
}


# ---------------------------------------------------------------------
# Cached resource loaders — each heavy object is built once per session.
# ---------------------------------------------------------------------

@st.cache_resource(show_spinner="Loading v1 baseline index…")
def load_v1_db():
    import chat_ollama

    return chat_ollama.load_db()


@st.cache_resource(show_spinner="Loading v2/v3 structured index and BM25 retriever…")
def load_v2_retrievers():
    import chat_structured_ollama as chat

    return chat.load_dense_db(), chat.build_bm25_retriever()


# ---------------------------------------------------------------------
# Pipeline dispatch
# ---------------------------------------------------------------------

def run_pipeline(pipeline: str, question: str) -> dict:
    """Run one question through the selected pipeline and return a result dict.

    The result always has an ``answer`` string and a ``sources`` list of
    ``{rank, header, snippet, signals}`` dicts, regardless of pipeline.
    """
    if pipeline == "v1":
        import chat_ollama

        db = load_v1_db()
        result = chat_ollama.run_query(question, db)
        sources = []
        for i, doc in enumerate(result["docs"], start=1):
            meta = doc.metadata
            sources.append(
                {
                    "rank": i,
                    "header": f"{meta.get('paper_id', 'unknown')} ({meta.get('year', '')}) "
                    f"— {meta.get('category', '')}",
                    "snippet": chat_ollama.clean_text(doc.page_content)[:800],
                    "signals": meta.get("filename", ""),
                }
            )
        return {"answer": result["answer"], "sources": sources}

    import chat_structured_ollama as chat

    dense_db, bm25_retriever = load_v2_retrievers()
    result = chat.run_query(question, dense_db, bm25_retriever, pipeline=pipeline)

    sources = []
    for i, item in enumerate(result["final_results"], start=1):
        doc = item["doc"]
        meta = doc.metadata
        header = (
            f"{meta.get('title') or meta.get('paper_id', 'unknown')} "
            f"({meta.get('year', '')}) — {meta.get('section_title', '')} "
            f"[{meta.get('section_type', '')}]"
        )
        signal_bits = []
        if item.get("fused_score") is not None:
            signal_bits.append(f"fused={item['fused_score']:.4f}")
        if item.get("rerank_score") is not None:
            signal_bits.append(f"rerank={item['rerank_score']:.4f}")
        if item.get("dense_rank") is not None:
            signal_bits.append(f"dense_rank={item['dense_rank']}")
        if item.get("bm25_rank") is not None:
            signal_bits.append(f"bm25_rank={item['bm25_rank']}")
        sources.append(
            {
                "rank": i,
                "header": header,
                "snippet": chat.select_evidence_sentences(question, doc),
                "signals": " · ".join(signal_bits),
            }
        )
    return {"answer": result["answer"], "sources": sources}


# ---------------------------------------------------------------------
# UI
# ---------------------------------------------------------------------

st.set_page_config(page_title="NeuroRag", page_icon="🧠", layout="wide")
st.title("🧠 NeuroRag")
st.caption(
    "Local retrieval-augmented generation over neuroscience literature. "
    "Pick a pipeline and ask a question to see the answer and its retrieved sources."
)

with st.sidebar:
    st.header("Pipeline")
    pipeline_label = st.radio(
        "Retrieval pipeline",
        list(PIPELINES.keys()),
        index=2,
        help="v1 → v2 → v3 is the quality progression. v3 reranks v2's candidates "
        "with a cross-encoder.",
    )
    pipeline = PIPELINES[pipeline_label]

    st.divider()
    st.subheader("Active configuration")
    model = settings.v1_ollama_model if pipeline == "v1" else settings.v2_ollama_model
    st.text(f"LLM:        {model}")
    st.text(f"Embeddings: {settings.embedding_model.split('/')[-1]}")
    if pipeline == "v3_reranked":
        st.text(f"Reranker:   {settings.reranker_model.split('/')[-1]}")
    st.text(f"Top-k final: {settings.top_k_final}")
    st.caption("Tunable via NEURORAG_* environment variables (see src/config.py).")

question = st.text_input(
    "Question",
    placeholder="e.g. What ion channels shape spiral ganglion neuron excitability?",
)

if st.button("Ask", type="primary") and question.strip():
    try:
        with st.spinner(f"Running {pipeline_label}…"):
            result = run_pipeline(pipeline, question.strip())
    except FileNotFoundError:
        st.error(
            "Index not found. Build the indexes first — see the README "
            "'Running the pipelines' section."
        )
    except Exception as e:  # noqa: BLE001 — surface any runtime failure to the user
        st.error(
            f"Pipeline failed: {e}\n\n"
            "Common causes: the Ollama service is not running, the configured "
            "model is not pulled, or the indexes have not been built yet."
        )
    else:
        if not result["sources"]:
            st.warning("No documents were retrieved from the index for this question.")
        else:
            st.subheader("Answer")
            st.markdown(result["answer"])

            st.subheader(f"Retrieved sources ({len(result['sources'])})")
            for src in result["sources"]:
                with st.expander(f"[{src['rank']}] {src['header']}"):
                    if src["signals"]:
                        st.caption(src["signals"])
                    st.write(src["snippet"])
