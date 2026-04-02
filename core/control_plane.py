import hashlib
import json
from copy import deepcopy
from datetime import datetime, timezone
from threading import Lock
from uuid import uuid4

from app.config import settings
from core.redis_runtime import redis_client


_client = redis_client()
_control_plane_key = "optic:control_plane"
_lock = Lock()
_ALLOWED_SECTIONS = {
    "organization",
    "devices",
    "feeds",
    "pipelines",
    "identity",
    "training",
    "operators",
    "deployment",
}


def _timestamp() -> str:
    return datetime.now(timezone.utc).isoformat()


def _clone(data: dict) -> dict:
    return deepcopy(data)


def _password_hash(password: str) -> str:
    return hashlib.sha256(password.encode("utf-8")).hexdigest()


def _new_id(prefix: str) -> str:
    return f"{prefix}-{uuid4().hex[:10]}"


def _seed_feed_defaults() -> list[dict]:
    return [
        {
            "id": "feed-alpha-01",
            "name": "Mount Rainier Longmire Road Cam",
            "device_id": "dev-edge-alpha",
            "transport": "http",
            "source_type": "cctv",
            "modality": "video",
            "connector_type": "http",
            "source_uri": "https://www.nps.gov/webcams-mora/longmire.jpg",
            "zone": "north_access",
            "profile": "public-roadway-webcam",
            "mission_role": "ingress-monitor",
            "analysis_mode": "object-detection",
            "description_prompt": "Describe vehicles, parking activity, and road conditions visible in the current Longmire roadway webcam.",
            "resolution": [960, 540],
            "fps_target": 1,
            "refresh_seconds": 60,
            "source_attribution": "National Park Service Mount Rainier webcam",
            "enabled": True,
        },
        {
            "id": "feed-bravo-01",
            "name": "Paradise East Elevated Cam",
            "device_id": "dev-drone-bravo",
            "transport": "http",
            "source_type": "camera",
            "modality": "video",
            "connector_type": "http",
            "source_uri": "https://www.nps.gov/webcams-mora/east.jpg",
            "zone": "handoff_corridor",
            "profile": "public-elevated-webcam",
            "mission_role": "terrain-overwatch",
            "analysis_mode": "scene-description",
            "description_prompt": "Describe weather, terrain visibility, vehicles, and activity visible in the elevated Paradise parking-area webcam.",
            "resolution": [960, 540],
            "fps_target": 1,
            "refresh_seconds": 60,
            "source_attribution": "National Park Service Mount Rainier webcam",
            "enabled": True,
        },
        {
            "id": "feed-charlie-01",
            "name": "Tatoosh Terrain Road Cam",
            "device_id": "dev-yard-charlie",
            "transport": "http",
            "source_type": "camera",
            "modality": "video",
            "connector_type": "http",
            "source_uri": "https://www.nps.gov/webcams-mora/tatoosh.jpg",
            "zone": "yard_lane",
            "profile": "public-terrain-webcam",
            "mission_role": "terrain-visibility",
            "analysis_mode": "scene-description",
            "description_prompt": "Describe terrain, roadside conditions, and environmental visibility visible from the Tatoosh public webcam.",
            "resolution": [960, 540],
            "fps_target": 1,
            "refresh_seconds": 60,
            "source_attribution": "National Park Service Mount Rainier webcam",
            "enabled": True,
        },
        {
            "id": "feed-echo-01",
            "name": "Camp Muir High Camp Cam",
            "device_id": "dev-drone-bravo",
            "transport": "http",
            "source_type": "camera",
            "modality": "video",
            "connector_type": "http",
            "source_uri": "https://www.nps.gov/customcf/webcam/dsp_webcam_image.cfm?id=81B463C8-1DD8-B71B-0B89D924E49661B5",
            "zone": "high_camp",
            "profile": "public-high-alpine-webcam",
            "mission_role": "alpine-overwatch",
            "analysis_mode": "scene-description",
            "description_prompt": "Describe snow cover, ridge visibility, alpine weather, and personnel or equipment activity visible from the Camp Muir webcam.",
            "resolution": [960, 540],
            "fps_target": 1,
            "refresh_seconds": 60,
            "source_attribution": "National Park Service Mount Rainier webcam",
            "enabled": True,
        },
        {
            "id": "feed-foxtrot-01",
            "name": "Paradise Visitor Center Cam",
            "device_id": "dev-edge-alpha",
            "transport": "http",
            "source_type": "cctv",
            "modality": "video",
            "connector_type": "http",
            "source_uri": "https://www.nps.gov/customcf/webcam/dsp_webcam_image.cfm?id=81B4632E-1DD8-B71B-0BD89E4ADA74C23A",
            "zone": "visitor_center",
            "profile": "public-plaza-webcam",
            "mission_role": "footfall-monitor",
            "analysis_mode": "object-detection",
            "description_prompt": "Describe foot traffic, vehicle staging, and weather conditions visible around the Paradise visitor center area.",
            "resolution": [960, 540],
            "fps_target": 1,
            "refresh_seconds": 60,
            "source_attribution": "National Park Service Mount Rainier webcam",
            "enabled": True,
        },
        {
            "id": "feed-golf-01",
            "name": "Paradise West Approach Cam",
            "device_id": "dev-yard-charlie",
            "transport": "http",
            "source_type": "camera",
            "modality": "video",
            "connector_type": "http",
            "source_uri": "https://www.nps.gov/customcf/webcam/dsp_webcam_image.cfm?id=81B46314-1DD8-B71B-0BF361626323496A",
            "zone": "west_perimeter",
            "profile": "public-road-approach-webcam",
            "mission_role": "west-approach-monitor",
            "analysis_mode": "scene-description",
            "description_prompt": "Describe roadway visibility, snowfall, and approach-lane conditions visible from the Paradise west-facing webcam.",
            "resolution": [960, 540],
            "fps_target": 1,
            "refresh_seconds": 60,
            "source_attribution": "National Park Service Mount Rainier webcam",
            "enabled": True,
        },
        {
            "id": "feed-hotel-01",
            "name": "Sunrise East Alpine Cam",
            "device_id": "dev-drone-bravo",
            "transport": "http",
            "source_type": "camera",
            "modality": "video",
            "connector_type": "http",
            "source_uri": "https://www.nps.gov/customcf/webcam/dsp_webcam_image.cfm?id=81B4639C-1DD8-B71B-0B3D811FB1DA1D25",
            "zone": "sunrise_east",
            "profile": "public-alpine-webcam",
            "mission_role": "terrain-watch",
            "analysis_mode": "scene-description",
            "description_prompt": "Describe alpine access conditions, terrain visibility, and visitor activity visible from the Sunrise East webcam.",
            "resolution": [960, 540],
            "fps_target": 1,
            "refresh_seconds": 60,
            "source_attribution": "National Park Service Mount Rainier webcam",
            "enabled": True,
        },
        {
            "id": "feed-delta-01",
            "name": "GOES-19 GeoColor Satellite",
            "device_id": "dev-bay-delta",
            "transport": "http",
            "source_type": "satellite",
            "modality": "imagery",
            "connector_type": "http",
            "source_uri": "https://cdn.star.nesdis.noaa.gov/GOES19/ABI/FD/GEOCOLOR/1808x1808.jpg",
            "zone": "loading_bay",
            "profile": "orbital-revisit",
            "mission_role": "wide-area-change-monitor",
            "analysis_mode": "scene-description",
            "description_prompt": "Describe cloud structures, weather bands, and broad-area conditions visible in the current GOES-19 GeoColor image.",
            "resolution": [960, 540],
            "fps_target": 1,
            "refresh_seconds": 600,
            "source_attribution": "NOAA NESDIS GOES-19 GeoColor imagery",
            "enabled": True,
        },
    ]


