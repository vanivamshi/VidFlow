import time
from typing import Optional
from uuid import UUID

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel

from shared.config import get_settings
from shared.kafka_client import KafkaProducer
from shared.logging_config import setup_logging
from shared.metrics import REQUEST_COUNT, REQUEST_LATENCY, setup_metrics
from shared.redis_client import RedisClient

from .cassandra_client import get_user_history, get_video_stats, init_cassandra, record_watch_event

settings = get_settings()
logger = setup_logging(settings.service_name)
app = FastAPI(title="Analytics Service", version="1.0.0")
setup_metrics(app, settings.service_name)
kafka = KafkaProducer(settings.kafka_bootstrap_servers)
redis = RedisClient(settings.redis_url)


class WatchEvent(BaseModel):
    user_id: UUID
    video_id: UUID
    event_type: str
    watch_duration: float = 0
    position_seconds: float = 0


@app.on_event("startup")
def startup():
    try:
        init_cassandra()
    except Exception as e:
        logger.warning("Cassandra not ready: %s", e)


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


@app.post("/api/analytics/events")
def track_event(event: WatchEvent):
    record_watch_event(
        str(event.user_id), str(event.video_id),
        event.event_type, event.watch_duration, event.position_seconds,
    )
    kafka.publish("analytics.event", str(event.video_id), event.model_dump(mode="json"))
    return {"status": "recorded"}


@app.get("/api/analytics/videos/{video_id}/stats")
def video_stats(video_id: UUID):
    cache_key = f"stats:{video_id}"
    cached = redis.get_json(cache_key)
    if cached:
        return cached
    stats = get_video_stats(str(video_id))
    redis.set_json(cache_key, stats, ttl=60)
    return stats


@app.get("/api/analytics/users/{user_id}/history")
def user_history(user_id: UUID, limit: int = 20):
    return {"user_id": str(user_id), "events": get_user_history(str(user_id), limit)}
