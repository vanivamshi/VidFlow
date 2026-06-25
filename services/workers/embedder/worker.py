"""Embedding + summary generation worker — consumes video.transcribed events."""

import json
import logging
import uuid

import httpx
import psycopg2

from shared.config import get_settings
from shared.kafka_client import KafkaConsumer
from shared.logging_config import setup_logging
from vector_store import store_embedding

settings = get_settings()
logger = setup_logging("embedder-worker")


def generate_summary(segments: list[dict]) -> dict:
    full_text = " ".join(s["text"] for s in segments)
    words = full_text.split()
    summary = " ".join(words[:100]) + ("..." if len(words) > 100 else "")

    chapters = []
    for i, seg in enumerate(segments[:5]):
        chapters.append({
            "title": seg["text"][:60],
            "start_time": seg["start"],
            "end_time": seg["end"],
        })

    key_points = [seg["text"] for seg in segments[:3]]
    qa_pairs = [
        {"question": "What is this video about?", "answer": summary[:200]},
        {"question": "What topics are covered?", "answer": ", ".join(key_points[:2])},
    ]

    return {
        "summary": summary,
        "chapters": chapters,
        "key_points": key_points,
        "qa_pairs": qa_pairs,
    }


def store_summary(video_id: str, summary_data: dict):
    conn = psycopg2.connect(settings.postgres_url)
    cur = conn.cursor()
    cur.execute(
        "INSERT INTO video_summaries (video_id, summary, chapters, key_points, qa_pairs) "
        "VALUES (%s, %s, %s, %s, %s)",
        (
            video_id,
            summary_data["summary"],
            json.dumps(summary_data["chapters"]),
            json.dumps(summary_data["key_points"]),
            json.dumps(summary_data["qa_pairs"]),
        ),
    )
    conn.commit()
    cur.close()
    conn.close()


def update_video_ready(video_id: str):
    httpx.patch(
        f"http://video-service:8000/api/videos/{video_id}/status",
        json={"status": "ready"},
        timeout=30,
    )


def handle_event(event: dict):
    video_id = event["video_id"]
    segments = event["segments"]
    logger.info("Generating embeddings for video %s", video_id)

    for seg in segments:
        chunk_id = str(uuid.uuid4())
        store_embedding(video_id, chunk_id, seg["start"], seg["end"], seg["text"])

    summary_data = generate_summary(segments)
    store_summary(video_id, summary_data)
    update_video_ready(video_id)
    logger.info("Processing complete: %s", video_id)


if __name__ == "__main__":
    consumer = KafkaConsumer(
        settings.kafka_bootstrap_servers,
        "embedder-group",
        ["video.transcribed"],
    )
    consumer.consume(handle_event)