def _default_control_plane() -> dict:
    return {
        "organization": {
            "name": "Optic Mission Systems",
            "workspace": "Physical AI Perception Infrastructure",
            "environment": "Demo / Operator Sandbox",
            "region": "us-east-1",
            "mission": "Persistent site security and cross-camera identity continuity.",
            "updated_at": _timestamp(),
        },
        "devices": [
            {
                "id": "dev-edge-alpha",
                "name": "Edge Alpha Gateway",
                "kind": "edge-node",
                "location": "North access lane",
                "network_address": "192.168.10.21",
                "health": "online",
                "deployment_target": "rack-a",
                "capabilities": ["rtsp", "re-id", "event-forwarding"],
                "assigned_feed_ids": ["feed-alpha-01", "feed-foxtrot-01"],
                "enabled": True,
            },
            {
                "id": "dev-drone-bravo",
                "name": "Aerial Bravo ISR",
                "kind": "uas",
                "location": "Patrol corridor",
                "network_address": "10.4.0.18",
                "health": "online",
                "deployment_target": "mobile-fleet",
                "capabilities": ["stabilized-eo", "handoff-relay", "telemetry"],
                "assigned_feed_ids": ["feed-bravo-01", "feed-echo-01", "feed-hotel-01"],
                "enabled": True,
            },
            {
                "id": "dev-yard-charlie",
                "name": "Yard Charlie Mast",
                "kind": "fixed-camera",
                "location": "Industrial yard",
                "network_address": "192.168.10.44",
                "health": "online",
                "deployment_target": "yard-grid",
                "capabilities": ["night-eo", "tracking", "watchlist-tagging"],
                "assigned_feed_ids": ["feed-charlie-01", "feed-golf-01"],
                "enabled": True,
            },
            {
                "id": "dev-bay-delta",
                "name": "Loading Bay Delta",
                "kind": "fixed-camera",
                "location": "Loading bay",
                "network_address": "192.168.10.58",
                "health": "online",
                "deployment_target": "bay-gateway",
                "capabilities": ["rtsp", "identity-handoff", "archive-sync"],
                "assigned_feed_ids": ["feed-delta-01"],
                "enabled": True,
            },
        ],
        "feeds": _seed_feed_defaults(),
        "pipelines": {
            "perception": {
                "model": settings.yolo_model,
                "detection_confidence": settings.detection_confidence,
                "enabled_labels": ["person", "car", "truck", "forklift", "tree"],
                "track_distance_threshold": 110.0,
                "track_max_missed": 12,
            },
            "meaning": {
                "rules": [
                    {
                        "id": "meaning-restricted-person",
                        "name": "Restricted zone person",
                        "labels": ["person"],
                        "zones": ["north_access", "loading_bay"],
                        "min_confidence": 0.84,
                        "meaning": "restricted-presence",
                        "severity": "high",
                    },
                    {
                        "id": "meaning-yard-vehicle",
                        "name": "Vehicle in yard corridor",
                        "labels": ["car", "truck", "forklift"],
                        "zones": ["yard_lane", "loading_bay"],
                        "min_confidence": 0.72,
                        "meaning": "asset-movement",
                        "severity": "medium",
                    },
                    {
                        "id": "meaning-handoff-observed",
                        "name": "Identity handoff corridor occupancy",
                        "labels": ["person"],
                        "zones": ["handoff_corridor"],
                        "min_confidence": 0.8,
                        "meaning": "handoff-visible",
                        "severity": "medium",
                    },
                ],
            },
            "alerts": {
                "enabled": True,
                "person_confidence": settings.alert_confidence,
                "watchlist_alerts": True,
                "handoff_alerts": True,
            },
        },
        "identity": {
            "global_tracking_enabled": True,
            "matching_strategy": "topology-plus-identity-hint",
            "matching_threshold": 0.78,
            "handoff_window_seconds": 8,
            "watchlist": [
                {
                    "id": "watch-echo",
                    "name": "Echo Subject",
                    "match_key": "identity-echo",
                    "category": "person",
                    "priority": "high",
                    "notes": "Maintain custody across ingress and loading bay zones.",
                }
            ],
            "topology": [
                {
                    "id": "topo-north-corridor",
                    "from_feed_id": "feed-alpha-01",
                    "to_feed_id": "feed-bravo-01",
                    "relationship": "handoff",
                    "expected_travel_seconds": 4,
                },
                {
                    "id": "topo-corridor-bay",
                    "from_feed_id": "feed-bravo-01",
                    "to_feed_id": "feed-delta-01",
                    "relationship": "handoff",
                    "expected_travel_seconds": 5,
                },
                {
                    "id": "topo-yard-bay",
                    "from_feed_id": "feed-charlie-01",
                    "to_feed_id": "feed-delta-01",
                    "relationship": "shared-coverage",
                    "expected_travel_seconds": 6,
                },
            ],
        },
        "training": {
            "active_mode": "robotics",
            "use_live_meaning": True,
            "use_alerts": True,
            "use_digital_twins": True,
            "closed_loop_enabled": True,
            "modes": {
                "robotics": {
                    "enabled": True,
                    "targets": ["ground_robot", "drone", "surface_vessel", "subsea_robot"],
                    "focus": ["navigation", "obstacle_reasoning", "handoff", "weather_response"],
                },
                "industrial": {
                    "enabled": True,
                    "targets": ["inspection_rover", "forklift", "camera_cell", "maintenance_twin"],
                    "focus": ["safety", "material_flow", "quality", "uptime"],
                },
                "automation": {
                    "enabled": True,
                    "targets": ["workflow_engine", "fleet_orchestrator", "alarm_router", "policy_compiler"],
                    "focus": ["trigger_action", "fallbacks", "auditability", "cross_system_sync"],
                },
            },
        },
        "operators": [
            {
                "id": "op-admin",
                "name": "Avery Sloan",
                "email": settings.admin_email,
                "role": "platform_admin",
                "permissions": [
                    "platform:read",
                    "platform:write",
                    "devices:write",
                    "feeds:write",
                    "pipelines:write",
                    "identity:write",
                    "operators:write",
                ],
                "status": "active",
                "password_hash": _password_hash(settings.admin_password),
                "seeded_demo": True,
                "last_login_at": None,
            },
            {
                "id": "op-ops",
                "name": "Jordan Reyes",
                "email": "ops@optic.local",
                "role": "mission_ops",
                "permissions": [
                    "platform:read",
                    "devices:write",
                    "feeds:write",
                    "identity:write",
                ],
                "status": "active",
                "password_hash": _password_hash("optic-ops"),
                "last_login_at": None,
            },
            {
                "id": "op-analyst",
                "name": "Maya Chen",
                "email": "analyst@optic.local",
                "role": "intelligence_analyst",
                "permissions": [
                    "platform:read",
                    "feeds:read",
                    "identity:read",
                ],
                "status": "active",
                "password_hash": _password_hash("optic-analyst"),
                "last_login_at": None,
            },
        ],
        "deployment": {
            "profile": "edge-plus-cloud",
            "sync_mode": "redis-streams",
            "retention_hours": 24,
            "preferred_runtime": "docker",
        },
        "updated_at": _timestamp(),
    }


