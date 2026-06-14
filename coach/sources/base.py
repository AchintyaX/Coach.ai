from dataclasses import dataclass
from typing import Literal

CAPABILITIES: set[str] = {
    "readiness",
    "hrv",
    "sleep",
    "body_battery",
    "stress",
    "training_load",
    "vo2max",
    "training_effect",
    "activity_streams",
    "prs",
    "structured_workouts",
    "free_text_workouts",
}

ROLES: set[str] = {"metrics", "workout_calendar"}


@dataclass
class SourceSpec:
    name: str
    mcp_server_name: str
    command: str
    args: list[str]
    env: dict[str, str]
    enabled_tools: list[str]
    roles: set[str]
    capabilities: set[str]
    auth_steps: list[str]
    status: Literal["functional", "scaffold"]
