# Repository Guidelines

## Project Structure & Module Organization
- `bms-monitor/app`: FastAPI backend — `api/`, `services/`, `models/`, `utils/`.
- `bms-monitor/requirements.txt`: Python dependencies for the service.
- `battery-monitor/docker`: Docker configs (e.g., Mosquitto). Frontend folder may be added later.
- `bms-bluetooth-poc/`: Protocol research and BLE test scripts (`core/`, `archive/`, `docs/`).
- Root files: `docker-compose.yml`, `.env`, `README.md`.

## Build, Test, and Development Commands
- Install deps: `pip install -r requirements.txt` (root) or `pip install -r bms-monitor/requirements.txt`.
- Run API (dev): `cd bms-monitor && python -m uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload`.
- Run with Docker: `docker compose up -d --build` (uses `docker-compose.yml`).
- Quick BLE tests: `python bms-monitor/app/utils/daly_d2_modbus_test.py`.
- Health check: `curl http://localhost:8000/api/status`.

## Coding Style & Naming Conventions
- Python 3.11+, 4‑space indentation, PEP8.
- Modules/functions: `snake_case`; classes: `PascalCase`; constants: `UPPER_SNAKE_CASE`.
- Place API routes in `app/api`, services in `app/services`, configuration in `app/config.py`.
- Prefer type hints and docstrings for public functions.

## Testing Guidelines
- Framework: pytest (recommended). Create `tests/` with files `test_*.py`.
- Run tests (if added): `pytest -q`.
- For now, validate via endpoints (`/`, `/api/*`) and WebSocket `/ws`; keep small, focused tests around services (e.g., cache/mqtt stubs).
- Aim for coverage on critical paths (BMS read/parse, alert rules).

## Commit & Pull Request Guidelines
- Commits: short, imperative summary; optional emoji + scope (e.g., "✨ api: add voltage alert").
- PRs: clear description, linked issue, steps to reproduce/verify, screenshots of `/docs` when UI/API changes.
- Include config notes for new env vars in `.env` and update `docker-compose.yml` if required.
- Keep changes small and focused; add migration notes if DB schemas change.

## Security & Configuration Tips
- Secrets live in `.env` (e.g., `DATABASE_URL`, `REDIS_URL`, `MQTT_BROKER_URL`, `BMS_MAC_ADDRESS`). Do not commit secrets.
- When using Docker, the service runs with `network_mode: host` and `privileged: true` for BLE access — limit to trusted hosts.
- Prefer local dev without privileges when BLE is not required.

