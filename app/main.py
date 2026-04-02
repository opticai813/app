import base64
from contextlib import asynccontextmanager
from pathlib import Path
from threading import Event, Thread

import cv2
import numpy as np
from fastapi import Body, Depends, FastAPI, Header, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from pydantic import BaseModel, Field

from app.config import settings
from core.api_keys import create_api_key, list_api_keys, require_api_key, revoke_api_key
from core.auth import authenticate, create_session, require_session, revoke_session, token_from_header
from core.control_plane import control_plane_snapshot, initialize_control_plane, update_control_plane
from core.event_bus import listen, publish
from core.feed_catalog import get_catalog_template, search_feed_catalog
from core.feed_discovery import scrape_public_feed_page
from core.state import (
    alerts,
    asset_scans,
    brain_chat,
    dashboard_snapshot,
    descriptions,
    events,
    initialize_dashboard,
    mark_runtime,
    record_alert,
    record_asset_scan,
    record_brain_chat,
    record_detection,
    record_description,
    record_training_plan,
    tracks,
)
from services.agent.agent import evaluate
from services.agent.brain import analyze_object_scan, answer_brain_chat
from services.agent.descriptor import describe_event, describe_payload
from services.agent.training import build_training_workspace, generate_training_plan
from services.ingestion.camera import fetch_public_snapshot_frame, start_camera
from services.perception.detector import Detector


UI_DASHBOARD = Path(__file__).resolve().parent.parent / "ui" / "dashboard.html"


class LoginRequest(BaseModel):
    email: str
    password: str


class ApiKeyCreateRequest(BaseModel):
    name: str
    scopes: list[str] = ["dashboard:read", "descriptions:generate"]


class DescriptionRequest(BaseModel):
    source_name: str
    source_type: str = "sensor"
    modality: str = "data"
    zone: str = "unknown area"
    observations: list[dict] = Field(default_factory=list)
    context: str | None = None


class BrowserObserveRequest(BaseModel):
    image_base64: str
    source_name: str = "Device Camera"
    source_type: str = "camera"
    modality: str = "video"
    zone: str = "device_view"
    connector_type: str = "browser"
    analysis_mode: str = "object-detection"
    description_prompt: str | None = None


class SourceObserveRequest(BaseModel):
    source_name: str
    source_uri: str
    source_type: str = "cctv"
    modality: str = "video"
    zone: str = "monitored_area"
    connector_type: str = "rtsp"
    analysis_mode: str = "object-detection"
    description_prompt: str | None = None


class FeedScrapeRequest(BaseModel):
    page_url: str
    source_type: str | None = None


class ObjectScanRequest(BaseModel):
    image_base64: str
    source_name: str = "Device Scanner"
    zone: str = "scan_bay"
    scan_target: str = "vehicle"
    connector_type: str = "browser"
    context: str | None = None


class BrainChatRequest(BaseModel):
    message: str
    asset_scan_id: str | None = None
    scope: str = "auto"


class TrainingPlanRequest(BaseModel):
    mode: str = "robotics"
    asset_scan_id: str | None = None
    objective: str | None = None
    target_class: str | None = None
    operating_domain: str | None = None
    autonomy_level: str | None = None
    automation_goal: str | None = None
    notes: str | None = None


def _stream_safe_detection_event(result: dict) -> dict:
    return {
        "type": "detections",
        "source": result["source"],
        "feed_id": result["feed_id"],
        "camera_id": result["camera_id"],
        "camera_label": result["camera_label"],
        "frame_id": result["frame_id"],
        "captured_at": result["captured_at"],
        "processed_at": result["processed_at"],
        "detected_count": result["detected_count"],
        "active_track_count": len(result["active_tracks"]),
        "detections": [
            {
                "track_id": item["track_id"],
                "global_identity_id": item.get("global_identity_id"),
                "identity_label": item.get("identity_label"),
                "label": item["label"],
                "class_id": item["class_id"],
                "confidence": item["confidence"],
                "bbox": item["bbox"],
                "zone": item["zone"],
            }
            for item in result["detections"]
        ],
        "metadata": result["metadata"],
    }


