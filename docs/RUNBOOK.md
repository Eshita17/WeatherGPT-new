# Runbook

## App does not start
Check `docker compose logs api`.

## Weather API is unavailable
The application automatically uses fixture weather data.

## Gemini is unavailable
Remove/leave `GEMINI_API_KEY` empty. The deterministic local answer engine remains active.

## Alert demo
Open Alerts and press Replay storm. The browser connects to `/ws/alerts`.

## Kubernetes
The supplied manifests are a local development starting point. Build the API image as `weathergpt/api:local` and load it into kind before applying the overlay.
