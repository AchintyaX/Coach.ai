"""Functional matrix row: body-checkin (techspec section 13).

``body-checkin`` is capability-independent — the skill installs (Full) on
both paths — but ``{{tool: body_battery_optional}}`` resolves differently:

- Garmin: ``get_body_battery``.
- Strava+Calendar: "not available on this path — omit".

The matrix marks this row "Full on both paths", meaning the skill is usable
on both — not that the rendered text is identical. We assert each path's
render resolves to its correct placeholder text and that both renders are
non-empty/well-formed (no leftover ``{{tool: ...}}`` placeholders).
"""

from __future__ import annotations

from coach.harness.base import render_skill
from tests.functional_helpers import (
    GARMIN_CAPABILITIES,
    STRAVA_CALENDAR_CAPABILITIES,
    read_skill,
)


def test_garmin_path_resolves_body_battery_optional():
    content = read_skill("body-checkin")

    rendered = render_skill(content, GARMIN_CAPABILITIES)

    assert "{{tool:" not in rendered
    assert rendered.strip()  # non-empty / well-formed

    allowed_tools_line = next(
        line for line in rendered.splitlines() if line.startswith("allowed-tools:")
    )
    assert "get_body_battery" in allowed_tools_line
    assert "Call `get_body_battery` (Garmin only" in rendered


def test_strava_calendar_path_body_battery_optional_omitted():
    content = read_skill("body-checkin")

    rendered = render_skill(content, STRAVA_CALENDAR_CAPABILITIES)

    assert "{{tool:" not in rendered
    assert rendered.strip()  # non-empty / well-formed

    allowed_tools_line = next(
        line for line in rendered.splitlines() if line.startswith("allowed-tools:")
    )
    assert "not available on this path — omit" in allowed_tools_line
    assert "Call `not available on this path — omit` (Garmin only" in rendered


def test_body_checkin_installs_on_both_paths():
    """The skill itself is capability-independent (Full on both paths)."""
    content = read_skill("body-checkin")

    import yaml

    frontmatter = yaml.safe_load(content.split("---", 2)[1])
    assert frontmatter.get("capabilities") == []
