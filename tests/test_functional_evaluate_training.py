"""Functional matrix row: evaluate-training (techspec section 13).

- ``{{tool: activity_detail}}`` / ``{{tool: recent_load_context}}`` rendering:
  - Garmin: ``get_activity`` / ``get_activities, get_training_load_trend``.
  - Strava+Calendar (Degraded): ``get-activity-streams`` / ``get-activities``.

- ``assemble.py`` on the recorded activity fixtures:
  - Garmin (+ Garmin capabilities) -> ``actual`` includes ``training_effect``
    and/or ``execution_score``.
  - Strava (+ Strava+Calendar capabilities) -> ``actual`` has no
    ``training_effect``/``execution_score``, has ``avg_pace_min_km`` (and HR
    data) instead.
"""

from __future__ import annotations

from coach.analysis.assemble import assemble
from coach.harness.base import render_skill
from tests.functional_helpers import (
    GARMIN_CAPABILITIES,
    STRAVA_CALENDAR_CAPABILITIES,
    load_fixture,
    read_skill,
)


# ---------------------------------------------------------------------------
# {{tool: ...}} placeholder rendering
# ---------------------------------------------------------------------------


def test_garmin_path_resolves_activity_detail_and_recent_load_context():
    content = read_skill("evaluate-training")

    rendered = render_skill(content, GARMIN_CAPABILITIES)

    assert "{{tool:" not in rendered
    allowed_tools_line = next(
        line for line in rendered.splitlines() if line.startswith("allowed-tools:")
    )
    assert "get_activity" in allowed_tools_line
    assert "get_activities, get_training_load_trend" in allowed_tools_line


def test_strava_calendar_path_resolves_activity_detail_and_recent_load_context():
    content = read_skill("evaluate-training")

    rendered = render_skill(content, STRAVA_CALENDAR_CAPABILITIES)

    assert "{{tool:" not in rendered
    allowed_tools_line = next(
        line for line in rendered.splitlines() if line.startswith("allowed-tools:")
    )
    assert "get-activity-streams" in allowed_tools_line
    assert "get-activities" in allowed_tools_line
    assert "get_activity" not in allowed_tools_line


# ---------------------------------------------------------------------------
# assemble.py on recorded activity fixtures
# ---------------------------------------------------------------------------


def test_garmin_path_assemble_includes_training_effect():
    activities = load_fixture("garmin", "activities.json")["activities"]
    actual_activity = activities[0]
    recent = activities[1:]

    output = assemble(
        date="2026-06-13",
        goal=None,
        plan_note=None,
        actual_activity=actual_activity,
        recent_activities=recent,
        readiness=None,
        capabilities=GARMIN_CAPABILITIES,
    )

    actual = output["actual"]
    assert actual["activity_id"] == "19283746"
    assert "training_effect" in actual or "execution_score" in actual
    assert actual["training_effect"] == {"aerobic": 2.8, "anaerobic": 0.4}
    assert actual["execution_score"] == "completed"
    assert "avg_pace_min_km" not in actual


def test_strava_path_assemble_excludes_training_effect():
    activities = load_fixture("strava", "activities.json")["activities"]
    actual_activity = activities[0]
    recent = activities[1:]

    output = assemble(
        date="2026-06-13",
        goal=None,
        plan_note=None,
        actual_activity=actual_activity,
        recent_activities=recent,
        readiness=None,
        capabilities=STRAVA_CALENDAR_CAPABILITIES,
    )

    actual = output["actual"]
    assert actual["activity_id"] == 19283746
    assert "training_effect" not in actual
    assert "execution_score" not in actual
    # avg_pace_min_km derived from moving_time/distance, plus HR data present.
    assert "avg_pace_min_km" in actual
    assert actual["avg_hr"] == 154.0
