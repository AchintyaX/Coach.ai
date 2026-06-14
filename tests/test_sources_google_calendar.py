from coach.sources import google_calendar
from coach.sources.base import CAPABILITIES, ROLES
from coach.sources.registry import SOURCES


def test_google_calendar_registered_on_import():
    assert "google_calendar" in SOURCES
    assert SOURCES["google_calendar"] is google_calendar.SOURCE_SPEC


def test_google_calendar_roles_and_capabilities():
    spec = google_calendar.SOURCE_SPEC

    assert spec.capabilities <= CAPABILITIES
    assert spec.roles <= ROLES

    assert spec.roles == {"workout_calendar"}
    assert spec.capabilities == {"free_text_workouts"}


def test_google_calendar_env_matches_mcp_config():
    spec = google_calendar.SOURCE_SPEC

    assert spec.env == {"GOOGLE_OAUTH_CREDENTIALS": "./gcp-oauth.keys.json"}
