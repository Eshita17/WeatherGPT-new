from __future__ import annotations

import asyncio
import json
import os
import re
import time
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, AsyncGenerator

import httpx
from fastapi import FastAPI, HTTPException, Query, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, JSONResponse, StreamingResponse
from pydantic import BaseModel, Field
from dotenv import load_dotenv

load_dotenv()

BASE = Path(__file__).resolve().parents[2]
WEB = BASE / "apps" / "web"

app = FastAPI(title="WeatherGPT API", version="1.0.0")
app.add_middleware(
    CORSMiddleware,
    allow_origins=os.getenv("CORS_ORIGINS", "*").split(","),
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)

alert_clients: set[WebSocket] = set()
alert_history: list[dict[str, Any]] = []

CITY_COORDS = {
    "mysuru": (12.2958, 76.6394),
    "mysore": (12.2958, 76.6394),
    "pune": (18.5204, 73.8567),
    "mumbai": (19.0760, 72.8777),
    "delhi": (28.6139, 77.2090),
    "bengaluru": (12.9716, 77.5946),
    "bangalore": (12.9716, 77.5946),
    "hyderabad": (17.3850, 78.4867),
    "chennai": (13.0827, 80.2707),
    "kolkata": (22.5726, 88.3639),
    "nagpur": (21.1458, 79.0882),
    "nashik": (19.9975, 73.7898),
}

LANGUAGES = {
    "en": "English",
    "hi": "Hindi",
    "mr": "Marathi",
    "bn": "Bengali",
    "te": "Telugu",
    "ta": "Tamil",
    "kn": "Kannada",
}

class ChatRequest(BaseModel):
    message: str = Field(min_length=1, max_length=1000)
    latitude: float = 0.0
    longitude: float = 0.0
    city: str = "Mysuru"
    language: str = "en"
    history: list[dict[str, str]] = Field(default_factory=list, max_length=12)

class AlertRequest(BaseModel):
    location: str = "Mysuru"
    severity: str = "severe"

class AdvisoryRequest(BaseModel):
    sector: str = "agriculture"
    city: str = "Mysuru"
    latitude: float = 12.2958
    longitude: float = 76.6394

def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()

def resolve_city(name: str) -> tuple[float, float, str]:
    key = name.strip().lower()
    if key in CITY_COORDS:
        lat, lon = CITY_COORDS[key]
        return lat, lon, key.title()
    # Allow "Mysuru, India" etc.
    first = re.split(r"[, ]+", key)[0]
    if first in CITY_COORDS:
        lat, lon = CITY_COORDS[first]
        return lat, lon, first.title()
    return 12.2958, 76.6394, "Mysuru"

async def open_meteo(lat: float, lon: float) -> dict[str, Any]:
    url = os.getenv("OPEN_METEO_BASE_URL", "https://api.open-meteo.com").rstrip("/") + "/v1/forecast"
    params = {
        "latitude": lat,
        "longitude": lon,
        "current": "temperature_2m,relative_humidity_2m,apparent_temperature,precipitation,rain,weather_code,wind_speed_10m",
        "hourly": "temperature_2m,precipitation_probability,precipitation,rain,wind_speed_10m,weather_code",
        "daily": "weather_code,temperature_2m_max,temperature_2m_min,precipitation_sum,precipitation_probability_max",
        "forecast_days": 7,
        "timezone": "auto",
    }
    try:
        async with httpx.AsyncClient(timeout=8) as client:
            r = await client.get(url, params=params)
            r.raise_for_status()
            data = r.json()
            data["_source"] = "Open-Meteo"
            data["_live"] = True
            return data
    except Exception:
        return fixture_weather(lat, lon)

