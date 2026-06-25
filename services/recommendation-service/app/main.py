import time
from typing import Optional
from uuid import UUID

from fastapi import FastAPI, Query
from pydantic import BaseModel
from sqlalchemy import Column, String, create_engine, text
from sqlalchemy.dialects.postgresql import UUID as PGUUID
from sqlalchemy.orm import DeclarativeBase, sessionmaker

from shared.config import get_settings
from shared.logging_config import setup_logging
from shared.metrics import REQUEST_COUNT, REQUEST_LATENCY, setup_metrics
from shared.redis_client import RedisClient

settings = get_settings()
logger = setup_logging(settings.service_name)
app = FastAPI(title="Recommendation Service", version="1.0.0")
setup_metrics(app, settings.service_name)
redis = RedisClient(settings.redis_url)
engine = create_engine(settings.postgres_url)
Session = sessionmaker(bind=engine)


class VideoRec(BaseModel):
    video_id: str
    title: str
    score: float
    reason: str


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


@app.get("/api/recommendations", response_model=list[VideoRec])
def get_recommendations(
    user_id: Optional[UUID] = None,
    limit: int = Query(10, ge=1, le=50),
):
    cache_key = f"recs:{user_id or 'anonymous'}:{limit}"
    cached = redis.get_json(cache_key)
    if cached:
        return cached

    with Session() as session:
        rows = session.execute(text(
            "SELECT id, title FROM videos WHERE status = 'ready' "
            "ORDER BY created_at DESC LIMIT :limit"
        ), {"limit": limit}).fetchall()

    recs = [
        VideoRec(
            video_id=str(row.id),
            title=row.title,
            score=1.0 - (i * 0.05),
            reason="recently processed" if i < 3 else "trending",
        )
        for i, row in enumerate(rows)
    ]

    redis.set_json(cache_key, [r.model_dump() for r in recs], ttl=300)
    return recs


@app.get("/api/recommendations/similar/{video_id}", response_model=list[VideoRec])
def similar_videos(video_id: UUID, limit: int = Query(5, ge=1, le=20)):
    with Session() as session:
        rows = session.execute(text(
            "SELECT id, title FROM videos WHERE status = 'ready' AND id != :vid "
            "ORDER BY RANDOM() LIMIT :limit"
        ), {"vid": str(video_id), "limit": limit}).fetchall()

    return [
        VideoRec(video_id=str(r.id), title=r.title, score=0.7, reason="similar content")
        for r in rows
    ]
