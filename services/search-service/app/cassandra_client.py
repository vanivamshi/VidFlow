import hashlib
import logging

from cassandra.cluster import Cluster
from cassandra.query import SimpleStatement

from shared.config import get_settings

logger = logging.getLogger(__name__)
settings = get_settings()

KEYSPACE = "aivideo"
cluster = None
session = None


def init_cassandra():
    global cluster, session
    cluster = Cluster([settings.cassandra_hosts])
    session = cluster.connect()
    session.execute(f"""
        CREATE KEYSPACE IF NOT EXISTS {KEYSPACE}
        WITH replication = {{'class': 'SimpleStrategy', 'replication_factor': 1}}
    """)
    session.set_keyspace(KEYSPACE)
    session.execute("""
        CREATE TABLE IF NOT EXISTS transcript_chunks (
            video_id UUID,
            chunk_id UUID,
            start_time FLOAT,
            end_time FLOAT,
            text TEXT,
            PRIMARY KEY (video_id, chunk_id)
        )
    """)
    session.execute("""
        CREATE TABLE IF NOT EXISTS search_index (
            query_hash TEXT,
            video_id UUID,
            start_time FLOAT,
            end_time FLOAT,
            text TEXT,
            score FLOAT,
            PRIMARY KEY (query_hash, video_id, start_time)
        )
    """)
    logger.info("Cassandra initialized")


def store_transcript_chunk(video_id: str, chunk_id: str, start: float, end: float, text: str):
    if not session:
        init_cassandra()
    session.execute(
        SimpleStatement(
            "INSERT INTO transcript_chunks (video_id, chunk_id, start_time, end_time, text) "
            "VALUES (%s, %s, %s, %s, %s)"
        ),
        (video_id, chunk_id, start, end, text),
    )


def search_transcripts(query: str, limit: int = 10) -> list[dict]:
    if not session:
        init_cassandra()
    rows = session.execute(
        "SELECT video_id, start_time, end_time, text FROM transcript_chunks ALLOW FILTERING"
    )
    query_lower = query.lower()
    results = []
    for row in rows:
        if query_lower in row.text.lower():
            results.append({
                "video_id": str(row.video_id),
                "start_time": row.start_time,
                "end_time": row.end_time,
                "text": row.text,
                "score": 0.8,
            })
    return results[:limit]
