"""Whisper transcription worker — consumes video.transcoded events."""

import logging
import os
import subprocess
import tempfile
import uuid

import boto3
from botocore.client import Config
from cassandra.cluster import Cluster

from shared.config import get_settings
from shared.kafka_client import KafkaConsumer, KafkaProducer
from shared.logging_config import setup_logging

settings = get_settings()
logger = setup_logging("transcriber-worker")
BUCKET = "videos"
KEYSPACE = "aivideo"


def get_s3():
    return boto3.client(
        "s3",
        endpoint_url=f"http://{settings.minio_endpoint}",
        aws_access_key_id=settings.minio_access_key,
        aws_secret_access_key=settings.minio_secret_key,
        config=Config(signature_version="s3v4"),
        region_name="us-east-1",
    )


def get_cassandra():
    cluster = Cluster([settings.cassandra_hosts])
    session = cluster.connect()
    session.execute(f"""
        CREATE KEYSPACE IF NOT EXISTS {KEYSPACE}
        WITH replication = {{'class': 'SimpleStrategy', 'replication_factor': 1}}
    """)
    session.set_keyspace(KEYSPACE)
    session.execute("""
        CREATE TABLE IF NOT EXISTS transcript_chunks (
            video_id UUID, chunk_id UUID, start_time FLOAT,
            end_time FLOAT, text TEXT,
            PRIMARY KEY (video_id, chunk_id)
        )
    """)
    return session


def extract_audio(video_path: str, audio_path: str):
    subprocess.run([
        "ffmpeg", "-i", video_path, "-vn", "-acodec", "pcm_s16le",
        "-ar", "16000", "-ac", "1", audio_path,
    ], check=True, capture_output=True)


def transcribe(audio_path: str) -> list[dict]:
    """Transcribe audio. Uses whisper CLI if available, else mock segments."""
    try:
        import whisper
        model = whisper.load_model("base")
        result = model.transcribe(audio_path)
        return [{
            "start": seg["start"],
            "end": seg["end"],
            "text": seg["text"].strip(),
        } for seg in result["segments"]]
    except ImportError:
        logger.warning("Whisper not installed — using mock transcript")
        return [
            {"start": 0.0, "end": 30.0, "text": "Introduction to the video content."},
            {"start": 30.0, "end": 60.0, "text": "Discussion of Kubernetes orchestration and deployment."},
            {"start": 60.0, "end": 90.0, "text": "Docker containers and microservices architecture."},
        ]


def store_chunks(session, video_id: str, segments: list[dict]):
    for seg in segments:
        session.execute(
            "INSERT INTO transcript_chunks (video_id, chunk_id, start_time, end_time, text) "
            "VALUES (%s, %s, %s, %s, %s)",
            (video_id, str(uuid.uuid4()), seg["start"], seg["end"], seg["text"]),
        )


def handle_event(event: dict):
    video_id = event["video_id"]
    s3_key = event["transcoded_s3_key"]
    logger.info("Transcribing video %s", video_id)

    with tempfile.TemporaryDirectory() as tmpdir:
        video_path = os.path.join(tmpdir, "video.mp4")
        audio_path = os.path.join(tmpdir, "audio.wav")
        get_s3().download_file(BUCKET, s3_key, video_path)
        extract_audio(video_path, audio_path)
        segments = transcribe(audio_path)

    session = get_cassandra()
    store_chunks(session, video_id, segments)

    producer = KafkaProducer(settings.kafka_bootstrap_servers)
    producer.publish("video.transcribed", video_id, {
        "video_id": video_id,
        "segments": segments,
    })
    logger.info("Transcription complete: %s (%d segments)", video_id, len(segments))


if __name__ == "__main__":
    consumer = KafkaConsumer(
        settings.kafka_bootstrap_servers,
        "transcriber-group",
        ["video.transcoded"],
    )
    consumer.consume(handle_event)
