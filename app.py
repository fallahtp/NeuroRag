"""
NeuroRag — Streamlit demo UI.

A chat interface over the NeuroRag retrieval pipelines. Pick a pipeline
(v1 baseline, v2 hybrid, or v3 reranked), ask a neuroscience question, and see
the grounded answer alongside the source chunks that were retrieved — so the
quality progression across pipeline versions is visible live.

Run from the project root:

    streamlit run app.py

Requires the indexes to be built first (see the README "Running the pipelines"
section) and a generation backend (local Ollama, or Gemini via
NEURORAG_LLM_BACKEND=gemini).
"""

from __future__ import annotations

import html as html_lib
import re
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

DEFAULT_QUESTION = "How do spiral ganglion neuron lengths compare between humans and cats?"


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
# Answer formatting
# ---------------------------------------------------------------------

def parse_answer(text: str) -> dict:
    """Split the normalized answer string into answer / evidence / source-ids."""
    a = re.search(r"(?is)answer\s*:\s*(.*?)(?:\n\s*evidence summary\s*:|\Z)", text)
    e = re.search(r"(?is)evidence summary\s*:\s*(.*?)(?:\n\s*source ids\s*:|\Z)", text)
    s = re.search(r"(?is)source ids\s*:\s*(.*)\Z", text)
    return {
        "answer": (a.group(1).strip() if a else text.strip()),
        "evidence": (e.group(1).strip() if e else ""),
        "sources": (s.group(1).strip() if s else ""),
    }


def card_html(label: str, text: str, accent: str) -> str:
    safe = html_lib.escape(text).replace("\n", "<br>")
    return (
        f'<div class="nr-card" style="border-left:4px solid {accent}">'
        f'<div class="nr-card-label" style="color:{accent}">{label}</div>'
        f'<div class="nr-card-body">{safe}</div></div>'
    )


# ---------------------------------------------------------------------
# Page + styling
# ---------------------------------------------------------------------

st.set_page_config(page_title="NeuroRag", page_icon="🧠", layout="wide")

st.markdown(
    """
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700;800&display=swap');
    html, body, [class*="css"] { font-family: 'Inter', sans-serif; }
    #MainMenu, footer { visibility: hidden; }

    .nr-title {
        font-size: 2.7rem; font-weight: 800; letter-spacing: -0.02em; margin: 0;
        background: linear-gradient(90deg,#a78bfa,#60a5fa 55%,#34d399);
        -webkit-background-clip: text; -webkit-text-fill-color: transparent; background-clip: text;
    }
    .nr-sub { color:#9aa4b2; font-size:1.03rem; margin:.35rem 0 .2rem 0; max-width:760px; }
    .nr-badge {
        display:inline-block; font-size:.72rem; font-weight:600; color:#c4b5fd;
        background:rgba(139,92,246,.12); border:1px solid rgba(139,92,246,.35);
        padding:3px 10px; border-radius:999px; margin:.5rem 6px 0 0;
    }

    .stButton>button, .stFormSubmitButton>button {
        background: linear-gradient(90deg,#7c3aed,#6366f1); color:#fff; border:0;
        border-radius:10px; padding:.6rem 1.2rem; font-weight:600;
        box-shadow:0 4px 14px rgba(124,58,237,.35); transition:transform .05s ease, box-shadow .2s ease;
    }
    .stButton>button:hover, .stFormSubmitButton>button:hover {
        transform:translateY(-1px); box-shadow:0 6px 20px rgba(124,58,237,.55);
    }
    .stTextInput input { border-radius:10px !important; padding:.7rem .9rem !important; font-size:1rem !important; }

    .nr-card {
        background:#11151d; border:1px solid #232a37; border-radius:14px;
        padding:1rem 1.2rem; margin:.6rem 0; box-shadow:0 2px 12px rgba(0,0,0,.28);
    }
    .nr-card-label {
        font-size:.72rem; font-weight:700; text-transform:uppercase;
        letter-spacing:.09em; margin-bottom:.4rem;
    }
    .nr-card-body { color:#e6e9ef; line-height:1.6; font-size:1.02rem; }

    .nr-chip {
        display:inline-block; font-size:.74rem; color:#93c5fd; background:rgba(59,130,246,.12);
        border:1px solid rgba(59,130,246,.3); padding:2px 9px; border-radius:999px;
        margin:.2rem 5px .2rem 0; font-family:ui-monospace,Menlo,monospace;
    }
    .nr-section { font-size:1.15rem; font-weight:700; color:#e6e9ef; margin:1.4rem 0 .4rem 0; }

    [data-testid="stExpander"] {
        border:1px solid #232a37 !important; border-radius:12px !important;
        margin-bottom:.5rem; background:#0f131b;
    }
    [data-testid="stSidebar"] { background:#0c0f16; border-right:1px solid #1c2230; }
    .nr-cfg { color:#cbd5e1; font-size:.9rem; margin:.15rem 0; }
    .nr-cfg b { color:#a78bfa; }
    .nr-footer { color:#6b7280; font-size:.8rem; margin-top:2.2rem; border-top:1px solid #1c2230; padding-top:.8rem; }
    </style>
    """,
    unsafe_allow_html=True,
)

