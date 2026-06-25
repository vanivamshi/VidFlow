import uuid
from datetime import datetime
from typing import Optional

from sqlalchemy import BigInteger, Column, DateTime, Float, ForeignKey, String, Text, create_engine
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import DeclarativeBase, Session, sessionmaker

from shared.config import get_settings

settings = get_settings()
engine = create_engine(settings.postgres_url)
SessionLocal = sessionmaker(bind=engine)


class Base(DeclarativeBase):
    pass


class Video(Base):
    __tablename__ = "videos"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=True)
    title = Column(String(500), nullable=False)
    description = Column(Text)
    status = Column(String(50), default="uploading")
    raw_s3_key = Column(String(500))
    transcoded_s3_key = Column(String(500))
    thumbnail_s3_key = Column(String(500))
    duration_seconds = Column(Float)
    file_size_bytes = Column(BigInteger)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
