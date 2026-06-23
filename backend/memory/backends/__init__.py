import os


def get_memory_store():
    """
    Factory function — return the correct memory backend based on .env config.

    Set MEMORY_BACKEND in your .env to choose a backend:
      MEMORY_BACKEND=qdrant  (default) — in-memory when no QDRANT_URL, cloud otherwise

    To add a new backend (e.g. Pinecone):
      1. Create memory/backends/pinecone.py extending BaseMemoryStore.
      2. Add an elif branch below and set MEMORY_BACKEND=pinecone in .env.
    """
    backend = os.getenv("MEMORY_BACKEND", "qdrant")
    if backend == "qdrant":
        from .qdrant import QdrantMemoryStore

        return QdrantMemoryStore()
    raise ValueError(f"Unknown backend: {backend}")
