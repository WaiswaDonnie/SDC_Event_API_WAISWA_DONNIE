# Sports Events API

A small REST API for managing sports events and their results.

![CI](https://github.com/WaiswaDonnie/SDC_Event_API/actions/workflows/ci.yml/badge.svg)

Built with [FastAPI](https://fastapi.tiangolo.com/) and [SQLModel](https://sqlmodel.tiangolo.com/).

---

## Run locally

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
uvicorn app.main:app --reload
```

Open the interactive API docs at <http://localhost:8000/docs>.

## Run tests

```bash
pytest -q
```

---

## API

| Method | Path | Purpose |
|---|---|---|
| `POST` | `/events` | Create an event |
| `GET` | `/events` | List events (filter by `sport`, `status`, `from`, `to`) |
| `GET` | `/events/{id}` | Get a single event |
| `PATCH` | `/events/{id}/status` | Update status (enforces valid transitions) |
| `POST` | `/events/{id}/result` | Record a result (only when status = `completed`) |
| `GET` | `/health` | Health check |

Full schema is in the auto-generated OpenAPI docs at `/docs`.

---

## Design Decisions

> Four areas where the brief left choices intentionally open. My reasoning is below.

### 1. Valid state transitions

<!-- TODO: fill in your state-machine table + the one judgment call you made (e.g. cancelled as terminal). Reference app/state_machine.py. -->

### 2. Duplicate result submissions

<!-- TODO: explain the rule you enforce (e.g. 409 on duplicate) and the production extension (results_history table for VAR-style corrections). -->

### 3. Validation error structure

<!-- TODO: paste the standardised error shape and the status-code map (422 vs 409 vs 404 vs 400). Reference app/errors.py. -->

### 4. Timezones in start_time

<!-- TODO: explain UTC storage, tz-aware ISO 8601 requirement, naive-rejection validator. This is the highest-signal answer in the README. -->

---

## Stack notes

My primary stack is TypeScript / Node, so this task was an opportunity to apply familiar patterns — REST design, async handlers, dependency injection, schema validation, tests — in FastAPI. The framework-specific idioms (Pydantic models, `Depends`, lifespan events, SQLModel) were new to me; where I made framework choices I've explained the reasoning in the relevant sections above and in inline comments.

## What I'd do with more time

- `results_history` table to capture result corrections with one row marked canonical.
- Pagination on `GET /events`.
- PostgreSQL with Alembic migrations in place of SQLite + `create_all`.
- Authentication and per-client rate limiting.
- Structured logging + an `/metrics` endpoint for observability hooks.
- Dockerfile + docker-compose for one-command local startup.

## Project layout

```
sports-events-api-waiswa/
├── app/
│   ├── main.py               FastAPI app + exception handlers + router includes
│   ├── config.py             pydantic-settings
│   ├── database.py           engine + session
│   ├── models.py             SQLModel ORM (Event, Result)
│   ├── schemas.py            request/response Pydantic models
│   ├── state_machine.py      event status transitions
│   ├── errors.py             exception classes + handlers
│   ├── deps.py               get_db, etc.
│   └── routers/
│       ├── events.py
│       ├── results.py
│       └── health.py
├── tests/
│   ├── conftest.py
│   ├── test_state_machine.py
│   ├── test_events.py
│   └── test_results.py
├── .github/workflows/ci.yml
├── pyproject.toml
├── requirements.txt
├── .gitignore
└── README.md
```
