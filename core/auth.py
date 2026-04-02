import hashlib
import json
import secrets
from datetime import datetime, timezone

from fastapi import Header, HTTPException, status

from app.config import settings
from core.control_plane import control_plane_snapshot, touch_operator_login
from core.redis_runtime import redis_client


_client = redis_client()
_session_prefix = "optic:session:"


def _timestamp() -> str:
    return datetime.now(timezone.utc).isoformat()


def _password_hash(password: str) -> str:
    return hashlib.sha256(password.encode("utf-8")).hexdigest()


def _session_key(token: str) -> str:
    return f"{_session_prefix}{token}"


def authenticate(email: str, password: str) -> dict | None:
    control_plane = control_plane_snapshot(sanitized=False)
    expected = _password_hash(password)
    for operator in control_plane.get("operators", []):
        if operator.get("email", "").lower() != email.lower():
            continue
        if operator.get("status") != "active":
            return None
        if operator.get("password_hash") != expected:
            return None
        return {
            "operator_id": operator["id"],
            "email": operator["email"],
            "name": operator["name"],
            "role": operator["role"],
            "permissions": operator.get("permissions", []),
        }
    return None


def create_session(identity: dict) -> dict:
    token = secrets.token_urlsafe(32)
    session = {
        "token": token,
        **identity,
        "created_at": _timestamp(),
        "last_seen_at": _timestamp(),
        "expires_in_seconds": settings.session_ttl_seconds,
    }
    _client.setex(
        _session_key(token),
        settings.session_ttl_seconds,
        json.dumps(session, separators=(",", ":")),
    )
    touch_operator_login(identity["operator_id"])
    return session


def read_session(token: str) -> dict | None:
    raw = _client.get(_session_key(token))
    if not raw:
        return None
    session = json.loads(raw)
    session["last_seen_at"] = _timestamp()
    _client.setex(
        _session_key(token),
        settings.session_ttl_seconds,
        json.dumps(session, separators=(",", ":")),
    )
    return session


def revoke_session(token: str) -> None:
    _client.delete(_session_key(token))


def token_from_header(authorization: str | None) -> str | None:
    if not authorization:
        return None
    scheme, _, token = authorization.partition(" ")
    if scheme.lower() != "bearer" or not token:
        return None
    return token.strip()


def require_session(authorization: str | None = Header(default=None)) -> dict:
    token = token_from_header(authorization)
    if not token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing bearer token.",
        )
    session = read_session(token)
    if not session:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Session expired or invalid.",
        )
    return session