# ---------------------------------------------------------------------
# Hero
# ---------------------------------------------------------------------

st.markdown(
    """
    <div>
      <div class="nr-title">🧠 NeuroRag</div>
      <div class="nr-sub">Grounded, source-cited question answering over neuroscience literature —
      with three retrieval pipelines and a measured evaluation harness behind it.</div>
      <div>
        <span class="nr-badge">Hybrid retrieval</span>
        <span class="nr-badge">Cross-encoder reranking</span>
        <span class="nr-badge">Grounded citations</span>
        <span class="nr-badge">0 hallucinations</span>
      </div>
    </div>
    """,
    unsafe_allow_html=True,
)

# ---------------------------------------------------------------------
# Sidebar
# ---------------------------------------------------------------------

with st.sidebar:
    st.markdown('<div class="nr-section" style="margin-top:.2rem">Pipeline</div>', unsafe_allow_html=True)
    pipeline_label = st.radio(
        "Retrieval pipeline",
        list(PIPELINES.keys()),
        index=2,
        label_visibility="collapsed",
        help="v1 → v2 → v3 is the quality progression. v3 reranks v2's candidates "
        "with a cross-encoder.",
    )
    pipeline = PIPELINES[pipeline_label]

    st.divider()
    st.markdown('<div class="nr-section" style="font-size:1rem">Active configuration</div>', unsafe_allow_html=True)
    if settings.llm_backend == "gemini":
        llm_label = f"{settings.gemini_gen_model} (gemini)"
    else:
        ollama_model = settings.v1_ollama_model if pipeline == "v1" else settings.v2_ollama_model
        llm_label = f"{ollama_model} (ollama)"
    st.markdown(f'<div class="nr-cfg"><b>LLM</b> · {llm_label}</div>', unsafe_allow_html=True)
    st.markdown(
        f'<div class="nr-cfg"><b>Embeddings</b> · {settings.embedding_model.split("/")[-1]}</div>',
        unsafe_allow_html=True,
    )
    if pipeline == "v3_reranked":
        st.markdown(
            f'<div class="nr-cfg"><b>Reranker</b> · {settings.reranker_model.split("/")[-1]}</div>',
            unsafe_allow_html=True,
        )
    st.markdown(f'<div class="nr-cfg"><b>Top-k final</b> · {settings.top_k_final}</div>', unsafe_allow_html=True)
    st.caption("Tunable via NEURORAG_* environment variables (see src/config.py).")

# ---------------------------------------------------------------------
# Question form (Enter submits)
# ---------------------------------------------------------------------

if "nr_question" not in st.session_state:
    st.session_state.nr_question = ""

st.markdown('<div class="nr-section">Ask a question</div>', unsafe_allow_html=True)
with st.form("ask_form", clear_on_submit=False):
    col_q, col_b = st.columns([6, 1])
    with col_q:
        st.text_input(
            "Question",
            key="nr_question",
            label_visibility="collapsed",
            placeholder=DEFAULT_QUESTION,
        )
    with col_b:
        submitted = st.form_submit_button("Ask ↵", type="primary", use_container_width=True)

question = st.session_state.nr_question

if submitted and question.strip():
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
            f"Generation failed: {e}\n\n"
            "Common causes: the configured generation backend is unreachable "
            "(Ollama not running, or an invalid/missing GEMINI_API_KEY), or the "
            "indexes have not been built yet."
        )
    else:
        if not result["sources"]:
            st.warning("No documents were retrieved from the index for this question.")
        else:
            parts = parse_answer(result["answer"])
            st.markdown(card_html("Answer", parts["answer"], "#a78bfa"), unsafe_allow_html=True)
            if parts["evidence"]:
                st.markdown(card_html("Evidence summary", parts["evidence"], "#60a5fa"), unsafe_allow_html=True)

            ids = parts["sources"]
            if ids and ids.lower() != "none":
                chips = "".join(
                    f'<span class="nr-chip">{html_lib.escape(c)}</span>'
                    for c in re.findall(r"\[\d+\]", ids)
                )
                st.markdown(
                    '<div style="margin:.2rem 0 .4rem 0"><span class="nr-card-label" '
                    f'style="color:#34d399">Cited sources</span><br>{chips}</div>',
                    unsafe_allow_html=True,
                )

            st.markdown(
                f'<div class="nr-section">Retrieved sources ({len(result["sources"])})</div>',
                unsafe_allow_html=True,
            )
            for src in result["sources"]:
                with st.expander(f"[{src['rank']}]  {src['header']}"):
                    if src["signals"]:
                        st.caption(src["signals"])
                    st.write(src["snippet"])

st.markdown(
    '<div class="nr-footer">NeuroRag · local-first RAG with a measured eval harness · '
    '<a href="https://github.com/fallahtp/NeuroRag" style="color:#8b5cf6">github.com/fallahtp/NeuroRag</a></div>',
    unsafe_allow_html=True,
)
