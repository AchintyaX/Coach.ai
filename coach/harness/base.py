"""Contract for installing Coach AI into an agent harness.

A small Python ABC defines the contract every agent harness must satisfy
(see techspec section 5.1). Concrete implementations (``ClaudeHarness``,
``CodexHarness``, ...) write to harness-specific files but share the same
public surface, so the rest of ``coach`` (skills, sources, storage) never
needs to know which harness is active.

This module also hosts the ``{{tool: ...}}`` placeholder-resolution table
used by ``install_skills()`` to render each ``SKILL.md`` for the active
path's concrete tools (techspec sections 5.5, 6a, 6b, 7).
"""

from __future__ import annotations

import re
from abc import ABC, abstractmethod
from pathlib import Path

from coach.sources.base import SourceSpec

__all__ = [
    "BaseHarness",
    "TOOL_PLACEHOLDERS",
    "resolve_tool_placeholder",
    "render_skill",
]


# ---------------------------------------------------------------------------
# {{tool: ...}} placeholder resolution
# ---------------------------------------------------------------------------

# Each entry maps a placeholder name to its resolution on each of the two
# Milestone 1 paths:
#   - "garmin": active when "structured_workouts" is in the capability set.
#   - "strava_calendar": active when "free_text_workouts" is in the
#     capability set (and "structured_workouts" is not).
#
# Where a capability simply doesn't exist on a path, the resolution is a
# short human-readable note describing what the agent should do instead
# (skip the step, or omit it) rather than a tool name.
TOOL_PLACEHOLDERS: dict[str, dict[str, str]] = {
    "fitness_assessment": {
        "garmin": "get_training_status, get_training_readiness, get_vo2max_trend",
        "strava_calendar": "get-athlete-stats, get-activities, get-segment-prs",
    },
    "readiness_metrics": {
        "garmin": (
            "get_training_readiness, get_morning_training_readiness, "
            "get_hrv_data, get_sleep_data, get_body_battery"
        ),
        "strava_calendar": "not available on this path — skip this step entirely",
    },
    "recent_training_load": {
        "garmin": "get_training_status, get_activities, get_training_load_trend",
        "strava_calendar": "get-activities, get-activity-streams",
    },
    "structured_workout_create": {
        "garmin": "create_walk_run_workout / create_z2_walk_workout / create_strength_workout",
        "strava_calendar": "create-event",
    },
    "schedule_workout": {
        "garmin": "schedule_workout / schedule_week",
        "strava_calendar": "covered by create-event above — no separate call",
    },
    "activity_detail": {
        "garmin": "get_activity",
        "strava_calendar": "get-activity-streams",
    },
    "recent_load_context": {
        "garmin": "get_activities, get_training_load_trend",
        "strava_calendar": "get-activities",
    },
    "find_scheduled_workout": {
        "garmin": "get_scheduled_workouts",
        "strava_calendar": "list-events / get-event",
    },
    "modify_workout": {
        "garmin": "unschedule_workout -> create_* -> schedule_workout",
        "strava_calendar": "update-event",
    },
    "body_battery_optional": {
        "garmin": "get_body_battery",
        "strava_calendar": "not available on this path — omit",
    },
}

# Matches `{{tool: <name>}}`, allowing for surrounding whitespace, e.g.
# "{{tool: readiness_metrics}}" or "{{tool:readiness_metrics}}".
_PLACEHOLDER_RE = re.compile(r"\{\{\s*tool:\s*([a-zA-Z0-9_]+)\s*\}\}")


def resolve_tool_placeholder(name: str, capabilities: set[str]) -> str:
    """Resolve a ``{{tool: <name>}}`` placeholder for the active capability set.

    Picks the Garmin-path resolution if ``"structured_workouts"`` is in
    ``capabilities``, else the Strava+Calendar-path resolution if
    ``"free_text_workouts"`` is in ``capabilities``. If ``name`` isn't a
    known placeholder, it's returned unchanged (rendered as-is).
    """
    entry = TOOL_PLACEHOLDERS.get(name)
    if entry is None:
        return name

    if "structured_workouts" in capabilities:
        return entry["garmin"]
    if "free_text_workouts" in capabilities:
        return entry["strava_calendar"]

    # Fall back to the Garmin-path resolution if neither marker capability
    # is present (shouldn't normally happen for the two M1 paths, but keeps
    # this total rather than raising).
    return entry["garmin"]


def render_skill(content: str, capabilities: set[str]) -> str:
    """Replace every ``{{tool: <name>}}`` occurrence in ``content``.

    Each placeholder is resolved via ``resolve_tool_placeholder`` for the
    active ``capabilities`` set.
    """

    def _sub(match: re.Match[str]) -> str:
        return resolve_tool_placeholder(match.group(1), capabilities)

    return _PLACEHOLDER_RE.sub(_sub, content)


# ---------------------------------------------------------------------------
# BaseHarness
# ---------------------------------------------------------------------------


class BaseHarness(ABC):
    """Contract for installing Coach AI into an agent harness."""

    def __init__(self, project_dir: Path):
        self.project_dir = Path(project_dir)

    @abstractmethod
    def install_personality(self, text: str) -> Path:
        """Write/merge the coach personality into the harness's instructions file."""

    @abstractmethod
    def register_mcp_server(self, spec: SourceSpec) -> Path:
        """Add an MCP server entry (command, args, env, enabled tools) for `spec`."""

    @abstractmethod
    def install_skills(self, skills_dir: Path, capabilities: set[str]) -> list[Path]:
        """Install skills whose required capabilities subset `capabilities`.

        Renders each ``SKILL.md``'s tool list/procedure for the active path
        before copying.
        """

    @abstractmethod
    def setup_source(self, spec: SourceSpec) -> None:
        """Run auth + register_mcp_server for a data source end-to-end."""

    @abstractmethod
    def verify(self) -> dict[str, bool]:
        """Sanity-check that files exist and are well-formed; returns a status map."""
