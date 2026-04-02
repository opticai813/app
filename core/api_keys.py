import hashlib
import json
import secrets
from datetime import datetime, timezone
from threading import Lock
from uuid import uuid4

from fastapi import Header, HTTPException, status

from app.config import settings
from core.redis_runtime import redis_client


_client = redis_client()
_index_key = "optic:api_keys:index"
_lock = Lock()


def _timestamp() -> str:
    return datetime.now(timezone.utc).isoformat()


def _hash_key(raw_key: str) -> str:
    return hashlib.sha256(raw_key.encode("utf-8")).hexdigest()


def _load_records() -> list[dict]:
    raw = _client.get(_index_key)
    if not raw:
        return []
    return json.loads(raw)


def _save_records(records: list[dict]) -> list[dict]:
    _client.set(_index_key, json.dumps(records, separators=(",", ":")))
    return records


def _public_record(record: dict) -> dict:
    return {
        "id": record["id"],
        "name": record["name"],
        "prefix": record["prefix"],
        "scopes": record["scopes"],
        "enabled": record["enabled"],
        "created_at": record["created_at"],
        "created_by": record["created_by"],
        "last_used_at": record.get("last_used_at"),
    }


def list_api_keys() -> list[dict]:
    with _lock:
        records = _load_records()
    return [_public_record(item) for item in records]


def create_api_key(*, name: str, scopes: list[str], created_by: str) -> dict:
    raw_key = f"optic_{secrets.token_urlsafe(24)}"
    record = {
        "id": f"key-{uuid4().hex[:12]}",
        "name": name,
        "prefix": raw_key[:14],
        "key_hash": _hash_key(raw_key),
        "scopes": scopes,
        "enabled": True,
        "created_at": _timestamp(),
        "created_by": created_by,
        "last_used_at": None,
    }
    with _lock:
        records = _load_records()
        records.insert(0, record)
        _save_records(records)
    return {
        "api_key": raw_key,
        "record": _public_record(record),
    }


def revoke_api_key(key_id: str) -> None:
    with _lock:
        records = _load_records()
        for record in records:
            if record["id"] == key_id:
                record["enabled"] = False
                break
        _save_records(records)


def authenticate_api_key(raw_key: str) -> dict | None:
    key_hash = _hash_key(raw_key)
    with _lock:
        records = _load_records()
        match = next(
            (record for record in records if record["key_hash"] == key_hash and record.get("enabled", True)),
            None,
        )
        if not match:
            return None
        match["last_used_at"] = _timestamp()
        _save_records(records)
    return _public_record(match)


def require_api_key(x_optic_api_key: str | None = Header(default=None, alias="X-Optic-API-Key")) -> dict:
    if not x_optic_api_key:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing X-Optic-API-Key header.",
        )
    record = authenticate_api_key(x_optic_api_key)
    if not record:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid API key.",
        )
    return record
