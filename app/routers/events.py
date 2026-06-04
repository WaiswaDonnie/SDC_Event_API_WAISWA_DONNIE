from app.models import ResultRead
from sqlalchemy.exc import IntegrityError # Importing IntegrityError to handle potential database integrity issues during event creation or updates
from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlmodel import Session, select
from datetime import datetime
from app.database import get_db
from app.models import Event, EventCreate, EventRead, Sport, Status, StatusUpdate,ResultCreate,Result,Winner
from app.state_machine import transition, InvalidStateTransition
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

@router.patch('/{event_id}/status', response_model=EventRead)
def update_event_status(
    event_id: int,
    payload:StatusUpdate,
    db: Session = Depends(get_db)
)-> Event:
    event = db.get(Event, event_id) # Fetch the event by ID
    if event is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Event not found")
    try:
        event.status =  transition(event.status, payload.status) # Attempt the state transition
    except InvalidStateTransition as e:  
         # Use 409 Conflict to indicate that the request could not be completed due to a conflict with the current state of the resource
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(e)) from e
    db.add(event) # Add the modified event back to the session (not strictly necessary since it's already in the session, but explicit)
    db.commit() # Commit the transaction to save the changes to the database
    db.refresh(event)
    return event


@router.post('/{event_id}/result',response_model=ResultRead, status_code=status.HTTP_201_CREATED)
def record_result(
    event_id: int,
    payload: ResultCreate,
    db: Session = Depends(get_db)) -> Result:
    event = db.get(Event, event_id)
    # 1 Ensure the event exists
    if event is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Event not found")
    # 2 Ensure the event is completed before recording a result
    if event.status != Status.COMPLETED:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=(
                f"Cannot record result for event with status '{event.status.value}'. "
                f"Event must be 'completed' first."
            ),
        )
        
    # 3. Score / winner consistency check (sanity guard).
    if payload.home_score > payload.away_score:
        expected = Winner.HOME
    elif payload.away_score > payload.home_score:
        expected = Winner.AWAY
    else:
        expected = Winner.DRAW
    if payload.winner != expected:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=(
                f"Winner '{payload.winner.value}' is inconsistent with scores "
                f"{payload.home_score}-{payload.away_score} "
                f"(expected '{expected.value}')."
            ),
        )
    
    # 4. layer 1: application-level duplicate check (friendly message).
    existing = db.exec(
        select(Result).where(Result.event_id == event_id)
    ).first()
    if existing is not None:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"A result already exists for event {event_id}.",
        )
    
    # 5. Insert. layer 2 (DB UNIQUE) + layer 3 (IntegrityError catch)
    #    handles the rare race-condition case where two concurrent requests
    #    both pass step 4.

    # we use this approach to leverage the validation and parsing of ResultCreate, while also adding the event_id in one step.
    result = Result.model_validate(payload, update={"event_id": event_id}) 
    # or we could simply use this
    # """
    # result = Result(
    #     event_id=event_id,
    #     home_score=payload.home_score,
    #     away_score=payload.away_score,
    #     winner=payload.winner,
    # """
    try:
        db.add(result)
        db.commit()
    except IntegrityError as exc:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"A result already exists for event {event_id}.",
        ) from exc
    db.refresh(result)
    return result