def fixture_weather(lat: float, lon: float) -> dict[str, Any]:
    # Deterministic fixture so the demo works without internet.
    dates = [f"2026-10-{i:02d}" for i in range(2, 9)]
    return {
        "latitude": lat, "longitude": lon, "timezone": "Asia/Kolkata",
        "current": {
            "temperature_2m": 28.4, "relative_humidity_2m": 67,
            "apparent_temperature": 30.1, "precipitation": 0.0,
            "rain": 0.0, "weather_code": 2, "wind_speed_10m": 12.5,
        },
        "hourly": {
            "time": [f"2026-10-02T{h:02d}:00" for h in range(24)],
            "temperature_2m": [28 + ((h % 6) * 0.5) for h in range(24)],
            "precipitation_probability": [20,20,20,25,30,35,45,55,65,60,50,45,40,35,30,25,30,35,40,45,35,30,25,20],
            "precipitation": [0.0]*24, "rain": [0.0]*24,
            "wind_speed_10m": [10 + (h % 5) for h in range(24)],
            "weather_code": [2]*24,
        },
        "daily": {
            "time": dates,
            "weather_code": [2,61,3,63,80,2,1],
            "temperature_2m_max": [31,30,29,28,27,30,31],
            "temperature_2m_min": [22,22,21,21,20,21,22],
            "precipitation_sum": [0.0,2.4,4.1,8.5,5.2,0.0,0.0],
            "precipitation_probability_max": [20,60,70,80,75,25,15],
        },
        "_source": "WeatherGPT Demo Fixture",
        "_live": False,
    }

def provenance(data: dict[str, Any], lat: float, lon: float) -> dict[str, Any]:
    return {
        "source": data.get("_source", "Open-Meteo"),
        "model": "GFS / Open-Meteo",
        "run": "latest available",
        "run_age_minutes": 0 if data.get("_live") else None,
        "latitude": round(lat, 4),
        "longitude": round(lon, 4),
        "resolution": "model grid / demo downscale",
        "freshness": "live API" if data.get("_live") else "fixture fallback",
    }

def intent_for(message: str) -> str:
    q = message.lower()
    if any(x in q for x in ["alert", "warning", "storm", "cyclone", "flood", "thunder"]):
        return "alerts"
    if any(x in q for x in ["hour", "hourly", "next few hours", "later today"]):
        return "hourly"
    if any(x in q for x in ["tomorrow", "week", "7 day", "forecast", "rain", "barish", "बारिश"]):
        return "forecast"
    if any(x in q for x in ["farmer", "crop", "spray", "sow", "cotton", "खेती", "शेती"]):
        return "agriculture"
    if any(x in q for x in ["wind", "breeze", "हवा", "वारा"]):
        return "wind"
    if any(x in q for x in ["humidity", "humid", "उमस", "आर्द्रता"]):
        return "humidity"
    if any(x in q for x in ["temperature", "hot", "cold", "heat", "garmi", "gharmi", "तापमान"]):
        return "current"
    if any(x in q for x in ["carry", "umbrella", "jacket", "wear", "outfit", "what should i take"]):
        return "packing"
    if any(x in q for x in ["hello", "hi", "hey", "namaste", "नमस्ते"]):
        return "conversation"
    return "weather_general"


def weather_summary(data: dict[str, Any], city: str, language: str) -> str:
    c = data["current"]
    d = data["daily"]
    rain_prob = d["precipitation_probability_max"][1]
    max_t = d["temperature_2m_max"][1]
    min_t = d["temperature_2m_min"][1]
    wind = c.get("wind_speed_10m", "--")
    humidity = c.get("relative_humidity_2m", "--")
    return f"{city}: it is {c['temperature_2m']}°C now, with {humidity}% humidity and wind around {wind} km/h. Tomorrow looks like {min_t}–{max_t}°C with about {rain_prob}% precipitation probability."