def _decode_image_payload(payload: str) -> np.ndarray:
    raw = payload
    if "," in payload and payload.split(",", 1)[0].startswith("data:"):
        raw = payload.split(",", 1)[1]
    image_bytes = base64.b64decode(raw)
    array = np.frombuffer(image_bytes, np.uint8)
    frame = cv2.imdecode(array, cv2.IMREAD_COLOR)
    if frame is None:
        raise HTTPException(status_code=400, detail="Unable to decode image payload.")
    return frame


def _simulated_object(
    *,
    label: str,
    class_id: int,
    bbox: list[int],
    confidence: float,
    identity_hint: str,
    display_name: str,
) -> dict:
    return {
        "label": label,
        "class_id": class_id,
        "bbox": bbox,
        "confidence": confidence,
        "identity_hint": identity_hint,
        "display_name": display_name,
    }


def _synthetic_source_payload(
    source_name: str,
    source_type: str,
    zone: str,
    connector_type: str,
) -> tuple[np.ndarray, list[dict]]:
    width = settings.capture_width
    height = settings.capture_height
    frame = np.zeros((height, width, 3), dtype=np.uint8)
    normalized_type = (source_type or "cctv").lower()
    simulated_objects: list[dict] = []

    if normalized_type == "satellite":
        frame[:] = (54, 86, 62)
        cv2.rectangle(frame, (0, 0), (width, int(height * 0.18)), (104, 136, 88), -1)
        cv2.rectangle(frame, (int(width * 0.08), int(height * 0.28)), (int(width * 0.3), int(height * 0.52)), (90, 108, 112), -1)
        cv2.rectangle(frame, (int(width * 0.42), int(height * 0.22)), (int(width * 0.76), int(height * 0.44)), (118, 128, 126), -1)
        cv2.rectangle(frame, (int(width * 0.62), int(height * 0.58)), (int(width * 0.88), int(height * 0.82)), (100, 112, 116), -1)
        cv2.line(frame, (int(width * 0.1), int(height * 0.95)), (int(width * 0.94), int(height * 0.1)), (188, 194, 178), 18)
        cv2.line(frame, (int(width * 0.04), int(height * 0.64)), (int(width * 0.82), int(height * 0.64)), (188, 194, 178), 12)
        cv2.rectangle(frame, (int(width * 0.34), int(height * 0.6)), (int(width * 0.38), int(height * 0.66)), (222, 240, 240), -1)
        cv2.rectangle(frame, (int(width * 0.58), int(height * 0.47)), (int(width * 0.62), int(height * 0.53)), (222, 240, 240), -1)
        cv2.rectangle(frame, (int(width * 0.78), int(height * 0.28)), (int(width * 0.82), int(height * 0.34)), (222, 240, 240), -1)
        simulated_objects = [
            _simulated_object(
                label="truck",
                class_id=7,
                bbox=[int(width * 0.32), int(height * 0.58), int(width * 0.4), int(height * 0.68)],
                confidence=0.88,
                identity_hint="asset-orbit-1",
                display_name="Orbital Truck",
            ),
            _simulated_object(
                label="car",
                class_id=2,
                bbox=[int(width * 0.56), int(height * 0.45), int(width * 0.64), int(height * 0.55)],
                confidence=0.84,
                identity_hint="asset-orbit-2",
                display_name="Orbital Sedan",
            ),
        ]
    else:
        frame[:] = (16, 24, 38)
        cv2.rectangle(frame, (0, int(height * 0.7)), (width, height), (24, 36, 52), -1)
        cv2.rectangle(frame, (int(width * 0.08), int(height * 0.2)), (int(width * 0.32), int(height * 0.62)), (46, 58, 78), -1)
        cv2.rectangle(frame, (int(width * 0.66), int(height * 0.16)), (int(width * 0.92), int(height * 0.58)), (42, 52, 72), -1)
        cv2.line(frame, (0, int(height * 0.82)), (width, int(height * 0.82)), (196, 200, 188), 8)
        cv2.rectangle(frame, (int(width * 0.18), int(height * 0.62)), (int(width * 0.34), int(height * 0.82)), (86, 198, 250), 3)
        cv2.rectangle(frame, (int(width * 0.46), int(height * 0.6)), (int(width * 0.7), int(height * 0.8)), (82, 214, 160), 3)
        cv2.rectangle(frame, (int(width * 0.78), int(height * 0.48)), (int(width * 0.84), int(height * 0.76)), (244, 202, 96), 3)
        simulated_objects = [
            _simulated_object(
                label="person",
                class_id=0,
                bbox=[int(width * 0.2), int(height * 0.44), int(width * 0.28), int(height * 0.78)],
                confidence=0.93,
                identity_hint="identity-echo",
                display_name="Echo Subject",
            ),
            _simulated_object(
                label="truck",
                class_id=7,
                bbox=[int(width * 0.44), int(height * 0.56), int(width * 0.74), int(height * 0.8)],
                confidence=0.87,
                identity_hint="asset-atlas",
                display_name="Atlas Truck",
            ),
        ]

    cv2.putText(
        frame,
        f"OPTIC LIVE / {source_name.upper()}",
        (24, 36),
        cv2.FONT_HERSHEY_SIMPLEX,
        0.82,
        (240, 247, 255),
        2,
        cv2.LINE_AA,
    )
    cv2.putText(
        frame,
        f"{normalized_type} | {connector_type} | zone {zone}",
        (24, 70),
        cv2.FONT_HERSHEY_SIMPLEX,
        0.58,
        (166, 226, 255),
        1,
        cv2.LINE_AA,
    )
    return frame, simulated_objects


