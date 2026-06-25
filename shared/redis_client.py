import json
from typing import Any, Optional

import redis


class RedisClient:
    def __init__(self, url: str):
        self._client = redis.from_url(url, decode_responses=True)

    def get(self, key: str) -> Optional[str]:
        return self._client.get(key)

    def set(self, key: str, value: str, ttl: int = 3600) -> None:
        self._client.setex(key, ttl, value)

    def get_json(self, key: str) -> Optional[Any]:
        raw = self.get(key)
        return json.loads(raw) if raw else None

    def set_json(self, key: str, value: Any, ttl: int = 3600) -> None:
        self.set(key, json.dumps(value), ttl)

    def incr_rate_limit(self, key: str, window: int = 60) -> int:
        pipe = self._client.pipeline()
        pipe.incr(key)
        pipe.expire(key, window)
        results = pipe.execute()
        return results[0]

    def delete(self, key: str) -> None:
        self._client.delete(key)
