# Optic Platform

Standalone operator console for the Optic backend.

## Runtime modes

- `sim`: always use the built-in simulator
- `proxy`: require the FastAPI backend and proxy live runtime data
- `hybrid`: try the backend first, then fall back to the simulator

## Run locally

```bash
cd optic-platform
npm start
```

## Environment

Copy `.env.example` values into your shell or process manager:

- `HOST`
- `PORT`
- `OPTIC_PLATFORM_MODE`
- `OPTIC_API_URL`
- `OPTIC_API_TIMEOUT_MS`

## Routes

- `/`
- `/health`
- `/api/dashboard`
- `/api/events`
- `/api/alerts`
- `/api/tracks`