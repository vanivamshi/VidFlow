import logging
import uuid
from datetime import datetime

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
        CREATE TABLE IF NOT EXISTS watch_events (
            user_id UUID,
            video_id UUID,
            event_time TIMESTAMP,
            event_type TEXT,
            watch_duration FLOAT,
            position_seconds FLOAT,
            PRIMARY KEY ((user_id), event_time, video_id)
        ) WITH CLUSTERING ORDER BY (event_time DESC)
    """)
    session.execute("""
        CREATE TABLE IF NOT EXISTS video_stats (
            video_id UUID PRIMARY KEY,
            view_count COUNTER,
            total_watch_seconds COUNTER,
            like_count COUNTER
        )
    """)
    logger.info("Analytics Cassandra initialized")


def record_watch_event(user_id: str, video_id: str, event_type: str,
                       watch_duration: float = 0, position: float = 0):
    if not session:
        init_cassandra()
    session.execute(
        SimpleStatement(
            "INSERT INTO watch_events (user_id, video_id, event_time, event_type, "
            "watch_duration, position_seconds) VALUES (%s, %s, %s, %s, %s, %s)"
        ),
        (user_id, video_id, datetime.utcnow(), event_type, watch_duration, position),
    )
    if event_type == "view":
        session.execute(
            "UPDATE video_stats SET view_count = view_count + 1 WHERE video_id = %s",
            (video_id,),
        )


def get_video_stats(video_id: str) -> dict:
    if not session:
        init_cassandra()
    row = session.execute(
        "SELECT view_count, total_watch_seconds, like_count FROM video_stats WHERE video_id = %s",
        (video_id,),
    ).one()
    if not row:
        return {"video_id": video_id, "view_count": 0, "total_watch_seconds": 0, "like_count": 0}
    return {
        "video_id": video_id,
        "view_count": row.view_count,
        "total_watch_seconds": row.total_watch_seconds,
        "like_count": row.like_count,
    }


def get_user_history(user_id: str, limit: int = 20) -> list[dict]:
    if not session:
        init_cassandra()
    rows = session.execute(
        "SELECT video_id, event_time, event_type, watch_duration, position_seconds "
        "FROM watch_events WHERE user_id = %s LIMIT %s",
        (user_id, limit),
    )
    return [{
        "video_id": str(r.video_id),
        "event_time": r.event_time.isoformat(),
        "event_type": r.event_type,
        "watch_duration": r.watch_duration,
        "position_seconds": r.position_seconds,
    } for r in rows]
