from pathlib import Path
import re
from langchain_community.vectorstores import FAISS
try:
    from langchain_huggingface import HuggingFaceEmbeddings
except ImportError:
    from langchain_community.embeddings import HuggingFaceEmbeddings

BASE_DIR = Path(__file__).resolve().parents[3]
INDEX_DIR = BASE_DIR / "storage" / "faiss_index"


def embeddings():
    return HuggingFaceEmbeddings(model_name="sentence-transformers/all-MiniLM-L6-v2")


def clean_text(s: str) -> str:
    s = s.replace("\x00", " ")
    s = re.sub(r"\s+", " ", s).strip()
    return s


if __name__ == "__main__":
    db = FAISS.load_local(
        str(INDEX_DIR),
        embeddings(),
        allow_dangerous_deserialization=True,
    )

    query = "HCN channels spiral ganglion neuron function"
    results = db.similarity_search(query, k=10)

    seen = set()
    filtered = []
    for r in results:
        key = (r.metadata.get("paper_id"), hash(r.page_content[:200]))
        if key in seen:
            continue
        seen.add(key)
        filtered.append(r)

    for i, r in enumerate(filtered[:5], start=1):
        meta = r.metadata
        print("=" * 80)
        print(f"RESULT {i} | {meta.get('paper_id')} | {meta.get('year')} | {meta.get('category')}")
        print(clean_text(r.page_content)[:800])