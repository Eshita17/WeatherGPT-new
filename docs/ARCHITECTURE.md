# WeatherGPT Architecture

## Runtime path
1. Browser/PWA sends a chat request to FastAPI.
2. FastAPI retrieves live Open-Meteo weather or a deterministic fixture.
3. Agent router classifies the request and produces a grounded answer.
4. SSE sends the answer progressively to the UI.
5. Provenance metadata is displayed with every answer.
6. Alerts use WebSocket delivery and can be replayed locally.
7. Advisory uses the seven-day forecast to create a sector-specific decision calendar.

## Production extension points
- Replace Open-Meteo enrichment with IMD/WIS2.0 adapters.
- Move each service into its own deployable container.
- Add TimescaleDB/PostGIS/pgvector persistence.
- Add EMQX MQTT ingestion and CAP XML parsing.
- Add Bhashini ASR/TTS.
- Add Prometheus/Grafana/Loki/OTel instrumentation.
