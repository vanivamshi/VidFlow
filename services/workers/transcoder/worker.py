"""FFmpeg transcoding worker — consumes video.uploaded events."""

import logging
import os
import subprocess
import tempfile
import uuid

import boto3
import httpx
from botocore.client import Config

from shared.config import get_settings
from shared.kafka_client import KafkaConsumer, KafkaProducer
from shared.logging_config import setup_logging

settings = get_settings()
logger = setup_logging("transcoder-worker")
BUCKET = "videos"


def get_s3():
    return boto3.client(
        "s3",
        endpoint_url=f"http://{settings.minio_endpoint}",
        aws_access_key_id=settings.minio_access_key,
        aws_secret_access_key=settings.minio_secret_key,
        config=Config(signature_version="s3v4"),
        region_name="us-east-1",
    )


def download_video(s3_key: str, dest: str):
    get_s3().download_file(BUCKET, s3_key, dest)


def upload_file(local_path: str, s3_key: str, content_type: str):
    get_s3().upload_file(local_path, BUCKET, s3_key, ExtraArgs={"ContentType": content_type})


def get_duration(path: str) -> float:
    result = subprocess.run(
        ["ffprobe", "-v", "error", "-show_entries", "format=duration",
         "-of", "default=noprint_wrappers=1:nokey=1", path],
        capture_output=True, text=True,
    )
    return float(result.stdout.strip() or 0)


def transcode(input_path: str, output_path: str):
    subprocess.run([
        "ffmpeg", "-i", input_path,
        "-c:v", "libx264", "-preset", "fast", "-crf", "23",
        "-c:a", "aac", "-b:a", "128k",
        "-movflags", "+faststart",
        output_path,
    ], check=True, capture_output=True)


def generate_thumbnail(input_path: str, output_path: str):
    subprocess.run([
        "ffmpeg", "-i", input_path, "-ss", "00:00:05",
        "-vframes", "1", "-q:v", "2", output_path,
    ], check=True, capture_output=True)


def update_video_status(video_id: str, status: str, **kwargs):
    httpx.patch(
        f"http://video-service:8000/api/videos/{video_id}/status",
        json={"status": status, **kwargs},
        timeout=30,
    )


def handle_event(event: dict):
    video_id = event["video_id"]
    s3_key = event["s3_key"]
    logger.info("Transcoding video %s", video_id)

    with tempfile.TemporaryDirectory() as tmpdir:
        raw_path = os.path.join(tmpdir, "raw.mp4")
        transcoded_path = os.path.join(tmpdir, "transcoded.mp4")
        thumb_path = os.path.join(tmpdir, "thumb.jpg")

        download_video(s3_key, raw_path)
        transcode(raw_path, transcoded_path)
        generate_thumbnail(raw_path, thumb_path)
        duration = get_duration(transcoded_path)

        transcoded_key = f"transcoded/{video_id}/video.mp4"
        thumb_key = f"thumbnails/{video_id}/thumb.jpg"
        upload_file(transcoded_path, transcoded_key, "video/mp4")
        upload_file(thumb_path, thumb_key, "image/jpeg")

        update_video_status(video_id, "transcribing",
                            transcoded_s3_key=transcoded_key,
                            thumbnail_s3_key=thumb_key,
                            duration_seconds=duration)

    producer = KafkaProducer(settings.kafka_bootstrap_servers)
    producer.publish("video.transcoded", video_id, {
        "video_id": video_id,
        "transcoded_s3_key": transcoded_key,
        "duration_seconds": duration,
    })
    logger.info("Transcoding complete: %s", video_id)


if __name__ == "__main__":
    consumer = KafkaConsumer(
        settings.kafka_bootstrap_servers,
        "transcoder-group",
        ["video.uploaded"],
    )
    consumer.consume(handle_event)
