from fastapi import Depends, FastAPI, HTTPException, status
from sqlalchemy import text
from sqlmodel import Session
from app.database import get_db

from contextlib import asynccontextmanager  # Turns a generator into an async context manager (required for lifespan)
from app.errors import register_error_handlers

from app import models  # noqa: F401 — register Event/Result tables with SQLModel metadata
from app.database import init_db  # Creates database tables from registered models on startup
from app.routers import events  # Import the events router, which defines all /events endpoints

@asynccontextmanager  # FastAPI expects lifespan to be an async context manager, not a plain async function
async def lifespan(app: FastAPI):  # Runs once when the server starts and once when it shuts down
    init_db()  # Startup: create SQLite tables if they do not exist yet
    yield  # Hand off to the running app; code after yield would run on shutdown

app = FastAPI(title="Sports Events Api",lifespan=lifespan)  # Application instance; pass lifespan= here to run init_db
register_error_handlers(app)

app.include_router(events.router)  # Include the events router, which defines all /events endpoints

@app.get("/")
def root():
    return {"message": "Welcome to the Sports Events API!"}

@app.get("/health")
def health_check(db: Session = Depends(get_db)) -> dict[str, str]:
    """
    Verifies the service is alive AND its downstream dependencies are reachable.

    Returns 200 with a status breakdown if everything is healthy.
    Returns 503 (via our standard error envelope) if a dependency is down —
    suitable for load-balancer / Kubernetes readiness probes.
    """
    try:
        db.execute(text("SELECT 1"))
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=f"Database unreachable: {exc}",
        ) from exc

    return {"status": "ok", "database": "ok"}