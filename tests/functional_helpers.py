"""Shared helpers for Layer-2 functional tests (techspec section 13).

Provides:
- Paths to ``tests/fixtures/**`` and ``skills/**``
- A small JSON-fixture loader
- The two Milestone-1 capability sets (Garmin, Strava+Calendar), derived the
  same way the rest of the codebase derives them (via
  ``coach.sources.registry.resolve_capabilities``), so these tests stay in
  sync with ``coach/sources/*.py`` if those ever change.
"""

from __future__ import annotations

import json
from pathlib import Path

from coach.sources import garmin, google_calendar, strava
from coach.sources.registry import resolve_capabilities

REPO_ROOT = Path(__file__).resolve().parent.parent
FIXTURES_DIR = Path(__file__).resolve().parent / "fixtures"
SKILLS_DIR = REPO_ROOT / "skills"

# Garmin path: Garmin alone supplies every capability used by the skills.
GARMIN_CAPABILITIES = resolve_capabilities([garmin.SOURCE_SPEC])

# Strava + (Google) Calendar path: Strava for metrics, Google Calendar for
# the workout-calendar role.
STRAVA_CALENDAR_CAPABILITIES = resolve_capabilities(
    [strava.SOURCE_SPEC, google_calendar.SOURCE_SPEC]
)


def load_fixture(*parts: str) -> dict:
    """Load and parse a JSON fixture from ``tests/fixtures/<parts...>``."""
    path = FIXTURES_DIR.joinpath(*parts)
    return json.loads(path.read_text(encoding="utf-8"))


def read_skill(name: str) -> str:
    """Read the raw ``SKILL.md`` content for skill ``name``."""
    return (SKILLS_DIR / name / "SKILL.md").read_text(encoding="utf-8")
