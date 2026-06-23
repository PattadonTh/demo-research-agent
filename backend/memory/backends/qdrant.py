import os
import uuid
from ..store import BaseMemoryStore
from ..embeddings import embed, embed_batch, embedding_dim
from ..chunking import chunk_report

# QDRANT_URL set → Qdrant Cloud (deploy)
# QDRANT_URL unset → local file at QDRANT_PATH (test/dev, persists between runs)
QDRANT_URL = os.getenv("QDRANT_URL")
QDRANT_API_KEY = os.getenv("QDRANT_API_KEY")
QDRANT_PATH = os.getenv("QDRANT_PATH", "qdrant_db")
COLLECTION_NAME = os.getenv("COLLECTION_NAME", "agent_memory")
SIMILARITY_THRESHOLD = 0.3


class QdrantMemoryStore(BaseMemoryStore):
    def __init__(self):
        from qdrant_client import QdrantClient

        if QDRANT_URL:
            print(f"🗄️  [Qdrant] Mode: cloud | URL: {QDRANT_URL}")
            self.client = QdrantClient(url=QDRANT_URL, api_key=QDRANT_API_KEY)
        else:
            print(f"🗄️  [Qdrant] Mode: local file | Path: {QDRANT_PATH}")
            self.client = QdrantClient(path=QDRANT_PATH)

        self._ensure_collection()

    def _ensure_collection(self):
        from qdrant_client.models import Distance, VectorParams

        existing = {c.name for c in self.client.get_collections().collections}
        if COLLECTION_NAME not in existing:
            self.client.create_collection(
                collection_name=COLLECTION_NAME,
                vectors_config=VectorParams(size=embedding_dim(), distance=Distance.COSINE),
            )

    def save(self, report, topic: str) -> int:
        from qdrant_client.models import PointStruct

        chunks = chunk_report(report, topic=topic)
        if not chunks:
            return 0

        texts = [c["text"] for c in chunks]
        vectors = embed_batch(texts)

        points = [
            PointStruct(
                id=str(uuid.uuid5(uuid.NAMESPACE_DNS, c["id"])),
                vector=vec,
                payload={"text": c["text"], **c["metadata"]},
            )
            for c, vec in zip(chunks, vectors)
        ]
        self.client.upsert(collection_name=COLLECTION_NAME, points=points)
        print(f"💾 [Memory] Saved {len(chunks)} chunks for '{topic}'")
        return len(chunks)

    def query(self, topic: str, top_k: int = 5) -> list[dict]:
        count = self.client.get_collection(COLLECTION_NAME).points_count
        if count == 0:
            return []

        response = self.client.query_points(
            collection_name=COLLECTION_NAME,
            query=embed(topic),
            limit=min(top_k, count),
            with_payload=True,
        )

        memories = []
        for hit in response.points:
            similarity = round(hit.score, 3)
            if similarity < SIMILARITY_THRESHOLD:
                continue
            payload = dict(hit.payload)
            text = payload.pop("text", "")
            memories.append({"text": text, "metadata": payload, "similarity": similarity})
        return memories

    def format_context(self, memories: list[dict]) -> str:
        if not memories:
            return ""
        lines = ["## Past Context (retrieved by relevance)\n"]
        for i, mem in enumerate(memories, 1):
            meta = mem["metadata"]
            chunk_type = meta.get("chunk_type")
            lines.append(
                f"[{i}] topic={meta.get('topic')} "
                f"type={chunk_type} "
                f"relevance={mem['similarity']:.0%}"
            )
            if chunk_type == "sources":
                lines.append("*** COPY THESE URLS VERBATIM INTO YOUR sources LIST ***")
            lines.append(mem["text"])
            lines.append("")
        return "\n".join(lines)

    def count(self) -> int:
        return self.client.get_collection(COLLECTION_NAME).points_count

    def clear(self) -> None:
        from qdrant_client.models import Distance, VectorParams

        self.client.delete_collection(COLLECTION_NAME)
        self.client.create_collection(
            collection_name=COLLECTION_NAME,
            vectors_config=VectorParams(size=embedding_dim(), distance=Distance.COSINE),
        )
        print("🗑️  [Memory] Cleared.")
