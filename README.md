# SDC Events API

A small REST API for managing sports events and their results. Built with FastAPI and SQLModel.

[![CI](https://github.com/WaiswaDonnie/SDC_Event_API_WAISWA_DONNIE/actions/workflows/ci.yml/badge.svg)](https://github.com/WaiswaDonnie/SDC_Event_API_WAISWA_DONNIE/actions/workflows/ci.yml)

## Quick Start

```bash
# 1. Set up Python environment
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt

# 2. Run the server
uvicorn app.main:app --reload
```

The API runs on <http://localhost:8000>. Interactive docs at <http://localhost:8000/docs>.

The database (`sport_events.db`) is created automatically on first startup, so there's no migration step to run.

## Run tests

```bash
pytest -v
```

There are 27 tests total. The state machine has pure unit tests that don't touch a database or HTTP. The endpoint tests use FastAPI's `TestClient` with an in-memory SQLite database, swapped in via `dependency_overrides` so each test session gets a fresh DB.

---

## Endpoints

| Method | Path | Description |
|--------|------|-------------|
| POST   | /events | Create an event |
| GET    | /events | List events. Filter by sport, status, date range |
| GET    | /events/{event_id} | Get a single event |
| PATCH  | /events/{event_id}/status | Update status (valid transitions only) |
| POST   | /events/{event_id}/result | Record a result (completed events only) |
| GET    | /health | Health check including DB connectivity |

---

## Design Decisions

The brief left four questions intentionally open. Here's how I thought about each.

### 1. State transitions

Events move through a small state machine: `scheduled → live → completed`, with `cancelled` reachable from either of the first two states. Once an event hits `completed` or `cancelled`, it can't move anywhere else.

**Decision:** I pulled the rules out into a separate module (`app/state_machine.py`) instead of inlining the if/else in the route handler. The rules live in a single dict (`ALLOWED_TRANSITIONS`) which acts as the source of truth, and a `transition()` function either returns the new status or raises `InvalidStateTransition`.

Two reasons I made it a module rather than inline:
- It's pure Python with no DB or HTTP dependencies, so I can unit test the rules in isolation (see `tests/test_state_machine.py`).
- The brief said this should feel like the start of a codebase. If another resource needed transitions later (orders, payments, etc.) I'd refactor this into a generic `StateMachine` class parameterised by a transitions dict.

For invalid transitions I return **409 Conflict**, not 400. The request itself is well-formed; what's wrong is the state of the resource. 409 is the spec definition of "request can't be fulfilled because of a conflict with the resource's current state", which matched my mental model better than "client sent bad data".

### 2. Duplicate results

Each event can have one result. A second POST returns 409.

I enforce this at three layers, ordered cheapest to most defensive:

1. **Application check** in the route handler. Before insert, I query for an existing result. If one exists, return 409 with a clear message. This is what catches normal usage.
2. **DB UNIQUE constraint** on `result.event_id`. If two concurrent requests both pass the application check (race condition), the second one fails at the DB layer.
3. **`IntegrityError` catch** around `db.commit()`. Translates the DB-layer rejection from step 2 into a clean 409 instead of letting it bubble up as a 500.

For most take-home scopes, the application check alone is enough. I added the DB constraint and the IntegrityError catch because the brief asked specifically about "what if a result is submitted more than once" — to me that question is really about concurrency, not about a single user clicking twice.

If result corrections become a real requirement later (a VAR review overturning a goal, for example), I'd add a `results_history` table with one row marked canonical. For now, "one result per event" is the simpler invariant.

I also require `event.status == "completed"` before accepting a result. Submitting one for a `scheduled` or `live` event returns 409 with a different message, since that's a domain error, not a duplicate.

There's also a small sanity check on the payload itself: if the scores don't match the `winner` (for example `3-1` with `winner: "draw"`), I return 422. The brief doesn't ask for this, but it's three lines and catches obvious client bugs.

### 3. Validation error structure

Every error response from the API has the same shape:

```json
{
  "error": {
    "code": "<machine_code>",
    "message": "<human_message>",
    "details": null | [...]
  }
}
```

The `code` field maps to the HTTP status:

| HTTP | code |
|------|------|
| 400 | bad_request |
| 404 | not_found |
| 409 | conflict |
| 422 | unprocessable_entity (or validation_error for Pydantic) |
| 500 | internal_server_error |

**Decision:** FastAPI's default error responses are inconsistent: `HTTPException` returns `{detail: string}`, Pydantic validation returns `{detail: [list of objects]}`. A client has to write two error parsers.

I wrapped both in a single envelope via exception handlers in `app/errors.py` so a client only has to write one parser. For Pydantic errors, the per-field details go into the `details` field of the envelope. I had to wrap the content in `jsonable_encoder` because Pydantic's error context can contain raw Python exception objects, which `json.dumps` can't serialise.

For a six-endpoint API you could argue the default FastAPI shape is fine. I went with the envelope because the brief described this as the start of a codebase: standardising the error contract early is cheaper than retrofitting it later when a frontend has been written against the inconsistent default.

### 4. Timezone handling

The API accepts ISO 8601 datetimes with an explicit timezone offset, and rejects naive datetimes. Everything is stored as UTC.

Examples:
- `2025-08-10T15:00:00+01:00` accepted, stored as `14:00 UTC`
- `2025-08-10T15:00:00Z` accepted, already UTC
- `2025-08-10T15:00:00` rejected with 422

**Decision:** I never default a missing timezone to UTC or server-local time. The client is the only thing that knows the correct context, so if they don't tell us, we reject the request. That avoids the common bug where systems quietly assume the wrong timezone.

There's a small SQLite quirk I had to work around. SQLite strips `tzinfo` on read, so even after I store an aware UTC datetime, the next read returns a naive one. I handle this with two validators:

- `EventCreate.validate_start_time` rejects naive input and normalises aware input to UTC. Runs on every POST.
- `EventRead.assume_utc` re-attaches UTC to anything coming back from the database. This is safe because the input validator guarantees everything in storage is UTC.

In production on PostgreSQL I'd use `TIMESTAMP WITH TIME ZONE`, which preserves tzinfo through storage. That would remove the need for the output-side validator and leave only the input boundary check.

All API responses include a UTC offset (typically `+00:00` or `Z`). Clients are responsible for converting to local time for display.

---

## Stack notes

My day-to-day stack is TypeScript and Node, so this task was my first time writing FastAPI. I leaned on patterns I already knew (REST design, async handlers, dependency injection, schema validation, integration tests) and learned the Python-specific bits as I went: Pydantic v2 validators, SQLModel's `table=True` plus the base/create/read split, `Depends` for session injection, and FastAPI's `lifespan` context manager for startup/shutdown. Where I made framework-specific choices, the reasoning is in the relevant section above and in inline comments.

---
## Project Layout

```
SDC_Event_API_WAISWA_DONNIE/
├── app/
│   ├── main.py               FastAPI app, lifespan, error handler registration, /health
│   ├── database.py           SQLite engine, get_db session dependency, create_db_and_tables
│   ├── models.py             SQLModel classes (Event, Result, EventCreate, EventRead, etc.)
│   ├── state_machine.py      ALLOWED_TRANSITIONS, InvalidStateTransition, transition()
│   ├── errors.py             Standardised error envelope and FastAPI exception handlers
│   └── routers/
│       └── events.py         POST, GET, PATCH, POST-result handlers
├── tests/
│   ├── conftest.py           In-memory SQLite fixtures, dependency_overrides
│   ├── test_state_machine.py 13 unit tests, no DB
│   └── test_events.py        14 integration tests covering all four design decisions
├── .github/workflows/ci.yml  ruff + pytest on push and PR
├── pyproject.toml
├── requirements.txt
└── README.md
```

---

## What I'd do with more time

- Move to PostgreSQL with Alembic for schema migrations. That removes the SQLite timezone workaround and supports schema evolution properly.
- Add a `results_history` table to capture corrections (VAR-style review overturning a goal), with one row per event marked canonical. The current single-row design picks simplicity over audit history.
- Pagination on `GET /events`. Today it returns the full list. I'd add `cursor` or `limit` / `offset` parameters.
- Idempotency keys on `POST /events` using the Stripe-style `Idempotency-Key` header, so accidental client retries don't create duplicate events.
- Authentication and per-client rate limiting (JWT or API key based).
- Structured logging with request IDs, OpenTelemetry traces, and a `/metrics` endpoint for observability.
- Docker and docker-compose for one-command local startup, including a Postgres service.
- Refactor `state_machine.py` into a generic `StateMachine` class parameterised by a transitions dict, once a second domain needs state transitions.