"""Functional matrix row: setup-coach-personality (techspec section 13).

Step 3 of ``setup-coach-personality`` calls ``{{tool: fitness_assessment}}``:

- Garmin (Full): resolves to ``get_training_status``, ``get_training_readiness``,
  ``get_vo2max_trend``.
- Strava+Calendar (Degraded): resolves to ``get-athlete-stats``,
  ``get-activities``, ``get-segment-prs``.
"""

from __future__ import annotations

from coach.harness.base import render_skill
from tests.functional_helpers import (
    GARMIN_CAPABILITIES,
    STRAVA_CALENDAR_CAPABILITIES,
    read_skill,
)


def test_garmin_path_resolves_fitness_assessment():
    content = read_skill("setup-coach-personality")

    rendered = render_skill(content, GARMIN_CAPABILITIES)

    assert "{{tool:" not in rendered

    # The {{tool: fitness_assessment}} placeholder resolves to the Garmin
    # tool list (the SKILL.md body separately spells out both paths' tools
    # in prose for the agent, so we check the *resolved placeholder* directly).
    resolved = "get_training_status, get_training_readiness, get_vo2max_trend"
    assert resolved in rendered
    assert f"via `{resolved}`" in rendered


def test_strava_calendar_path_resolves_fitness_assessment_degraded():
    content = read_skill("setup-coach-personality")

    rendered = render_skill(content, STRAVA_CALENDAR_CAPABILITIES)

    assert "{{tool:" not in rendered

    # The {{tool: fitness_assessment}} placeholder resolves to the
    # Strava+Calendar tool list (Degraded path).
    resolved = "get-athlete-stats, get-activities, get-segment-prs"
    assert resolved in rendered
    assert f"via `{resolved}`" in rendered
