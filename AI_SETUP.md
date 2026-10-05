# WeatherGPT AI assistant setup

WeatherGPT-new has two chat modes:

1. **Gemini conversational AI (recommended):** set `GEMINI_API_KEY` in a `.env` file at the project root. The assistant then answers the user's actual question, keeps recent conversation context, uses live Open-Meteo weather data, and cites the weather source/model in the UI.
2. **Offline weather-AI fallback:** if no key is configured, the app remains runnable and uses a query-aware local fallback. It is not a general-purpose LLM and is intentionally limited to weather information.

## Enable full AI

From the project root:

```bash
cp .env.example .env
```

Open `.env` and set:

```text
GEMINI_API_KEY=YOUR_KEY_HERE
GEMINI_MODEL=gemini-2.5-flash
```

Then restart Uvicorn. The home page will show **AI Assistant Online** when the key is loaded.

## Verify

```bash
curl http://127.0.0.1:8000/v1/ai/status
```

A configured assistant returns `"provider":"gemini"`.

Never commit `.env` or expose the API key in frontend JavaScript.
