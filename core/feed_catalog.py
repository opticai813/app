from copy import deepcopy


_CATALOG = [
    {
        "id": "catalog-public-longmire-road",
        "name": "Mount Rainier Longmire Road Cam",
        "source_type": "cctv",
        "modality": "video",
        "connector_type": "http",
        "transport": "http",
        "zone": "north_access",
        "profile": "public-roadway-webcam",
        "mission_role": "ingress-monitor",
        "analysis_mode": "object-detection",
        "description_prompt": "Describe vehicles, parking activity, and road conditions visible in the public roadway webcam.",
        "source_uri": "https://www.nps.gov/webcams-mora/longmire.jpg",
        "description": "Official National Park Service webcam with a current road and parking-area view.",
    },
    {
        "id": "catalog-public-terrain-east",
        "name": "Paradise East Elevated Cam",
        "source_type": "camera",
        "modality": "video",
        "connector_type": "http",
        "transport": "http",
        "zone": "terrain_overwatch",
        "profile": "public-elevated-webcam",
        "mission_role": "terrain-visibility",
        "analysis_mode": "scene-description",
        "description_prompt": "Describe weather, terrain visibility, and visible vehicle activity from the elevated webcam.",
        "source_uri": "https://www.nps.gov/webcams-mora/east.jpg",
        "description": "Official Mount Rainier public webcam with an elevated parking-lot and terrain view.",
    },
    {
        "id": "catalog-public-goes19-geocolor",
        "name": "GOES-19 GeoColor Snapshot",
        "source_type": "satellite",
        "modality": "imagery",
        "connector_type": "http",
        "transport": "http",
        "zone": "broad_area",
        "profile": "orbital-revisit",
        "mission_role": "wide-area-change-monitor",
        "analysis_mode": "scene-description",
        "description_prompt": "Describe cloud structures and broad-area conditions visible in the current satellite image.",
        "source_uri": "https://cdn.star.nesdis.noaa.gov/GOES19/ABI/FD/GEOCOLOR/1808x1808.jpg",
        "description": "Official NOAA NESDIS GOES-19 GeoColor full-disk image that refreshes on an operational cadence.",
    },
    {
        "id": "catalog-camera-browser-device",
        "name": "Device Browser Camera",
        "source_type": "camera",
        "modality": "video",
        "connector_type": "browser",
        "transport": "usb",
        "zone": "local_device_view",
        "profile": "mobile-eo",
        "mission_role": "local-observe",
        "analysis_mode": "object-detection",
        "description_prompt": "Describe people, vehicles, and noteworthy activity from the local device camera.",
        "source_uri": "0",
        "description": "Use the tablet, mobile, or laptop camera directly through the platform browser session.",
    },
    {
        "id": "catalog-cctv-onvif-campus",
        "name": "Campus ONVIF CCTV",
        "source_type": "cctv",
        "modality": "video",
        "connector_type": "onvif",
        "transport": "rtsp",
        "zone": "campus_perimeter",
        "profile": "fixed-eo",
        "mission_role": "site-security",
        "analysis_mode": "object-detection",
        "description_prompt": "Describe people, vehicles, and unusual activity around the campus perimeter.",
        "source_uri": "rtsp://username:password@camera-host/stream1",
        "description": "Generic ONVIF CCTV connector template for perimeter cameras.",
    },
    {
        "id": "catalog-cctv-traffic-rtsp",
        "name": "Traffic RTSP Camera",
        "source_type": "cctv",
        "modality": "video",
        "connector_type": "rtsp",
        "transport": "rtsp",
        "zone": "traffic_corridor",
        "profile": "roadway-monitor",
        "mission_role": "vehicle-tracking",
        "analysis_mode": "asset-tracking",
        "description_prompt": "Describe traffic flow, stopped vehicles, and pedestrians near the corridor.",
        "source_uri": "rtsp://traffic-camera-host/live",
        "description": "RTSP template for roadway and city CCTV feeds.",
    },
    {
        "id": "catalog-satellite-sentinel",
        "name": "Sentinel-2 STAC Imagery",
        "source_type": "satellite",
        "modality": "imagery",
        "connector_type": "stac",
        "transport": "file",
        "zone": "area_of_interest",
        "profile": "orbital-revisit",
        "mission_role": "change-detection",
        "analysis_mode": "scene-description",
        "description_prompt": "Describe changes, vehicles, and site activity visible in the revisit imagery.",
        "source_uri": "https://earth-search.aws.element84.com/v1",
        "description": "Public STAC-compatible satellite imagery template for revisit monitoring.",
    },
    {
        "id": "catalog-satellite-landsat",
        "name": "Landsat STAC Collection",
        "source_type": "satellite",
        "modality": "imagery",
        "connector_type": "stac",
        "transport": "file",
        "zone": "broad_area",
        "profile": "broad-area",
        "mission_role": "pattern-of-life",
        "analysis_mode": "scene-description",
        "description_prompt": "Describe broad-area changes and visible asset activity from the satellite scene.",
        "source_uri": "https://landsatlook.usgs.gov/stac-server",
        "description": "Satellite STAC template for Landsat-based broad-area monitoring.",
    },
    {
        "id": "catalog-cv-archived-video",
        "name": "Computer Vision Video Workspace",
        "source_type": "computer-vision",
        "modality": "video",
        "connector_type": "s3",
        "transport": "file",
        "zone": "analysis_workspace",
        "profile": "archive-review",
        "mission_role": "forensic-analysis",
        "analysis_mode": "scene-description",
        "description_prompt": "Describe what the archived computer-vision feed contains and highlight mission-relevant activity.",
        "source_uri": "s3://optic-ingest-bucket/mission/video.mp4",
        "description": "Archived computer-vision workspace template for hosted video review pipelines.",
    },
    {
        "id": "catalog-sensor-mqtt-fusion",
        "name": "MQTT Sensor Fusion Topic",
        "source_type": "sensor",
        "modality": "fusion",
        "connector_type": "mqtt",
        "transport": "file",
        "zone": "industrial_site",
        "profile": "sensor-fusion",
        "mission_role": "facility-awareness",
        "analysis_mode": "scene-description",
        "description_prompt": "Describe the operational picture from the fused sensor signals.",
        "source_uri": "mqtt://broker-host/topic/site/fusion",
        "description": "Sensor fusion connector template for telemetry and detector topics.",
    },
]


def search_feed_catalog(query: str = "", source_type: str | None = None) -> list[dict]:
    q = query.strip().lower()
    source_filter = (source_type or "").strip().lower()
    results: list[dict] = []
    for item in _CATALOG:
        if source_filter and item["source_type"] != source_filter:
            continue
        haystack = " ".join(
            [
                item["name"],
                item["source_type"],
                item["modality"],
                item["connector_type"],
                item["description"],
                item["zone"],
                item["mission_role"],
            ]
        ).lower()
        if q and q not in haystack:
            continue
        results.append(deepcopy(item))
    return results


def get_catalog_template(template_id: str) -> dict | None:
    match = next((item for item in _CATALOG if item["id"] == template_id), None)
    return deepcopy(match) if match else None
