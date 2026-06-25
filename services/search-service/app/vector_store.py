import hashlib
import logging
from typing import Optional

import httpx
import numpy as np
from qdrant_client import QdrantClient
from qdrant_client.models import Distance, PointStruct, VectorParams

from shared.config import get_settings

logger = logging.getLogger(__name__)
settings = get_settings()

COLLECTION = "transcript_embeddings"
VECTOR_SIZE = 384
client: Optional[QdrantClient] = None


def get_client() -> QdrantClient:
    global client
    if client is None:
        client = QdrantClient(url=settings.qdrant_url)
        _ensure_collection()
    return client


def _ensure_collection():
    collections = [c.name for c in client.get_collections().collections]
    if COLLECTION not in collections:
        client.create_collection(
            collection_name=COLLECTION,
            vectors_config=VectorParams(size=VECTOR_SIZE, distance=Distance.COSINE),
        )


def _simple_embed(text: str) -> list[float]:
    """Deterministic hash-based embedding for local dev (swap for sentence-transformers in prod)."""
    h = hashlib.sha256(text.encode()).digest()
    vec = np.frombuffer(h * (VECTOR_SIZE // 32 + 1), dtype=np.uint8)[:VECTOR_SIZE]
    return (vec.astype(np.float32) / 255.0).tolist()


def embed_text(text: str) -> list[float]:
    return _simple_embed(text)


def store_embedding(video_id: str, chunk_id: str, start: float, end: float, text: str):
    vector = embed_text(text)
    point_id = int(hashlib.md5(f"{video_id}_{chunk_id}".encode()).hexdigest()[:15], 16)
    get_client().upsert(
        collection_name=COLLECTION,
        points=[PointStruct(
            id=point_id,
            vector=vector,
            payload={
                "video_id": video_id,
                "chunk_id": chunk_id,
                "start_time": start,
                "end_time": end,
                "text": text,
            },
        )],
    )


def semantic_search(query: str, limit: int = 10) -> list[dict]:
    vector = embed_text(query)
    results = get_client().search(
        collection_name=COLLECTION,
        query_vector=vector,
        limit=limit,
    )
    return [{
        "video_id": hit.payload["video_id"],
        "start_time": hit.payload["start_time"],
        "end_time": hit.payload["end_time"],
        "text": hit.payload["text"],
        "score": hit.score,
    } for hit in results]
