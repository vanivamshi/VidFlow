import time
from typing import Optional
from uuid import UUID

from fastapi import Depends, FastAPI, File, Form, HTTPException, UploadFile
from sqlalchemy.orm import Session

from shared.config import get_settings
from shared.kafka_client import KafkaProducer
from shared.logging_config import setup_logging
from shared.metrics import REQUEST_COUNT, REQUEST_LATENCY, setup_metrics
from shared.redis_client import RedisClient

from .database import Video, get_db
from .schemas import VideoCreate, VideoResponse, VideoStatusUpdate
from .storage import get_presigned_url, upload_video

settings = get_settings()
logger = setup_logging(settings.service_name)
app = FastAPI(title="Video Service", version="1.0.0")
setup_metrics(app, settings.service_name)

kafka = KafkaProducer(settings.kafka_bootstrap_servers)
redis = RedisClient(settings.redis_url)


@app.middleware("http")
async def metrics_middleware(request, call_next):
    start = time.time()
    response = await call_next(request)
    duration = time.time() - start
    endpoint = request.url.path
    REQUEST_COUNT.labels(settings.service_name, request.method, endpoint, response.status_code).inc()
    REQUEST_LATENCY.labels(settings.service_name, request.method, endpoint).observe(duration)
    return response


@app.get("/health")
def health():
    return {"status": "healthy", "service": settings.service_name}


@app.post("/api/videos/upload", response_model=VideoResponse)
async def upload_video_endpoint(
    title: str = Form(...),
    description: Optional[str] = Form(None),
    user_id: Optional[str] = Form(None),
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
):
    content = await file.read()
    s3_key = upload_video(content, file.filename, file.content_type or "video/mp4")

    video = Video(
        title=title,
        description=description,
        user_id=user_id,
        status="processing",
        raw_s3_key=s3_key,
        file_size_bytes=len(content),
    )
    db.add(video)
    db.commit()
    db.refresh(video)

    kafka.publish("video.uploaded", str(video.id), {
        "video_id": str(video.id),
        "s3_key": s3_key,
        "title": title,
    })

    logger.info("Video uploaded: %s", video.id)
    return _to_response(video)


@app.get("/api/videos/{video_id}", response_model=VideoResponse)
def get_video(video_id: UUID, db: Session = Depends(get_db)):
    cache_key = f"video:{video_id}"
    cached = redis.get_json(cache_key)
    if cached:
        return cached

    video = db.query(Video).filter(Video.id == video_id).first()
    if not video:
        raise HTTPException(status_code=404, detail="Video not found")

    response = _to_response(video)
    redis.set_json(cache_key, response.model_dump(mode="json"), ttl=300)
    return response


@app.get("/api/videos", response_model=list[VideoResponse])
def list_videos(skip: int = 0, limit: int = 20, db: Session = Depends(get_db)):
    videos = db.query(Video).order_by(Video.created_at.desc()).offset(skip).limit(limit).all()
    return [_to_response(v) for v in videos]


@app.patch("/api/videos/{video_id}/status", response_model=VideoResponse)
def update_status(video_id: UUID, update: VideoStatusUpdate, db: Session = Depends(get_db)):
    video = db.query(Video).filter(Video.id == video_id).first()
    if not video:
        raise HTTPException(status_code=404, detail="Video not found")

    video.status = update.status
    if update.transcoded_s3_key:
        video.transcoded_s3_key = update.transcoded_s3_key
    if update.thumbnail_s3_key:
        video.thumbnail_s3_key = update.thumbnail_s3_key
    if update.duration_seconds:
        video.duration_seconds = update.duration_seconds

    db.commit()
    db.refresh(video)
    redis.delete(f"video:{video_id}")
    return _to_response(video)


def _to_response(video: Video) -> VideoResponse:
    resp = VideoResponse.model_validate(video)
    if video.transcoded_s3_key:
        resp.playback_url = get_presigned_url(video.transcoded_s3_key)
    elif video.raw_s3_key:
        resp.playback_url = get_presigned_url(video.raw_s3_key)
    if video.thumbnail_s3_key:
        resp.thumbnail_url = get_presigned_url(video.thumbnail_s3_key)
    return resp
