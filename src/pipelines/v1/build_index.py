import sys
from pathlib import Path

from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_community.vectorstores import FAISS

try:
    from langchain_huggingface import HuggingFaceEmbeddings
except ImportError:
    from langchain_community.embeddings import HuggingFaceEmbeddings

# Make the v1 package directory and src/ importable regardless of the current
# working directory, so this script runs from the project root as well as v1/.
sys.path.insert(0, str(Path(__file__).resolve().parent))
sys.path.insert(0, str(Path(__file__).resolve().parents[2]))  # src/
from load_documents import load_papers
from config import settings

INDEX_DIR = settings.v1_index_dir


def split_papers(papers):
    splitter = RecursiveCharacterTextSplitter(
        chunk_size=settings.chunk_size,
        chunk_overlap=settings.chunk_overlap,
        separators=["\n\n", "\n", ". ", " ", ""],
    )
    return splitter.split_documents(papers)


def create_embeddings():
    return HuggingFaceEmbeddings(model_name=settings.embedding_model)


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