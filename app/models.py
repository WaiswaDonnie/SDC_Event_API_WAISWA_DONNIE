from datetime import datetime, timezone
from enum import Enum

from pydantic import field_validator
from sqlmodel import Field, SQLModel


# Enums use (str, Enum) so values store as strings in SQLite and serialise as
# strings in JSON. UPPER_CASE members per PEP 8.

class Sport(str, Enum):
    FOOTBALL = "football"
    BASKETBALL = "basketball"
    TENNIS = "tennis"
    OTHER = "other"


class Status(str, Enum):
    SCHEDULED = "scheduled"
    LIVE = "live"
    COMPLETED = "completed"
    CANCELLED = "cancelled"


class Winner(str, Enum):
    HOME = "home"
    AWAY = "away"
    DRAW = "draw"


# EventBase = the fields a CLIENT provides when creating an event.
# Server-controlled fields (id, status) live on Event below.
class EventBase(SQLModel):
    name: str
    sport: Sport
    start_time: datetime
    venue: str

    @field_validator("start_time")
    @classmethod
    def validate_start_time(cls, value: datetime) -> datetime:
        if value.tzinfo is None:
            raise ValueError(
                "start_time must include a timezone offset "
                "(e.g. '2026-06-03T14:00:00+01:00' or '...Z')"
            )
        return value.astimezone(timezone.utc)


# Event = the actual DB table. Adds server-controlled fields.
class Event(EventBase, table=True):
    id: int | None = Field(default=None, primary_key=True)
    status: Status = Field(default=Status.SCHEDULED)


# What POST /events accepts as the request body.
class EventCreate(EventBase):
    pass


# What GET /events and GET /events/{id} return.
class EventRead(EventBase):
    id: int
    status: Status


# ResultBase = what the client provides when recording a result.
class ResultBase(SQLModel):
    home_score: int = Field(ge=0)
    away_score: int = Field(ge=0)
    winner: Winner


# Result = the DB table.
# Decision 2: unique=True on event_id enforces "one canonical result per event"
# at the database level (belt-and-braces with the application-level 409 we'll add).
# index=True speeds up event_id lookups.
class Result(ResultBase, table=True):
    id: int | None = Field(default=None, primary_key=True)
    event_id: int = Field(foreign_key="event.id", unique=True, index=True)


class ResultCreate(ResultBase):
    pass


class ResultRead(ResultBase):
    id: int
    event_id: int