from pydantic import BaseModel
from typing import Optional
from uuid import UUID
from datetime import datetime


class VideoCreate(BaseModel):
    title: str
    description: Optional[str] = None
    user_id: Optional[UUID] = None


class VideoResponse(BaseModel):
    id: UUID
    user_id: Optional[UUID]
    title: str
    description: Optional[str]
    status: str
    raw_s3_key: Optional[str]
    transcoded_s3_key: Optional[str]
    thumbnail_s3_key: Optional[str]
    duration_seconds: Optional[float]
    file_size_bytes: Optional[int]
    created_at: datetime
    playback_url: Optional[str] = None
    thumbnail_url: Optional[str] = None

    class Config:
        from_attributes = True


class VideoStatusUpdate(BaseModel):
    status: str
    transcoded_s3_key: Optional[str] = None
    thumbnail_s3_key: Optional[str] = None
    duration_seconds: Optional[float] = None
