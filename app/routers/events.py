from fastapi import APIRouter

router = APIRouter(prefix="/events", tags=["events"])

@router.get("/_ping")
def ping():
    return {"router:": "events", "status": "ok"}