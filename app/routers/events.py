from fastapi import APIRouter, Depends, HTTPException, status
from sqlmodel import Session

from app.database import get_db
from app.models import Event, EventCreate, EventRead

router = APIRouter(prefix="/events", tags=["events"])

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