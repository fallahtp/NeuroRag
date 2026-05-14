import sys
from pathlib import Path
import re
import ollama
from langchain_community.vectorstores import FAISS
from langchain_huggingface import HuggingFaceEmbeddings

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))  # src/
from config import settings

INDEX_DIR = settings.v1_index_dir
OLLAMA_MODEL = settings.v1_ollama_model
TOP_K = settings.top_k_final


def embeddings():
    return HuggingFaceEmbeddings(model_name=settings.embedding_model)


def check_ollama() -> None:
    """Fail early with a clear message if the Ollama service is unreachable."""
    try:
        ollama.list()
    except Exception as e:
        raise SystemExit(
            f"Could not reach Ollama ({e}). Is the Ollama service running? "
            f"Start it, then pull a model with: ollama pull {OLLAMA_MODEL}"
        )


def clean_text(s: str) -> str:
    s = s.replace("\x00", " ")
    s = re.sub(r"\s+", " ", s).strip()
    return s


def load_db():
    return FAISS.load_local(
        str(INDEX_DIR),
        embeddings(),
        allow_dangerous_deserialization=True,
    )


def build_context(docs):
    blocks = []
    for i, d in enumerate(docs, start=1):
        meta = d.metadata
        tag = f"[{i}] {meta.get('paper_id')} ({meta.get('year')}) | {meta.get('category')}"
        snippet = clean_text(d.page_content)[:1200]
        blocks.append(f"{tag}\n{snippet}")
    return "\n\n".join(blocks)


def build_prompt(question: str, context: str) -> str:
    return (
        "You are NeuroRag, a coding + neuroscience assistant for NEURON/Python and SGN modeling.\n"
        "Use ONLY the provided context when citing paper facts. If the context is insufficient, say so.\n"
        "Answer clearly and concisely.\n\n"
        f"QUESTION:\n{question}\n\n"
        f"CONTEXT:\n{context}\n\n"
        "RESPONSE FORMAT:\n"
        "1) Answer\n"
        "2) Sources (list the bracket IDs you used, e.g., [1], [3])\n"
    )


def ask_ollama(prompt: str) -> str:
    r = ollama.chat(
        model=OLLAMA_MODEL,
        messages=[{"role": "user", "content": prompt}],
    )
    return r["message"]["content"]


def run_query(question: str, db) -> dict:
    """Run the v1 baseline retrieval + generation pipeline for one question.

    Returns a dict with the generated ``answer`` and the retrieved ``docs``.
    """
    docs = db.similarity_search(question, k=TOP_K)
    context = build_context(docs)
    prompt = build_prompt(question, context)
    answer = ask_ollama(prompt)
    return {"pipeline": "v1", "answer": answer, "docs": docs}


if __name__ == "__main__":
    check_ollama()
    db = load_db()

    while True:
        question = input("\nAsk: ").strip()
        if not question or question.lower() in {"exit", "quit"}:
            break

        result = run_query(question, db)

        print("\n" + result["answer"])
        print("\nSOURCES METADATA:")
        for i, d in enumerate(result["docs"], start=1):
            m = d.metadata
            print(f"[{i}] {m.get('paper_id')} | {m.get('year')} | {m.get('category')} | {m.get('filename')}")