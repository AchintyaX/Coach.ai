"""Functional matrix row: generate-daily-workout (techspec section 13).

- Garmin (Full): ``{{tool: structured_workout_create}}`` resolves to
  ``create_walk_run_workout / create_z2_walk_workout / upload_workout (strength)``,
  and ``{{tool: schedule_workout}}`` resolves to ``schedule_workout / schedule_week``.
- Strava+Calendar (Degraded): ``{{tool: structured_workout_create}}`` resolves
  to ``create-event``, and ``{{tool: schedule_workout}}`` resolves to
  "covered by create-event above — no separate call". A ``PlanNote`` with
  ``workout_source="google_calendar"`` validates against
  ``coach/storage/schema.py``.
"""

from __future__ import annotations

from coach.harness.base import render_skill
from coach.storage.schema import PlanNote
from tests.functional_helpers import (
    GARMIN_CAPABILITIES,
    STRAVA_CALENDAR_CAPABILITIES,
    read_skill,
)


def test_garmin_path_resolves_structured_workout_create_and_schedule():
    content = read_skill("generate-daily-workout")

    rendered = render_skill(content, GARMIN_CAPABILITIES)

    assert "{{tool:" not in rendered
    assert (
        "create_walk_run_workout / create_z2_walk_workout / upload_workout (strength)"
        in rendered
    )
    assert "schedule_workout / schedule_week" in rendered


def test_strava_calendar_path_resolves_create_event_degraded():
    content = read_skill("generate-daily-workout")

    rendered = render_skill(content, STRAVA_CALENDAR_CAPABILITIES)

    assert "{{tool:" not in rendered
    assert "Call `create-event`." in rendered
    assert "covered by create-event above — no separate call" in rendered

    # Garmin-only resolutions for these two placeholders must not appear.
    assert "create_walk_run_workout / create_z2_walk_workout / upload_workout (strength)" not in rendered
    assert "schedule_workout / schedule_week" not in rendered


def test_plan_note_with_google_calendar_workout_source_validates():
    plan_note = PlanNote(
        date="2026-06-13",
        sport="running",
        intent="Z2 aerobic base",
        rationale="Easy aerobic day after yesterday's strength session",
        goal_id="goal-5k-sub22",
        block_context="base-building",
        target_summary="45 min easy, keep it conversational",
        workout_ref="evt_8a91f2",
        workout_source="google_calendar",
    )

    assert plan_note.workout_source == "google_calendar"
    assert plan_note.workout_ref == "evt_8a91f2"


def test_plan_note_with_garmin_workout_source_validates():
    plan_note = PlanNote(
        date="2026-06-13",
        sport="running",
        intent="Z2 aerobic base",
        rationale="Easy aerobic day after yesterday's strength session",
        goal_id="goal-5k-sub22",
        block_context="base-building",
        target_summary="45 min easy run, HR < 150",
        workout_ref="wko_88213",
        workout_source="garmin",
    )

    assert plan_note.workout_source == "garmin"
    assert plan_note.workout_ref == "wko_88213"