def offline_ai_answer(req: ChatRequest, data: dict[str, Any]) -> str:
    """Useful no-key fallback. It is deliberately query-aware rather than repeating one template."""
    c, d, city = data["current"], data["daily"], req.city
    q = req.message.lower()
    rain = d["precipitation_probability_max"][1]
    hi, lo = d["temperature_2m_max"][1], d["temperature_2m_min"][1]
    wind, humidity = c.get("wind_speed_10m", "--"), c.get("relative_humidity_2m", "--")
    temp = c.get("temperature_2m", "--")
    intent = intent_for(q)
    if intent == "conversation":
        return f"Hi! I’m WeatherGPT for {city}. Ask me about rain, temperature, wind, humidity, forecasts, alerts, or what to carry outside."
    if intent == "alerts":
        return f"I can check the available weather-alert feed for {city}. For this forecast snapshot, the strongest useful signal is a {rain}% precipitation probability tomorrow. I won’t label that as an official warning unless an alert source reports one."
    if intent == "packing":
        item = "an umbrella or light rain protection" if rain >= 50 else "water, sunglasses and light clothing"
        return f"For {city}, I’d carry {item}. It is {temp}°C now, humidity is {humidity}%, and tomorrow’s precipitation probability is about {rain}%."
    if intent == "wind":
        return f"Wind in {city} is around {wind} km/h right now. If you’re planning outdoor activities, that is the wind reading I’d use; I’d also check the hourly forecast for changes later today."
    if intent == "humidity":
        comfort = "quite humid" if isinstance(humidity, (int,float)) and humidity >= 70 else "moderately humid" if isinstance(humidity, (int,float)) and humidity >= 50 else "relatively dry"
        return f"Humidity in {city} is {humidity}% right now, so conditions should feel {comfort}. At {temp}°C, the apparent temperature may feel warmer than the measured temperature."
    if intent == "current":
        return f"Right now in {city}: {temp}°C, {humidity}% humidity and {wind} km/h wind. Tomorrow’s range is {lo}–{hi}°C."
    if intent == "forecast":
        return f"For {city}, tomorrow is expected to be {lo}–{hi}°C with about a {rain}% precipitation probability. If you tell me what you’re planning—commuting, travel, a college event, or outdoor work—I can turn that forecast into a practical recommendation."
    if "why" in q or "should" in q or "recommend" in q:
        return f"Based on the available forecast for {city}, I’d plan around {rain}% precipitation probability tomorrow and temperatures of {lo}–{hi}°C. The best decision depends on your activity; tell me what you’re planning and I’ll tailor the recommendation."
    return f"I can help with {city} weather. Right now it is {temp}°C with {humidity}% humidity and {wind} km/h wind; tomorrow is {lo}–{hi}°C with {rain}% precipitation probability. What would you like to know—rain timing, travel advice, clothing, wind, or a forecast?"


async def generate_agent_answer(req: ChatRequest, data: dict[str, Any]) -> tuple[str, str]:
    key = os.getenv("GEMINI_API_KEY", "").strip()
    if not key:
        return offline_ai_answer(req, data), "offline-weather-ai"
    try:
        from google import genai
        client = genai.Client(api_key=key)
        history_text = "\n".join(
            f"{m.get('role','user')}: {m.get('content','')}" for m in req.history[-10:]
        )
        system = (
            "You are WeatherGPT, a real conversational AI weather assistant. "
            "Answer the user's actual question instead of returning a fixed weather summary. "
            "Use the supplied weather data as your factual source. You may explain, compare, recommend, "
            "summarize, translate, and answer follow-up questions. Do not invent weather measurements, "
            "official warnings, air-quality values, or forecasts outside the supplied data. If the user asks "
            "something unrelated to weather, briefly answer if it helps the conversation, then relate it back "
            "to weather when appropriate. Give practical advice and state uncertainty when necessary. "
            f"Respond naturally in {LANGUAGES.get(req.language, 'English')}."
        )
        prompt = (
            f"SYSTEM INSTRUCTIONS:\n{system}\n\n"
            f"RECENT CONVERSATION:\n{history_text or '(none)'}\n\n"
            f"CURRENT CITY: {req.city}\n"
            f"USER QUESTION: {req.message}\n\n"
            f"LIVE WEATHER DATA:\n{json.dumps(data, ensure_ascii=False)[:16000]}"
        )
        result = await asyncio.to_thread(
            client.models.generate_content,
            model=os.getenv("GEMINI_MODEL", "gemini-2.5-flash"),
            contents=prompt,
        )
        text = getattr(result, "text", None)
        if text and text.strip():
            return text.strip(), "gemini"
    except Exception as exc:
        print(f"Gemini unavailable, using offline fallback: {exc}")
    return offline_ai_answer(req, data), "offline-weather-ai"


async def stream_text(text: str) -> AsyncGenerator[str, None]:
    for word in text.split():
        yield f"data: {json.dumps({'token': word + ' '})}\n\n"
        await asyncio.sleep(0.025)
    yield "data: [DONE]\n\n"

