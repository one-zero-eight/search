"""Pure external-service argument models; no agent or calendar dependencies."""

from datetime import date, datetime
from typing import Literal

from pydantic import BaseModel, Field, field_validator, model_validator

from catix.common.dates import ClockTime
from catix.innohassle.identifiers import validate_outlook_id, validate_room_id
from catix.settings import settings

DEFAULT_DAYS = DEFAULT_SCHEDULE_DAYS = MAX_MUSIC_DAYS = 7
DEFAULT_EVENTS_WINDOW_DAYS = 14


class FutureSpan(BaseModel):
    day: date = Field(description="YYYY-MM-DD")
    time_from: ClockTime = Field(description="HH:MM")
    time_to: ClockTime = Field(description="HH:MM")

    @model_validator(mode="after")
    def future_span(self):
        start = datetime.combine(self.day, self.time_from, settings.tz)
        end = datetime.combine(self.day, self.time_to, settings.tz)
        if end <= start:
            raise ValueError("time_to must be after time_from.")
        if start <= datetime.now(settings.tz):
            raise ValueError("That time is already past: ask the asker for a time to come.")
        return self


class GetMyScheduleArgs(BaseModel):
    date_from: date | None = Field(None, description="YYYY-MM-DD, default today.")
    date_to: date | None = Field(
        None, description=f"YYYY-MM-DD inclusive, default date_from + {DEFAULT_DAYS - 1} days."
    )


class GetFreeRoomsArgs(BaseModel):
    day: date | None = Field(None, description="YYYY-MM-DD, default today.")
    time_from: ClockTime = Field(description="HH:MM")
    time_to: ClockTime = Field(description="HH:MM")


class BookMusicRoomArgs(FutureSpan):
    pass


class BookRoomArgs(FutureSpan):
    room_id: str = Field(max_length=80, description="The `room_id` from get_free_rooms.")
    title: str = Field(max_length=100, description="What the booking is for, as the asker said it ('Встреча команды').")
    _room_id = field_validator("room_id")(validate_room_id)


class EnrollArgs(BaseModel):
    event_id: str = Field(pattern="^[0-9a-f]{24}$")
    leave: bool = Field(False, description="true to cancel the asker's enrolment instead.")


class CancelBookingArgs(BaseModel):
    service: Literal["music_room", "room"] = Field(description="The `service` of the booking from get_my_schedule.")
    booking_id: str = Field(max_length=200, description="The `booking_id` of the booking from get_my_schedule.")
    _booking_id = field_validator("booking_id")(validate_outlook_id)

    @model_validator(mode="after")
    def music_identifier(self):
        if self.service == "music_room" and (not self.booking_id.isdigit()):
            raise ValueError("No such music room booking: take its booking_id from account_get_my_schedule.")
        return self


class GetSportTrainingsArgs(BaseModel):
    date_from: date | None = Field(None, description="YYYY-MM-DD, default today.")
    date_to: date | None = Field(
        None, description=f"YYYY-MM-DD inclusive, default date_from + {DEFAULT_DAYS - 1} days."
    )
    sport: str | None = Field(
        None,
        max_length=60,
        description="Only this sport, by a part of its name as in get_sports (such as 'Volleyball').",
    )


class GetSportsArgs(BaseModel):
    sport: str | None = Field(
        None, max_length=60, description="One sport, by a part of its name: its groups, trainers, rules."
    )


class SportCheckinArgs(BaseModel):
    training_id: int = Field(gt=0, description="The `training_id` from get_sport_trainings or get_my_sport.")
    cancel: bool = Field(False, description="true: cancel the asker's check-in to this training.")


class GetCoursesArgs(BaseModel):
    query: str = Field(
        max_length=80,
        description="A course ('Operating Systems', 'Операционные системы', 'AWA') or a teacher's name in English or Russian ('Zuev', 'Зуев'). Plain words, no group or year.",
    )


class GetRoomTimetableArgs(BaseModel):
    day: date | None = Field(None, description="YYYY-MM-DD, default today.")
    room: str | None = Field(
        None, max_length=20, description="A room number ('108', '313'). Omit to find the rooms without classes."
    )
    time_from: ClockTime | None = Field(
        None, description="HH:MM: the start of the time the rooms must be free (without `room`); default now."
    )
    time_to: ClockTime | None = Field(None, description="HH:MM: its end; default 90 minutes after time_from.")


class GetMusicRoomScheduleArgs(BaseModel):
    date_from: date | None = Field(None, description="YYYY-MM-DD, default today.")
    date_to: date | None = Field(
        None, description=f"YYYY-MM-DD inclusive, default date_from; at most {MAX_MUSIC_DAYS} days."
    )


class GetClubsArgs(BaseModel):
    query: str | None = Field(
        None, description="Keywords in English, e.g. 'chess', 'dance', 'robotics'. Club data is in English."
    )
    type: Literal["tech", "sport", "hobby", "art"] | None = None
    include_inactive: bool = Field(False, description="Also return closed clubs.")


class GetUniversityEventsArgs(BaseModel):
    date_from: date | None = Field(None, description="YYYY-MM-DD, default today.")
    date_to: date | None = Field(
        None, description=f"YYYY-MM-DD inclusive, default date_from + {DEFAULT_EVENTS_WINDOW_DAYS} days."
    )
    query: str | None = Field(None, description="Optional keywords to filter by.")


class FindRoomArgs(BaseModel):
    query: str = Field(description="Room number ('319'), place ('canteen', 'printer') or person surname.")


class GetScheduleArgs(BaseModel):
    group: str = Field(pattern="\\S")
    date_from: date | None = Field(None, description="YYYY-MM-DD, default today.")
    date_to: date | None = Field(
        None, description=f"YYYY-MM-DD inclusive, default date_from + {DEFAULT_SCHEDULE_DAYS - 1} days."
    )
    query: str | None = Field(None, description="Filter by words in the class title, e.g. 'lab', 'Programming'.")
