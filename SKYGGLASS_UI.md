# WeatherGPT-G — Skyglass UI

The web client has been redesigned around the supplied Skyglass reference: sky-blue gradients, translucent glass panels, soft clouds, lake/mountain atmosphere, rounded navigation, glass chat workspace, weather summary card, and responsive layouts.

## Run

```bash
cd ~/Downloads/WeatherGPT-G/apps/api
source ../../.venv/bin/activate
python -m uvicorn main:app --host 127.0.0.1 --port 8000
```

Open `http://127.0.0.1:8000/`.

If an older UI is still visible, hard refresh with **Cmd + Shift + R**. The service worker is versioned as `weathergpt-skyglass-v3` and the core assets use `?v=3` cache-busting.