@app.get("/", include_in_schema=False)
async def index():
    return FileResponse(WEB / "index.html")

@app.get("/app.js", include_in_schema=False)
async def app_js():
    return FileResponse(WEB / "app.js", media_type="application/javascript")

@app.get("/styles.css", include_in_schema=False)
async def css():
    return FileResponse(WEB / "styles.css", media_type="text/css")

@app.get("/manifest.webmanifest", include_in_schema=False)
async def manifest():
    return FileResponse(WEB / "manifest.webmanifest", media_type="application/manifest+json")

@app.get("/sw.js", include_in_schema=False)
async def sw():
    return FileResponse(WEB / "sw.js", media_type="application/javascript")

@app.get("/health")
async def health():
    return {"status": "ok", "service": "weathergpt-api", "time": now_iso()}

@app.get("/v1/weather")
async def weather(
    city: str = Query("Mysuru"),
    latitude: float | None = None,
    longitude: float | None = None,
):
    lat, lon, resolved = resolve_city(city)
    if latitude is not None and longitude is not None:
        lat, lon = latitude, longitude
    data = await open_meteo(lat, lon)
    return {
        "city": resolved,
        "current": data["current"],
        "daily": data["daily"],
        "hourly": data["hourly"],
        "provenance": provenance(data, lat, lon),
    }

@app.get("/v1/ai/status")
async def ai_status():
    configured = bool(os.getenv("GEMINI_API_KEY", "").strip())
    return {"configured": configured, "provider": "gemini" if configured else "offline-weather-ai", "model": os.getenv("GEMINI_MODEL", "gemini-2.5-flash")}


async def chat_data(req: ChatRequest):
    lat, lon, resolved = resolve_city(req.city)
    # A browser may send placeholder 0,0 coordinates. Prefer the selected city in that case.
    if abs(req.latitude) > 0.01 and abs(req.longitude) > 0.01:
        lat, lon = req.latitude, req.longitude
        resolved = req.city
    data = await open_meteo(lat, lon)
    return data, lat, lon, resolved


@app.post("/v1/chat")
async def chat(req: ChatRequest):
    data, lat, lon, resolved = await chat_data(req)
    req.city = resolved
    answer, model = await generate_agent_answer(req, data)
    return {"answer": answer, "intent": intent_for(req.message), "model": model, "provenance": provenance(data, lat, lon)}

@app.post("/v1/chat/stream")
async def chat_stream(req: ChatRequest):
    data, lat, lon, resolved = await chat_data(req)
    req.city = resolved
    answer, model = await generate_agent_answer(req, data)
    async def events():
        async for item in stream_text(answer):
            yield item
        meta = {"intent": intent_for(req.message), "model": model, "provenance": provenance(data, lat, lon)}
        yield f"event: metadata\ndata: {json.dumps(meta)}\n\n"
    return StreamingResponse(events(), media_type="text/event-stream")

@app.get("/v1/tools")
async def tools():
    return {
        "tools": [
            "get_now", "get_hourly", "get_daily", "get_model_run",
            "get_active_alerts", "get_climate_trend", "get_sector_advisory", "geo_resolve"
        ]
    }

@app.get("/v1/tools/get_now")
async def get_now(city: str = "Mysuru"):
    lat, lon, resolved = resolve_city(city)
    d = await open_meteo(lat, lon)
    return {"city": resolved, **d["current"], "provenance": provenance(d, lat, lon)}

@app.get("/v1/tools/get_hourly")
async def get_hourly(city: str = "Mysuru"):
    lat, lon, resolved = resolve_city(city)
    d = await open_meteo(lat, lon)
    return {"city": resolved, **d["hourly"], "provenance": provenance(d, lat, lon)}

@app.get("/v1/tools/get_daily")
async def get_daily(city: str = "Mysuru"):
    lat, lon, resolved = resolve_city(city)
    d = await open_meteo(lat, lon)
    return {"city": resolved, **d["daily"], "provenance": provenance(d, lat, lon)}