def _reconcile_seed_data(control_plane: dict) -> dict:
    updated = _clone(control_plane)
    for operator in updated.get("operators", []):
        if operator.get("id") == "op-admin":
            operator["email"] = settings.admin_email
            operator["password_hash"] = _password_hash(settings.admin_password)
            operator["seeded_demo"] = True
    seeded_defaults = _seed_feed_defaults()
    seeded_feeds = {item["id"]: item for item in seeded_defaults}
    existing_feeds = {item.get("id"): item for item in updated.get("feeds", []) if item.get("id")}
    reconciled_feeds: list[dict] = []

    for seeded in seeded_defaults:
        current = existing_feeds.pop(seeded["id"], None)
        if not current:
            reconciled_feeds.append(deepcopy(seeded))
            continue

        current_uri = str(current.get("source_uri") or "").strip().lower()
        if current_uri.startswith("demo://") or current.get("transport") == "demo":
            preserved_enabled = current.get("enabled", True)
            current = deepcopy(seeded)
            current["enabled"] = preserved_enabled
        else:
            for field in ("refresh_seconds", "source_attribution", "description_prompt", "profile", "mission_role"):
                if not current.get(field):
                    current[field] = deepcopy(seeded.get(field))

        reconciled_feeds.append(current)

    reconciled_feeds.extend(existing_feeds.values())
    updated["feeds"] = reconciled_feeds

    seeded_feed_ids_by_device: dict[str, list[str]] = {}
    for feed in seeded_defaults:
        device_id = feed.get("device_id")
        if not device_id:
            continue
        seeded_feed_ids_by_device.setdefault(device_id, []).append(feed["id"])

    for device in updated.get("devices", []):
        assigned_feed_ids = list(device.get("assigned_feed_ids") or [])
        for feed_id in seeded_feed_ids_by_device.get(device.get("id"), []):
            if feed_id not in assigned_feed_ids:
                assigned_feed_ids.append(feed_id)
        device["assigned_feed_ids"] = assigned_feed_ids

    perception = updated.get("pipelines", {}).get("perception", {})
    labels = list(perception.get("enabled_labels") or [])
    if "tree" not in [str(item).lower() for item in labels]:
        labels.append("tree")
        perception["enabled_labels"] = labels
    return updated


