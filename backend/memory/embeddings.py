import os
from dotenv import load_dotenv

load_dotenv()

EMBEDDING_MODEL = os.getenv("EMBEDDING_MODEL", "all-MiniLM-L6-v2")

_DIMS = {
    "all-MiniLM-L6-v2": 384,
    "all-mpnet-base-v2": 768,
    "paraphrase-MiniLM-L3-v2": 384,
    "BAAI/bge-small-en-v1.5": 384,
}

_st_model = None


def embedding_dim() -> int:
    return _DIMS.get(EMBEDDING_MODEL, 384)


def _get_st_model():
    global _st_model
    if _st_model is None:
        from sentence_transformers import SentenceTransformer
        print(f"🔢 [Embeddings] Model: {EMBEDDING_MODEL} | Dims: {embedding_dim()}")
        _st_model = SentenceTransformer(EMBEDDING_MODEL)
    return _st_model


def embed(text: str) -> list[float]:
    return _get_st_model().encode(text if text.strip() else "empty").tolist()


def embed_batch(texts: list[str]) -> list[list[float]]:
    texts = [t if t.strip() else "empty" for t in texts]
    return _get_st_model().encode(texts).tolist()
