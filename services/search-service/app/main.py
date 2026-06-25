import time
from typing import Optional

from fastapi import FastAPI, Query
from pydantic import BaseModel

from shared.config import get_settings
from shared.logging_config import setup_logging
from shared.metrics import REQUEST_COUNT, REQUEST_LATENCY, setup_metrics
from shared.redis_client import RedisClient

from .cassandra_client import init_cassandra, search_transcripts
from .vector_store import semantic_search

settings = get_settings()
logger = setup_logging(settings.service_name)
app = FastAPI(title="Search Service", version="1.0.0")
setup_metrics(app, settings.service_name)
redis = RedisClient(settings.redis_url)


class SearchResult(BaseModel):
    video_id: str
    start_time: float
    end_time: float
    text: str
    score: float


class SearchResponse(BaseModel):
    query: str
    results: list[SearchResult]
    search_type: str


@app.on_event("startup")
def startup():
    try:
        init_cassandra()
    except Exception as e:
        logger.warning("Cassandra not ready yet: %s", e)


@app.middleware("http")
async def metrics_middleware(request, call_next):
    start = time.time()
    response = await call_next(request)
    REQUEST_COUNT.labels(settings.service_name, request.method, request.url.path, response.status_code).inc()
    REQUEST_LATENCY.labels(settings.service_name, request.method, request.url.path).observe(time.time() - start)
    return response


@app.get("/health")
def health():
    return {"status": "healthy", "service": settings.service_name}


@app.get("/api/search", response_model=SearchResponse)
def search(
    q: str = Query(..., min_length=1),
    mode: str = Query("semantic", pattern="^(semantic|keyword|hybrid)$"),
    limit: int = Query(10, ge=1, le=50),
):
    cache_key = f"search:{mode}:{q}:{limit}"
    cached = redis.get_json(cache_key)
    if cached:
        return cached

    if mode == "semantic":
        results = semantic_search(q, limit)
    elif mode == "keyword":
        results = search_transcripts(q, limit)
    else:
        semantic = semantic_search(q, limit)
        keyword = search_transcripts(q, limit)
        seen = set()
        results = []
        for r in semantic + keyword:
            key = (r["video_id"], r["start_time"])
            if key not in seen:
                seen.add(key)
                results.append(r)
        results.sort(key=lambda x: x["score"], reverse=True)
        results = results[:limit]

    response = SearchResponse(
        query=q,
        results=[SearchResult(**r) for r in results],
        search_type=mode,
    )
    redis.set_json(cache_key, response.model_dump(), ttl=120)
    return response


@app.get("/api/search/timestamp")
def timestamp_search(
    q: str = Query(..., min_length=1),
    video_id: Optional[str] = None,
    limit: int = Query(5, ge=1, le=20),
):
    """Find exact timestamps where a topic is discussed."""
    results = semantic_search(q, limit * 3)
    if video_id:
        results = [r for r in results if r["video_id"] == video_id]
    return {
        "query": q,
        "segments": results[:limit],
    }