def _capture_source_frame(
    source_uri: str,
    *,
    source_name: str,
    source_type: str,
    connector_type: str,
    zone: str,
) -> tuple[np.ndarray, list[dict] | None, str]:
    uri = (source_uri or "").strip()
    normalized_type = (source_type or "cctv").lower()
    normalized_connector = (connector_type or "rtsp").lower()
    if not uri:
        raise HTTPException(status_code=400, detail="Source URI is required.")

    if uri.lower().startswith(("http://", "https://")):
        frame = fetch_public_snapshot_frame(uri, settings.capture_width, settings.capture_height)
        if frame is None:
            raise HTTPException(status_code=400, detail=f"Unable to fetch a current image from '{source_uri}'.")
        return frame, None, "live"

    if uri.lower().startswith("demo://") or normalized_connector == "stac":
        frame, simulated_objects = _synthetic_source_payload(
            source_name,
            normalized_type,
            zone,
            normalized_connector,
        )
        return frame, simulated_objects, "demo"

    source = int(uri) if uri.isdigit() else uri
    capture = cv2.VideoCapture(source)
    try:
        if not capture.isOpened():
            raise HTTPException(status_code=400, detail=f"Unable to open source '{source_uri}'.")
        ok, frame = capture.read()
        if not ok or frame is None:
            raise HTTPException(status_code=400, detail=f"Unable to read a frame from '{source_uri}'.")
        return frame, None, "live"
    finally:
        capture.release()


def _commit_analysis(result: dict) -> tuple[dict, dict | None]:
    description = describe_event(result)
    record_detection(result)
    record_description(description)
    publish(_stream_safe_detection_event(result))
    decision = evaluate(result)
    if decision:
        record_alert(decision)
        publish(decision)
    return description, decision


