# WeatherGPT — SIH26068

A runnable, beginner-friendly implementation of the WeatherGPT plan:
- Real-time weather via Open-Meteo
- Conversational weather agent with tool routing
- SSE streaming chat
- Provenance cards
- 7-day forecast and sector advisory
- Alert replay + WebSocket alert stream
- Multilingual response mode
- Trust/evaluation dashboard
- Docker Compose development stack
- Kubernetes manifests
- GitHub Actions CI
- Fixture fallback when external APIs are unavailable

## Quick start

### Option A — Python only
```bash
cd apps/api
python -m venv .venv
source .venv/bin/activate       # Windows: .venv\Scripts\activate
pip install -r requirements.txt
cd ../..
uvicorn apps.api.main:app --reload --port 8000
```

Open http://localhost:8000

### Option B — Docker Compose
```bash
docker compose up --build
```

Open http://localhost:8000

The database/cache/broker are optional for the core demo. The application automatically falls back to fixture data if they are unavailable.

## Optional Gemini

Create `.env` from `.env.example` and add `GEMINI_API_KEY`.
Without a key, WeatherGPT uses its deterministic local weather response engine, so the demo still works.

## Main demo
1. Search a city or use the default Mysuru location.
2. Ask: `Will it rain tomorrow?`
3. Ask: `gharmi ke liye barish hoga kya?`
4. Try the language buttons.
5. Open Alerts and press **Replay storm**.
6. Open Trust Dashboard.
7. Try a sector advisory such as agriculture.

## Architecture

```text
PWA / Flutter client
        |
        v
FastAPI Gateway ---- SSE chat ----> Agent service
        |                            |
        |                            +--> weather tools
        |                            +--> advisory tools
        |
        +---- WebSocket alerts <---- Alert service
        |
        +---- Trust / evaluation
        |
        +---- PostgreSQL / Redis / EMQX (optional)

Open-Meteo --> ingest/tool adapters
```

## Important implementation note

This repository is a functional hackathon/demo implementation of the plan, not a claim that production-grade IMD/WIS2.0 integrations, measured accuracy targets, Kubernetes autoscaling targets, or government ASR/TTS integrations have already been achieved. Those are included as extension points and demo-safe fallbacks. Never present an unmeasured target as a measured result.

## Conversational AI

WeatherGPT-new now has a real conversational AI path through Gemini. It uses the selected city, live weather payload, recent chat history, and the user's actual question instead of returning one fixed weather sentence. See `AI_SETUP.md` for configuration. Without a Gemini key, the project falls back to a query-aware offline weather assistant so the demo still runs.
