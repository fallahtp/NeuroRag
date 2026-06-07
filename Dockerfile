# NeuroRag — Hugging Face Space (Docker SDK) running the Streamlit demo.
# Streamlit is no longer a built-in Spaces SDK, so we run it inside a container.
FROM python:3.10-slim

# libgomp1 is required by faiss-cpu / torch (OpenMP runtime).
RUN apt-get update \
    && apt-get install -y --no-install-recommends libgomp1 \
    && rm -rf /var/lib/apt/lists/*

# Non-root user (Hugging Face Spaces convention).
RUN useradd -m -u 1000 user
USER user
ENV HOME=/home/user \
    PATH=/home/user/.local/bin:$PATH

WORKDIR $HOME/app

# Install Python dependencies first for better layer caching.
COPY --chown=user requirements.txt .
RUN pip install --no-cache-dir --upgrade pip \
    && pip install --no-cache-dir -r requirements.txt

# Copy the app: code + committed sample corpus + prebuilt indexes.
COPY --chown=user . .

# Demo configuration: hosted Gemini backend over the bundled sample corpus.
# GEMINI_API_KEY is injected at runtime as a Space secret.
ENV NEURORAG_LLM_BACKEND=gemini \
    NEURORAG_RAW_DIR=/home/user/app/data/sample/raw \
    NEURORAG_INTERIM_DIR=/home/user/app/data/sample/interim \
    NEURORAG_V1_INDEX_DIR=/home/user/app/storage/sample/faiss_index \
    NEURORAG_V2_INDEX_DIR=/home/user/app/storage/sample/faiss_index_v2_structured

EXPOSE 8501
CMD ["streamlit", "run", "app.py", \
     "--server.port=8501", "--server.address=0.0.0.0", \
     "--server.headless=true", "--browser.gatherUsageStats=false"]
