from typing import Any

from pydantic import BaseModel, ConfigDict


class ActivitySummary(BaseModel):
    """Summary of a completed activity from Intervals.icu."""

    model_config = ConfigDict(extra="ignore")

    id: str
    start_date_local: str
    type: str = "Ride"
    name: str | None = None
    moving_time: int | None = None
    elapsed_time: int | None = None
    distance: float | None = None
    icu_training_load: float | None = None
    icu_intensity: float | None = None
    icu_ftp: float | None = None
    average_watts: float | None = None
    icu_weighted_avg_watts: float | None = None
    max_watts: float | None = None
    average_heartrate: float | None = None
    max_heartrate: float | None = None
    average_cadence: float | None = None
    total_elevation_gain: float | None = None
    calories: float | None = None


class WellnessData(BaseModel):
    """Daily wellness record from Intervals.icu."""

    model_config = ConfigDict(extra="ignore")

    id: str  # date string YYYY-MM-DD
    weight: float | None = None
    restingHR: int | None = None  # noqa: N815
    hrv: float | None = None
    hrvSDNN: float | None = None  # noqa: N815
    sleepTime: float | None = None  # noqa: N815
    sleepScore: float | None = None  # noqa: N815
    atl: float | None = None
    ctl: float | None = None
    rampRate: float | None = None  # noqa: N815
    spO2: float | None = None  # noqa: N815
    steps: int | None = None
    kcalConsumed: float | None = None  # noqa: N815


class PlannedEvent(BaseModel):
    """Planned workout / calendar event from Intervals.icu."""

    model_config = ConfigDict(extra="ignore")

    id: int
    start_date_local: str
    category: str = "WORKOUT"
    name: str | None = None
    description: str | None = None
    type: str = "Ride"
    moving_time: int | None = None
    icu_training_load: float | None = None
    workout_doc: dict[str, Any] | None = None


class AthleteProfile(BaseModel):
    """Athlete profile from Intervals.icu."""

    model_config = ConfigDict(extra="ignore")

    id: int | str
    name: str | None = None
    ftp: float | None = None
    weight: float | None = None
    max_hr: int | None = None
    resting_hr: int | None = None
    lthr: int | None = None
