"""Shared utilities for all AI Video Platform services."""

from .config import Settings, get_settings
from .kafka_client import KafkaProducer, KafkaConsumer
from .redis_client import RedisClient
from .metrics import setup_metrics, REQUEST_COUNT, REQUEST_LATENCY
from .logging_config import setup_logging

__all__ = [
    "Settings",
    "get_settings",
    "KafkaProducer",
    "KafkaConsumer",
    "RedisClient",
    "setup_metrics",
    "REQUEST_COUNT",
    "REQUEST_LATENCY",
    "setup_logging",
]
