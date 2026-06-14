from coach.sources import outlook_calendar
from coach.sources.base import CAPABILITIES, ROLES
from coach.sources.registry import SOURCES


def test_outlook_calendar_registered_on_import():
    assert "outlook_calendar" in SOURCES
    assert SOURCES["outlook_calendar"] is outlook_calendar.SOURCE_SPEC


def test_outlook_calendar_roles_and_capabilities():
    spec = outlook_calendar.SOURCE_SPEC

    assert spec.capabilities <= CAPABILITIES
    assert spec.roles <= ROLES

    assert spec.roles == {"workout_calendar"}
    assert spec.capabilities == {"free_text_workouts"}


def test_outlook_calendar_env_has_ms365_credentials():
    spec = outlook_calendar.SOURCE_SPEC

    assert "MS365_TENANT_ID" in spec.env
    assert "MS365_CLIENT_ID" in spec.env
