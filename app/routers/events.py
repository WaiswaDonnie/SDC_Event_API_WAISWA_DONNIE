from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlmodel import Session, select
from datetime import datetime
from app.database import get_db
from app.models import Event, EventCreate, EventRead, Sport, Status

router = APIRouter(prefix="/events", tags=["events"])

@router.get('/', response_model=list[EventRead])
def list_events(
    sport: Sport | None = None,
    event_status: Status | None = Query(default=None, alias="status"),
    start_from: datetime | None = Query(default=None, alias="from"),
    start_to: datetime | None = Query(default=None, alias="to"),
    db: Session = Depends(get_db),
) -> list[Event]:
    statement = select(Event)
    if sport is not None:
        statement = statement.where(Event.sport == sport)
    if event_status is not None:
        statement = statement.where(Event.status == event_status)
    if start_from is not None:
        statement =  statement.where(Event.start_time >= start_from)
    if start_to is not None:
        statement =  statement.where(Event.start_time <= start_to)
    events = db.exec(statement).all()
    if not events:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="No events found matching the criteria")
    return events


@router.post('/', response_model=EventRead, status_code=status.HTTP_201_CREATED)
def create_event(payload: EventCreate, db: Session = Depends(get_db)):
    event = Event.model_validate(payload) # Convert the EventCreate Pydantic model to an Event SQLModel instance
    db.add(event) # Add the new event to the database session
    db.commit() # Commit the transaction to save the new event to the database
    db.refresh(event) # Refresh the event instance to get the generated ID and any default values from the database
    return event


@router.get('/{event_id}', response_model=EventRead)
def get_event(event_id: int, db: Session = Depends(get_db))-> Event:
    event = db.get(Event, event_id)
    if event is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Event not found")
    return event

