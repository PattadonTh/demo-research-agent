FROM python:3.12-slim-bookworm

# Patch OS-level CVEs in the base image
RUN apt-get update \
    && apt-get upgrade -y --no-install-recommends \
    && apt-get remove --purge -y perl perl-base \
    && apt-get autoremove -y \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

COPY requirements.txt .
# Install CPU-only torch first — avoids pulling the 2GB CUDA wheel
RUN pip install --no-cache-dir torch==2.12.0 --index-url https://download.pytorch.org/whl/cpu
RUN pip install --no-cache-dir -r requirements.txt

# Pre-download embedding model into the image (avoids runtime download)
RUN python -c "from sentence_transformers import SentenceTransformer; SentenceTransformer('all-MiniLM-L6-v2')"

COPY . .

RUN mkdir -p outputs

EXPOSE 8000
ENV PORT=8000
CMD ["sh", "-c", "uvicorn api:app --host 0.0.0.0 --port ${PORT}"]