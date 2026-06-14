"""Functional matrix row: research-goal-plan (techspec section 13).

``research-goal-plan`` is capability-independent and contains no
``{{tool: ...}}`` placeholders at all (it only uses WebSearch/WebFetch/Bash).
Per the section-13 matrix, the rendered SKILL.md must be byte-identical on
both the Garmin path and the Strava+Calendar path.
"""

from __future__ import annotations

from coach.harness.base import render_skill
from tests.functional_helpers import (
    GARMIN_CAPABILITIES,
    STRAVA_CALENDAR_CAPABILITIES,
    read_skill,
)


def test_research_goal_plan_has_no_tool_placeholders():
    content = read_skill("research-goal-plan")
    assert "{{tool:" not in content


def test_research_goal_plan_renders_identically_on_both_paths():
    content = read_skill("research-goal-plan")

    garmin_rendered = render_skill(content, GARMIN_CAPABILITIES)
    strava_rendered = render_skill(content, STRAVA_CALENDAR_CAPABILITIES)

    # No placeholders to resolve, so rendering is a no-op either way.
    assert garmin_rendered == content
    assert strava_rendered == content
    assert garmin_rendered == strava_rendered
