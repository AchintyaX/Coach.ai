"""Functional matrix row: adjust-workout (techspec section 13).

- ``{{tool: find_scheduled_workout}}``:
  - Garmin: ``get_scheduled_workouts``.
  - Strava+Calendar: ``list-events / get-event``.

- ``{{tool: modify_workout}}`` (both Full):
  - Garmin: ``unschedule_workout -> create_* -> schedule_workout``.
  - Strava+Calendar: ``update-event``.
"""

from __future__ import annotations

from coach.harness.base import render_skill
from tests.functional_helpers import (
    GARMIN_CAPABILITIES,
    STRAVA_CALENDAR_CAPABILITIES,
    read_skill,
)


def test_garmin_path_resolves_find_and_modify_workout():
    content = read_skill("adjust-workout")

    rendered = render_skill(content, GARMIN_CAPABILITIES)

    assert "{{tool:" not in rendered
    allowed_tools_line = next(
        line for line in rendered.splitlines() if line.startswith("allowed-tools:")
    )
    assert "get_scheduled_workouts" in allowed_tools_line
    assert "unschedule_workout -> create_* -> schedule_workout" in allowed_tools_line

    assert "Apply the adjustment via `unschedule_workout -> create_* -> schedule_workout`." in rendered


def test_strava_calendar_path_resolves_find_and_modify_workout():
    content = read_skill("adjust-workout")

    rendered = render_skill(content, STRAVA_CALENDAR_CAPABILITIES)

    assert "{{tool:" not in rendered
    allowed_tools_line = next(
        line for line in rendered.splitlines() if line.startswith("allowed-tools:")
    )
    assert "list-events / get-event" in allowed_tools_line
    assert "update-event" in allowed_tools_line
    assert "unschedule_workout" not in allowed_tools_line

    assert "Apply the adjustment via `update-event`." in rendered