def _sanitize_operator(operator: dict) -> dict:
    sanitized = {key: value for key, value in operator.items() if key != "password_hash"}
    sanitized["has_password"] = bool(operator.get("password_hash"))
    return sanitized


def _normalize_operator(record: dict, existing_by_id: dict[str, dict]) -> dict:
    operator_id = record.get("id") or _new_id("op")
    existing = existing_by_id.get(operator_id, {})
    password_hash = existing.get("password_hash")

    password = record.get("password")
    if password:
        password_hash = _password_hash(password)
    elif record.get("password_hash"):
        password_hash = record["password_hash"]

    normalized = {
        "id": operator_id,
        "name": record.get("name") or existing.get("name") or "Operator",
        "email": record.get("email") or existing.get("email") or f"{operator_id}@optic.local",
        "role": record.get("role") or existing.get("role") or "operator",
        "permissions": list(record.get("permissions") or existing.get("permissions") or []),
        "status": record.get("status") or existing.get("status") or "active",
        "last_login_at": record.get("last_login_at") or existing.get("last_login_at"),
        "password_hash": password_hash or _password_hash("optic-temp"),
    }
    return normalized


def _normalize_collection(items: list[dict], prefix: str, key_defaults: dict | None = None) -> list[dict]:
    defaults = key_defaults or {}
    normalized: list[dict] = []
    for item in items:
        normalized_item = {**defaults, **item}
        normalized_item["id"] = normalized_item.get("id") or _new_id(prefix)
        normalized.append(normalized_item)
    return normalized


