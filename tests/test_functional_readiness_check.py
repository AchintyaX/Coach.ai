"""Functional matrix row: readiness-check (techspec section 13).

Two things are exercised:

1. ``{{tool: readiness_metrics}}`` rendering:
   - Garmin (Full): resolves to the 5-tool overnight-metrics list.
   - Strava+Calendar (Degraded): resolves to "not available on this path —
     skip this step entirely".

2. ``assemble.py`` output, built from the Garmin readiness fixtures
   (``training_readiness.json``, ``hrv.json``, ``sleep.json``) reshaped into
   the ``readiness`` dict ``assemble()`` expects:
   - Garmin capabilities -> ``"readiness"`` key present and populated.
   - Strava+Calendar capabilities -> ``"readiness"`` key absent (omitted, not
     null/zero), even when passed the *same* readiness dict.
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
# {{tool: readiness_metrics}} placeholder
# ---------------------------------------------------------------------------


def test_garmin_path_resolves_readiness_metrics():
    content = read_skill("readiness-check")

    rendered = render_skill(content, GARMIN_CAPABILITIES)

    assert "{{tool:" not in rendered
    allowed_tools_line = next(
        line for line in rendered.splitlines() if line.startswith("allowed-tools:")
    )
    for tool in (
        "get_training_readiness",
        "get_morning_training_readiness",
        "get_hrv_data",
        "get_sleep_data",
        "get_body_battery",
    ):
        assert tool in allowed_tools_line


def test_strava_calendar_path_readiness_metrics_unavailable():
    content = read_skill("readiness-check")

    rendered = render_skill(content, STRAVA_CALENDAR_CAPABILITIES)

    assert "{{tool:" not in rendered
    allowed_tools_line = next(
        line for line in rendered.splitlines() if line.startswith("allowed-tools:")
    )
    assert "not available on this path" in allowed_tools_line
    assert "skip this step entirely" in allowed_tools_line
    assert "get_training_readiness" not in allowed_tools_line


# ---------------------------------------------------------------------------
# assemble.py readiness section
# ---------------------------------------------------------------------------


def _readiness_dict_from_garmin_fixtures() -> dict:
    """Reshape the Garmin fixtures into the ``readiness`` dict assemble() expects."""
    training_readiness = load_fixture("garmin", "training_readiness.json")
    hrv = load_fixture("garmin", "hrv.json")
    sleep = load_fixture("garmin", "sleep.json")

    return {
        "training_readiness": training_readiness["score"],
        "hrv_status": hrv["hrvSummary"]["status"],
        "sleep_score": sleep["sleepScores"]["overall"]["value"],
    }


def test_garmin_path_assemble_includes_populated_readiness():
    readiness = _readiness_dict_from_garmin_fixtures()

    output = assemble(
        date="2026-06-13",
        goal=None,
        plan_note=None,
        actual_activity=None,
        recent_activities=[],
        readiness=readiness,
        capabilities=GARMIN_CAPABILITIES,
    )

    assert "readiness" in output
    assert output["readiness"] == {
        "training_readiness": 58,
        "hrv_status": "UNBALANCED",
        "sleep_score": 61,
    }


def test_strava_calendar_path_assemble_omits_readiness():
    # Same readiness dict as the Garmin test, but with Strava+Calendar
    # capabilities: "readiness" must be absent entirely (not null/empty).
    readiness = _readiness_dict_from_garmin_fixtures()

    output = assemble(
        date="2026-06-13",
        goal=None,
        plan_note=None,
        actual_activity=None,
        recent_activities=[],
        readiness=readiness,
        capabilities=STRAVA_CALENDAR_CAPABILITIES,
    )

    assert "readiness" not in output
    assert output.get("readiness", "sentinel") == "sentinel"
