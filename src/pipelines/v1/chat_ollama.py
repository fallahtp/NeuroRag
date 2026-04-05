from pathlib import Path
import re
import ollama
from langchain_community.vectorstores import FAISS
from langchain_huggingface import HuggingFaceEmbeddings

BASE_DIR = Path(__file__).resolve().parents[3]
INDEX_DIR = BASE_DIR / "storage" / "faiss_index"

OLLAMA_MODEL = "phi3:mini"
TOP_K = 6


def embeddings():
    return HuggingFaceEmbeddings(model_name="sentence-transformers/all-MiniLM-L6-v2")


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


if __name__ == "__main__":
    db = load_db()

    while True:
        question = input("\nAsk: ").strip()
        if not question or question.lower() in {"exit", "quit"}:
            break

        docs = db.similarity_search(question, k=TOP_K)
        context = build_context(docs)
        prompt = build_prompt(question, context)
        answer = ask_ollama(prompt)

        print("\n" + answer)
        print("\nSOURCES METADATA:")
        for i, d in enumerate(docs, start=1):
            m = d.metadata
            print(f"[{i}] {m.get('paper_id')} | {m.get('year')} | {m.get('category')} | {m.get('filename')}")