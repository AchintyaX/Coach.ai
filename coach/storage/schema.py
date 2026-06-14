from typing import Literal, Optional

from pydantic import BaseModel, Field


class Goal(BaseModel):
    id: str
    title: str
    sport: str
    goal_type: Literal["event", "metric", "habit"]
    target_date: Optional[str] = None
    target_metrics: dict = Field(default_factory=dict)
    priority: str
    status: str
    created: str
    notes: Optional[str] = None
    research_file: Optional[str] = None


class PlanNote(BaseModel):
    date: str
    sport: str
    intent: str
    rationale: str
    goal_id: Optional[str] = None
    block_context: Optional[str] = None
    target_summary: str
    workout_ref: Optional[str] = None
    workout_source: Optional[Literal["garmin", "google_calendar", "outlook_calendar"]] = None


class Subjective(BaseModel):
    energy: int
    soreness: int
    mood: int
    sleep_quality: int
    notes: Optional[str] = None


class MetricsSnapshot(BaseModel):
    training_readiness: Optional[int] = None
    hrv: Optional[float] = None
    sleep: Optional[dict] = None
    body_battery: Optional[int] = None


class ReadinessCheckin(BaseModel):
    date: str
    subjective: Subjective
    metrics_snapshot: Optional[MetricsSnapshot] = None
    recommendation: str
