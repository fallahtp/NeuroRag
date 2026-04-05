from pathlib import Path
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_community.vectorstores import FAISS

try:
    from langchain_huggingface import HuggingFaceEmbeddings
except ImportError:
    from langchain_community.embeddings import HuggingFaceEmbeddings

from load_documents import load_papers

BASE_DIR = Path(__file__).resolve().parents[3]
INDEX_DIR = BASE_DIR / "storage" / "faiss_index"


def split_papers(papers):
    splitter = RecursiveCharacterTextSplitter(
        chunk_size=1000,
        chunk_overlap=200,
        separators=["\n\n", "\n", ". ", " ", ""],
    )
    return splitter.split_documents(papers)


def create_embeddings():
    return HuggingFaceEmbeddings(model_name="sentence-transformers/all-MiniLM-L6-v2")


def build_faiss_index(chunks):
    embeddings = create_embeddings()
    db = FAISS.from_documents(chunks, embeddings)
    INDEX_DIR.mkdir(parents=True, exist_ok=True)
    db.save_local(str(INDEX_DIR))
    return db


if __name__ == "__main__":
    papers = load_papers()
    chunks = split_papers(papers)
    print(f"Papers: {len(papers)}")
    print(f"Chunks: {len(chunks)}")
    build_faiss_index(chunks)
    print(f"Saved index to: {INDEX_DIR}")