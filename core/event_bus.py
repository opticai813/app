import json
from datetime import datetime, timezone
from typing import Iterator

from app.config import settings
from core.redis_runtime import redis_client


_client = redis_client()


def publish(event: dict) -> str:
    payload = dict(event)
    payload.setdefault("emitted_at", datetime.now(timezone.utc).isoformat())
    return _client.xadd(
        settings.stream_name,
        {"data": json.dumps(payload, separators=(",", ":"))},
    )


def listen(last_id: str = "$", block_ms: int = 1000) -> Iterator[dict]:
    cursor = last_id
    while True:
        messages = _client.xread({settings.stream_name: cursor}, block=block_ms)
        if not messages:
            continue

        for _, records in messages:
            for message_id, fields in records:
                cursor = message_id
                yield json.loads(fields["data"])