@app.get("/v1/tools/get_model_run")
async def get_model_run(city: str = "Mysuru"):
    lat, lon, _ = resolve_city(city)
    d = await open_meteo(lat, lon)
    return provenance(d, lat, lon)

@app.get("/v1/tools/get_active_alerts")
async def get_active_alerts(city: str = "Mysuru"):
    return {"city": city, "alerts": [a for a in alert_history if a.get("location") == city or a.get("location") == "all"]}

@app.get("/v1/tools/geo_resolve")
async def geo_resolve(city: str = "Mysuru"):
    lat, lon, resolved = resolve_city(city)
    return {"query": city, "city": resolved, "latitude": lat, "longitude": lon}

@app.get("/v1/tools/get_climate_trend")
async def climate_trend(city: str = "Mysuru"):
    # Demo-safe synthetic trend series; clearly labeled so it cannot be mistaken for IMD observations.
    years = list(range(2018, 2027))
    rainfall = [840, 820, 875, 790, 910, 860, 900, 885, 930]
    return {"city": city, "source": "WeatherGPT demo series", "years": years, "rainfall_mm": rainfall,
            "note": "Replace with IMD/NOAA historical observations for scientific use."}

@app.post("/v1/advisory")
async def advisory(req: AdvisoryRequest):
    data = await open_meteo(req.latitude, req.longitude)
    d = data["daily"]
    cards = []
    for i, day in enumerate(d["time"]):
        rain = d["precipitation_probability_max"][i]
        if req.sector == "agriculture":
            action = "Good spray window" if rain < 35 else "Avoid spraying; rain risk is elevated"
        elif req.sector == "aviation":
            action = "Review visibility/wind conditions before operations"
        elif req.sector == "marine":
            action = "Check wind and precipitation before sailing"
        else:
            action = "Review heat/rain risk and drainage readiness"
        cards.append({"date": day, "rain_probability": rain, "action": action})
    return {"sector": req.sector, "city": req.city, "calendar": cards, "provenance": provenance(data, req.latitude, req.longitude)}

@app.post("/v1/alerts/replay")
async def replay_alert(req: AlertRequest):
    alert = {
        "id": str(uuid.uuid4())[:8],
        "location": req.location,
        "severity": req.severity,
        "title": "WeatherGPT Storm Replay",
        "message": f"Demo alert: {req.severity.upper()} weather condition near {req.location}.",
        "issued_at": now_iso(),
        "acknowledged": False,
        "protocol": "WIS2.0-style MQTT / CAP demo",
    }
    alert_history.append(alert)
    dead = []
    for ws in alert_clients:
        try:
            await ws.send_json(alert)
        except Exception:
            dead.append(ws)
    for ws in dead:
        alert_clients.discard(ws)
    return {"status": "sent", "alert": alert}

@app.post("/v1/alerts/{alert_id}/ack")
async def ack_alert(alert_id: str):
    for a in alert_history:
        if a["id"] == alert_id:
            a["acknowledged"] = True
            return a
    raise HTTPException(404, "Alert not found")

@app.websocket("/ws/alerts")
async def ws_alerts(ws: WebSocket):
    await ws.accept()
    alert_clients.add(ws)
    try:
        await ws.send_json({"type": "connected", "message": "Live alert stream connected"})
        while True:
            await ws.receive_text()
    except WebSocketDisconnect:
        alert_clients.discard(ws)
    except Exception:
        alert_clients.discard(ws)

@app.get("/v1/trust")
async def trust():
    total = 100
    correct = 88
    return {
        "gold_set": {"questions": total, "correct": correct, "accuracy_percent": correct},
        "latency": {"ttft_seconds": 1.1, "p95_seconds": 3.4, "type": "demo baseline; measure in production"},
        "alerts": {"delivery_seconds": 2.4, "deduplication_percent": 96},
        "platform": {"uptime_percent": 99.0, "hpa_demo": "3→10 configured in Kubernetes manifests"},
        "languages": {k: 90 for k in LANGUAGES},
        "disclaimer": "These are demo/evaluation fixture values unless replaced by measured CI results.",
    }

@app.get("/v1/eval/goldset")
async def goldset():
    return JSONResponse((BASE / "eval" / "goldset.json").read_text())

