# Optic App

Optic App is the deployable Perception Infrastructure Engine stack: a FastAPI backend, Redis-backed runtime state, perception/meaning services, and a standalone operator platform UI.

## Included

- `app/`: FastAPI control plane and API
- `core/`: auth, Redis runtime helpers, control plane, state, feed discovery
- `services/`: ingestion, perception, scene meaning, agent logic, brain chat, training
- `ui/`: backend-served fallback dashboard
- `optic-platform/`: standalone operator console that can run in `sim`, `proxy`, or `hybrid` mode

## Quick start

### Backend

```bash
pip install -r requirements.txt
uvicorn app.main:app --host 127.0.0.1 --port 8000
```

### Standalone platform

```bash
cd optic-platform
npm start
```

### Full stack with Docker

```bash
docker compose up --build
```

- API docs: `http://127.0.0.1:8000/docs`
- Platform UI: `http://127.0.0.1:4314`

## Default demo login

- Email: `admin@opticcontrol.ai`
- Password: `OpticPlatform!2026`

## Notes

- Default camera mode is `demo`, so the stack is runnable without a local webcam.
- `ultralytics` may download `yolov8n.pt` on first run if it is not already present.
- Public snapshot feeds are seeded into the control plane for live-looking demo monitors.