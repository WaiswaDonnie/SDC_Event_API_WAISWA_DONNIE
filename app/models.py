from enum import Enum
from datetime import datetime

from pydrantic import field_validator
from sqlmodel import SQLModel, Field
#First creating the enums
class Sport(str,Enum):
    Football = "football"
    Basketball = "basketball"
    Tennis = "tennis"
    Other = "other"

class Status(str,Enum):
    Scheduled = "scheduled"
    Live = "live"
    Completed = "completed"
    Cancelled = "cancelled"

class Winner(str,Enum):
    Home = "home"
    Away = "away"
    Draw = "draw"
# End of Enums

# Now I have to create to two models, Event and Result
class EventBase(SQLModel):
    name: str
    sport: Sport
    status: Status
    venue: str
    start_time: datetime

    @field_validator('start_time')
    @classmethod
    def validate_start_time(cls, value):
        if value.tzinfo is None:
            raise ValueError("start_time must be timezone-aware")
        return value

class Event(EventBase, table=True):
    id: int = Field(default=None, primary_key=True)
    status: Status = Field(default=Status.Scheduled)

class CreateEvent(EventBase):
    pass

class GetEvent(EventBase):
    id: int
    status: Status

class ResultBase(SQLModel):
    winner: Winner
    home_score: int | None = None
    away_score: int | None = None


class Result(ResultBase, table=True):
    id: int = Field(default=None, primary_key=True)
    event_id: int = Field(foreign_key="event.id", unique=True,index=True)