def _normalize_control_plane(payload: dict, existing: dict) -> dict:
    normalized = _clone(existing)

    if "organization" in payload and isinstance(payload["organization"], dict):
        normalized["organization"] = {
            **normalized.get("organization", {}),
            **payload["organization"],
            "updated_at": _timestamp(),
        }

    if "devices" in payload and isinstance(payload["devices"], list):
        normalized["devices"] = _normalize_collection(
            payload["devices"],
            "dev",
            {
                "kind": "fixed-camera",
                "location": "Unassigned",
                "network_address": "n/a",
                "health": "online",
                "deployment_target": "default",
                "capabilities": [],
                "assigned_feed_ids": [],
                "enabled": True,
            },
        )

    if "feeds" in payload and isinstance(payload["feeds"], list):
        normalized["feeds"] = _normalize_collection(
            payload["feeds"],
            "feed",
            {
                "transport": "demo",
                "source_type": "cctv",
                "modality": "video",
                "connector_type": "rtsp",
                "source_uri": "demo://custom-feed",
                "zone": "unassigned_zone",
                "profile": "fixed-eo",
                "mission_role": "general-observe",
                "analysis_mode": "object-detection",
                "description_prompt": "Describe what the feed is showing in plain operational language.",
                "resolution": [960, 540],
                "fps_target": 8,
                "enabled": True,
            },
        )

    if "pipelines" in payload and isinstance(payload["pipelines"], dict):
        normalized["pipelines"] = {
            **normalized.get("pipelines", {}),
            **payload["pipelines"],
        }

    if "identity" in payload and isinstance(payload["identity"], dict):
        identity = {**normalized.get("identity", {}), **payload["identity"]}
        if isinstance(identity.get("watchlist"), list):
            identity["watchlist"] = _normalize_collection(
                identity["watchlist"],
                "watch",
                {"category": "person", "priority": "medium", "notes": ""},
            )
        if isinstance(identity.get("topology"), list):
            identity["topology"] = _normalize_collection(
                identity["topology"],
                "topo",
                {
                    "relationship": "handoff",
                    "expected_travel_seconds": 5,
                },
            )
        normalized["identity"] = identity

    if "training" in payload and isinstance(payload["training"], dict):
        training = {**normalized.get("training", {}), **payload["training"]}
        existing_modes = normalized.get("training", {}).get("modes", {})
        if isinstance(training.get("modes"), dict):
            merged_modes = {}
            for mode_key, mode_value in {**existing_modes, **training["modes"]}.items():
                merged_modes[mode_key] = {
                    **(existing_modes.get(mode_key, {}) if isinstance(existing_modes.get(mode_key), dict) else {}),
                    **(mode_value if isinstance(mode_value, dict) else {}),
                }
            training["modes"] = merged_modes
        normalized["training"] = training

    if "deployment" in payload and isinstance(payload["deployment"], dict):
        normalized["deployment"] = {
            **normalized.get("deployment", {}),
            **payload["deployment"],
        }

    if "operators" in payload and isinstance(payload["operators"], list):
        existing_by_id = {item["id"]: item for item in normalized.get("operators", []) if item.get("id")}
        normalized["operators"] = [
            _normalize_operator(record, existing_by_id)
            for record in payload["operators"]
        ]

    normalized["updated_at"] = _timestamp()
    return _reconcile_seed_data(normalized)