def _analysis_response(
    result: dict,
    description: dict,
    decision: dict | None = None,
    asset_scan: dict | None = None,
) -> dict:
    return {
        "runtime": {
            "source": result["camera_label"],
            "model": result["model"],
            "zone": result["zone"],
            "source_type": result["metadata"]["source_type"],
            "modality": result["metadata"]["modality"],
            "connector_type": result["metadata"]["connector_type"],
            "analysis_mode": result["metadata"]["analysis_mode"],
        },
        "preview_image": result["preview_image"],
        "detections": result["detections"],
        "perceived_meanings": result["perceived_meanings"],
        "active_tracks": result["active_tracks"],
        "active_identities": result["active_identities"],
        "alerts": (decision or {}).get("alerts", []),
        "description": description,
        "asset_scan": asset_scan,
    }


class PipelineRuntime:
    def __init__(self) -> None:
        self.stop_event = Event()
        self.detector = Detector()
        self.threads: list[Thread] = []

    def start(self) -> None:
        initialize_control_plane()
        initialize_dashboard(settings.camera_source, settings.camera_mode)
        mark_runtime(
            status="starting",
            source=settings.camera_source,
            mode=settings.camera_mode,
            model=settings.yolo_model,
        )
        self.threads = [
            Thread(target=self._run_camera, name="optic-camera", daemon=True),
            Thread(target=self._run_pipeline, name="optic-pipeline", daemon=True),
        ]
        for thread in self.threads:
            thread.start()

    def stop(self) -> None:
        self.stop_event.set()
        for thread in self.threads:
            thread.join(timeout=2.0)
        mark_runtime(status="stopped")

    def _run_camera(self) -> None:
        try:
            start_camera(self.stop_event)
        except Exception as exc:
            mark_runtime(status="degraded", error=f"Camera loop failed: {exc}")

    def _run_pipeline(self) -> None:
        try:
            for event in listen(block_ms=1000):
                if self.stop_event.is_set():
                    break
                if event.get("type") != "frame":
                    continue

                result = self.detector.process(event)
                if not result:
                    continue

                record_detection(result)
                record_description(describe_event(result))
                publish(_stream_safe_detection_event(result))

                decision = evaluate(result)
                if decision:
                    record_alert(decision)
                    publish(decision)
        except Exception as exc:
            mark_runtime(status="degraded", error=f"Pipeline loop failed: {exc}")


runtime = PipelineRuntime()


@asynccontextmanager
async def lifespan(_: FastAPI):
    runtime.start()
    try:
        yield
    finally:
        runtime.stop()


