from dataclasses import dataclass
import os


def _split_origins(value: str) -> tuple[str, ...]:
    return tuple(origin.strip() for origin in value.split(",") if origin.strip())


@dataclass(frozen=True)
class Settings:
    platform_name: str = os.getenv("PLATFORM_NAME", "Optic PIE Control")
    redis_host: str = os.getenv("REDIS_HOST", "127.0.0.1")
    redis_port: int = int(os.getenv("REDIS_PORT", "6379"))
    stream_name: str = os.getenv("STREAM_NAME", "optic_stream")
    camera_source: str = os.getenv("CAMERA_SOURCE", "demo")
    frame_interval_ms: int = int(os.getenv("FRAME_INTERVAL_MS", "250"))
    capture_width: int = int(os.getenv("CAPTURE_WIDTH", "960"))
    capture_height: int = int(os.getenv("CAPTURE_HEIGHT", "540"))
    max_recent_events: int = int(os.getenv("MAX_RECENT_EVENTS", "18"))
    max_preview_width: int = int(os.getenv("MAX_PREVIEW_WIDTH", "960"))
    detection_confidence: float = float(os.getenv("DETECTION_CONFIDENCE", "0.35"))
    alert_confidence: float = float(os.getenv("ALERT_CONFIDENCE", "0.85"))
    yolo_model: str = os.getenv("YOLO_MODEL", "yolov8n.pt")
    session_ttl_seconds: int = int(os.getenv("SESSION_TTL_SECONDS", "28800"))
    admin_email: str = os.getenv("OPTIC_ADMIN_EMAIL", "admin@opticcontrol.ai")
    admin_password: str = os.getenv("OPTIC_ADMIN_PASSWORD", "OpticPlatform!2026")
    ui_origins: tuple[str, ...] = _split_origins(
        os.getenv(
            "UI_ORIGINS",
            "http://localhost:5173,http://localhost:4173,http://127.0.0.1:4312,http://127.0.0.1:4314",
        )
    )

    @property
    def camera_mode(self) -> str:
        return "demo" if self.camera_source.lower() == "demo" else "live"

    @property
    def resolved_camera_source(self) -> int | str:
        source = self.camera_source.strip()
        if source.isdigit():
            return int(source)
        return source


settings = Settings()