def _load_control_plane() -> dict:
    raw = _client.get(_control_plane_key)
    if not raw:
        return _default_control_plane()
    return _reconcile_seed_data(json.loads(raw))


def _save_control_plane(control_plane: dict) -> dict:
    control_plane["updated_at"] = _timestamp()
    _client.set(_control_plane_key, json.dumps(control_plane, separators=(",", ":")))
    return control_plane


def initialize_control_plane() -> dict:
    with _lock:
        raw = _client.get(_control_plane_key)
        if raw:
            data = _reconcile_seed_data(json.loads(raw))
        else:
            data = _default_control_plane()
        return _save_control_plane(data)


def control_plane_snapshot(*, sanitized: bool = True) -> dict:
    with _lock:
        control_plane = _load_control_plane()
    if not sanitized:
        return control_plane
    public = _clone(control_plane)
    public["operators"] = [_sanitize_operator(item) for item in public.get("operators", [])]
    return public


def update_control_plane(payload: dict) -> dict:
    filtered = {key: value for key, value in payload.items() if key in _ALLOWED_SECTIONS}
    with _lock:
        current = _load_control_plane()
        updated = _normalize_control_plane(filtered, current)
        return _save_control_plane(updated)


def touch_operator_login(operator_id: str) -> None:
    with _lock:
        control_plane = _load_control_plane()
        for operator in control_plane.get("operators", []):
            if operator.get("id") == operator_id:
                operator["last_login_at"] = _timestamp()
                break
        _save_control_plane(control_plane)


def control_plane_summary() -> dict:
    snapshot = control_plane_snapshot()
    training_modes = snapshot.get("training", {}).get("modes", {})
    return {
        "devices": len(snapshot.get("devices", [])),
        "feeds": len(snapshot.get("feeds", [])),
        "operators": len(snapshot.get("operators", [])),
        "watchlist": len(snapshot.get("identity", {}).get("watchlist", [])),
        "topology_edges": len(snapshot.get("identity", {}).get("topology", [])),
        "training_modes": len([item for item in training_modes.values() if item.get("enabled", True)]),
    }


def enabled_feeds() -> list[dict]:
    control_plane = control_plane_snapshot()
    return [item for item in control_plane.get("feeds", []) if item.get("enabled", True)]