app = FastAPI(
    title="Optic PIE API",
    version="0.2.0",
    summary="Perception Infrastructure Engine backend and control plane for Optic.",
    lifespan=lifespan,
)
app.add_middleware(
    CORSMiddleware,
    allow_origins=list(settings.ui_origins) or ["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/")
def root() -> FileResponse:
    return FileResponse(UI_DASHBOARD)


@app.get("/dashboard")
def dashboard_page() -> FileResponse:
    return FileResponse(UI_DASHBOARD)


@app.get("/health")
def health() -> dict:
    dashboard = dashboard_snapshot()
    return {
        "status": dashboard["runtime"]["status"],
        "source": dashboard["runtime"]["source"],
        "mode": dashboard["runtime"]["mode"],
        "cameras": len(dashboard.get("cameras", [])),
    }


@app.get("/api/dashboard")
def api_dashboard() -> dict:
    return dashboard_snapshot()


@app.get("/api/events")
def api_events(limit: int = Query(default=10, ge=1, le=50)) -> list[dict]:
    return events(limit)


@app.get("/api/alerts")
def api_alerts(limit: int = Query(default=10, ge=1, le=50)) -> list[dict]:
    return alerts(limit)


@app.get("/api/tracks")
def api_tracks(limit: int = Query(default=10, ge=1, le=50)) -> list[dict]:
    return tracks(limit)


@app.get("/api/descriptions")
def api_descriptions(limit: int = Query(default=10, ge=1, le=50)) -> list[dict]:
    return descriptions(limit)


@app.get("/api/object-scans")
def api_object_scans(limit: int = Query(default=10, ge=1, le=50)) -> list[dict]:
    return asset_scans(limit)


@app.get("/api/brain-chat")
def api_brain_chat(limit: int = Query(default=10, ge=1, le=50)) -> list[dict]:
    return brain_chat(limit)


@app.post("/api/auth/login")
def api_login(payload: LoginRequest) -> dict:
    identity = authenticate(payload.email, payload.password)
    if not identity:
        raise HTTPException(status_code=401, detail="Invalid credentials.")
    session = create_session(identity)
    return {
        "token": session["token"],
        "session": {
            "operator_id": session["operator_id"],
            "email": session["email"],
            "name": session["name"],
            "role": session["role"],
            "permissions": session["permissions"],
            "created_at": session["created_at"],
            "expires_in_seconds": session["expires_in_seconds"],
        },
    }


@app.get("/api/auth/session")
def api_session(session: dict = Depends(require_session)) -> dict:
    return {
        "operator_id": session["operator_id"],
        "email": session["email"],
        "name": session["name"],
        "role": session["role"],
        "permissions": session["permissions"],
        "created_at": session["created_at"],
        "last_seen_at": session["last_seen_at"],
        "expires_in_seconds": session["expires_in_seconds"],
    }


@app.post("/api/auth/logout")
def api_logout(
    authorization: str | None = Header(default=None),
    _: dict = Depends(require_session),
) -> dict:
    token = token_from_header(authorization)
    if token:
        revoke_session(token)
    return {"status": "ok"}


@app.get("/api/platform/bootstrap")
def api_platform_bootstrap(session: dict = Depends(require_session)) -> dict:
    dashboard = dashboard_snapshot()
    control_plane = control_plane_snapshot()
    return {
        "session": {
            "operator_id": session["operator_id"],
            "email": session["email"],
            "name": session["name"],
            "role": session["role"],
            "permissions": session["permissions"],
        },
        "dashboard": dashboard,
        "control_plane": control_plane,
        "training": build_training_workspace(dashboard, control_plane),
    }


@app.get("/api/platform/control-plane")
def api_control_plane(_: dict = Depends(require_session)) -> dict:
    return control_plane_snapshot()


@app.put("/api/platform/control-plane")
def api_update_control_plane(
    payload: dict = Body(...),
    _: dict = Depends(require_session),
) -> dict:
    update_control_plane(payload)
    return {
        "status": "updated",
        "control_plane": control_plane_snapshot(),
        "dashboard": dashboard_snapshot(),
    }


@app.get("/api/platform/feed-catalog")
def api_feed_catalog(
    query: str = Query(default=""),
    source_type: str = Query(default=""),
    _: dict = Depends(require_session),
) -> dict:
    return {
        "results": search_feed_catalog(query=query, source_type=source_type or None),
    }


@app.get("/api/platform/feed-catalog/{template_id}")
def api_feed_catalog_template(
    template_id: str,
    _: dict = Depends(require_session),
) -> dict:
    template = get_catalog_template(template_id)
    if not template:
        raise HTTPException(status_code=404, detail="Catalog template not found.")
    return template


@app.post("/api/platform/feed-scrape")
def api_feed_scrape(
    payload: FeedScrapeRequest,
    _: dict = Depends(require_session),
) -> dict:
    try:
        results = scrape_public_feed_page(
            payload.page_url,
            source_type=payload.source_type,
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except Exception as exc:
        raise HTTPException(status_code=502, detail=f"Public feed scrape failed: {exc}") from exc
    return {
        "results": results,
        "page_url": payload.page_url,
    }


@app.get("/api/platform/training")
def api_platform_training(_: dict = Depends(require_session)) -> dict:
    dashboard = dashboard_snapshot()
    control_plane = control_plane_snapshot()
    return build_training_workspace(dashboard, control_plane)


@app.post("/api/platform/training/plan")
def api_platform_training_plan(
    payload: TrainingPlanRequest,
    _: dict = Depends(require_session),
) -> dict:
    dashboard = dashboard_snapshot()
    control_plane = control_plane_snapshot()
    plan = generate_training_plan(
        mode=payload.mode,
        dashboard=dashboard,
        control_plane=control_plane,
        asset_scan_id=payload.asset_scan_id,
        objective=payload.objective,
        target_class=payload.target_class,
        operating_domain=payload.operating_domain,
        autonomy_level=payload.autonomy_level,
        automation_goal=payload.automation_goal,
        notes=payload.notes,
    )
    record_training_plan(plan)
    return plan


@app.get("/api/platform/object-scans")
def api_platform_object_scans(
    limit: int = Query(default=10, ge=1, le=50),
    _: dict = Depends(require_session),
) -> dict:
    return {"asset_scans": asset_scans(limit)}


@app.get("/api/platform/brain-chat")
def api_platform_brain_history(
    limit: int = Query(default=10, ge=1, le=50),
    _: dict = Depends(require_session),
) -> dict:
    return {"messages": brain_chat(limit)}


@app.get("/api/platform/api-keys")
def api_list_platform_keys(_: dict = Depends(require_session)) -> dict:
    return {"api_keys": list_api_keys()}


@app.post("/api/platform/api-keys")
def api_create_platform_key(
    payload: ApiKeyCreateRequest,
    session: dict = Depends(require_session),
) -> dict:
    key = create_api_key(
        name=payload.name,
        scopes=payload.scopes,
        created_by=session["email"],
    )
    return key


@app.delete("/api/platform/api-keys/{key_id}")
def api_revoke_platform_key(
    key_id: str,
    _: dict = Depends(require_session),
) -> dict:
    revoke_api_key(key_id)
    return {"status": "revoked", "key_id": key_id}


@app.post("/api/platform/descriptions/generate")
def api_generate_platform_description(
    payload: DescriptionRequest,
    _: dict = Depends(require_session),
) -> dict:
    description = describe_payload(payload.model_dump())
    record_description(
        {
            "id": description["source_name"],
            "source": description["source_name"],
            "generated_at": description["generated_at"],
            "description": description["description"],
            "type": description["type"],
        }
    )
    return description


@app.post("/api/platform/browser-observe")
def api_browser_observe(
    payload: BrowserObserveRequest,
    _: dict = Depends(require_session),
) -> dict:
    frame = _decode_image_payload(payload.image_base64)
    result = runtime.detector.analyze_frame(
        frame,
        source_name=payload.source_name,
        source_type=payload.source_type,
        modality=payload.modality,
        connector_type=payload.connector_type,
        zone=payload.zone,
        analysis_mode=payload.analysis_mode,
        description_prompt=payload.description_prompt,
    )
    description, decision = _commit_analysis(result)
    return _analysis_response(result, description, decision)


@app.post("/api/platform/object-scan")
def api_object_scan(
    payload: ObjectScanRequest,
    _: dict = Depends(require_session),
) -> dict:
    frame = _decode_image_payload(payload.image_base64)
    result = runtime.detector.analyze_frame(
        frame,
        source_name=payload.source_name,
        source_type="camera",
        modality="video",
        connector_type=payload.connector_type,
        zone=payload.zone,
        analysis_mode="object-scan",
        description_prompt=payload.context,
    )
    description, decision = _commit_analysis(result)
    scan = analyze_object_scan(
        frame,
        result,
        scan_target=payload.scan_target,
        source_name=payload.source_name,
        zone=payload.zone,
        context=payload.context,
    )
    record_asset_scan(scan)
    return _analysis_response(result, description, decision, scan)


@app.post("/api/platform/source-observe")
def api_source_observe(
    payload: SourceObserveRequest,
    _: dict = Depends(require_session),
) -> dict:
    frame, simulated_objects, mode = _capture_source_frame(
        payload.source_uri,
        source_name=payload.source_name,
        source_type=payload.source_type,
        connector_type=payload.connector_type,
        zone=payload.zone,
    )
    result = runtime.detector.analyze_frame(
        frame,
        source_name=payload.source_name,
        source_type=payload.source_type,
        modality=payload.modality,
        connector_type=payload.connector_type,
        zone=payload.zone,
        analysis_mode=payload.analysis_mode,
        description_prompt=payload.description_prompt,
        source_uri=payload.source_uri,
        mode=mode,
        simulated_objects=simulated_objects,
    )
    description, decision = _commit_analysis(result)
    return _analysis_response(result, description, decision)


@app.post("/api/platform/brain-chat")
def api_platform_brain_chat(
    payload: BrainChatRequest,
    _: dict = Depends(require_session),
) -> dict:
    response = answer_brain_chat(
        payload.message,
        dashboard_snapshot(),
        asset_scan_id=payload.asset_scan_id,
        scope=payload.scope,
    )
    record_brain_chat(response)
    return response


@app.get("/api/external/runtime")
def api_external_runtime(_: dict = Depends(require_api_key)) -> dict:
    dashboard = dashboard_snapshot()
    return {
        "runtime": dashboard["runtime"],
        "cameras": dashboard.get("cameras", []),
        "descriptions": dashboard.get("description_feed", [])[:8],
        "meaning_feed": dashboard.get("meaning_feed", [])[:8],
        "asset_scans": dashboard.get("asset_scans", [])[:6],
    }


@app.post("/api/external/descriptions/generate")
def api_external_generate_description(
    payload: DescriptionRequest,
    _: dict = Depends(require_api_key),
) -> dict:
    description = describe_payload(payload.model_dump())
    record_description(
        {
            "id": description["source_name"],
            "source": description["source_name"],
            "generated_at": description["generated_at"],
            "description": description["description"],
            "type": description["type"],
        }
    )
    return description


@app.post("/api/external/source-observe")
def api_external_source_observe(
    payload: SourceObserveRequest,
    _: dict = Depends(require_api_key),
) -> dict:
    frame, simulated_objects, mode = _capture_source_frame(
        payload.source_uri,
        source_name=payload.source_name,
        source_type=payload.source_type,
        connector_type=payload.connector_type,
        zone=payload.zone,
    )
    result = runtime.detector.analyze_frame(
        frame,
        source_name=payload.source_name,
        source_type=payload.source_type,
        modality=payload.modality,
        connector_type=payload.connector_type,
        zone=payload.zone,
        analysis_mode=payload.analysis_mode,
        description_prompt=payload.description_prompt,
        source_uri=payload.source_uri,
        mode=mode,
        simulated_objects=simulated_objects,
    )
    description, decision = _commit_analysis(result)
    return _analysis_response(result, description, decision)


@app.post("/api/external/object-scan")
def api_external_object_scan(
    payload: ObjectScanRequest,
    _: dict = Depends(require_api_key),
) -> dict:
    frame = _decode_image_payload(payload.image_base64)
    result = runtime.detector.analyze_frame(
        frame,
        source_name=payload.source_name,
        source_type="camera",
        modality="video",
        connector_type=payload.connector_type,
        zone=payload.zone,
        analysis_mode="object-scan",
        description_prompt=payload.context,
    )
    description, decision = _commit_analysis(result)
    scan = analyze_object_scan(
        frame,
        result,
        scan_target=payload.scan_target,
        source_name=payload.source_name,
        zone=payload.zone,
        context=payload.context,
    )
    record_asset_scan(scan)
    return _analysis_response(result, description, decision, scan)


@app.post("/api/external/brain-chat")
def api_external_brain_chat(
    payload: BrainChatRequest,
    _: dict = Depends(require_api_key),
) -> dict:
    response = answer_brain_chat(
        payload.message,
        dashboard_snapshot(),
        asset_scan_id=payload.asset_scan_id,
        scope=payload.scope,
    )
    record_brain_chat(response)
    return response
