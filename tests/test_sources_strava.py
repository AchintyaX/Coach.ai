from coach.sources import strava
from coach.sources.base import CAPABILITIES, ROLES
from coach.sources.registry import SOURCES


def test_strava_registered_on_import():
    assert "strava" in SOURCES
    assert SOURCES["strava"] is strava.SOURCE_SPEC


def test_strava_roles_and_capabilities():
    spec = strava.SOURCE_SPEC

    assert spec.capabilities <= CAPABILITIES
    assert spec.roles <= ROLES

    # Read-only by design: never carries workout_calendar.
    assert spec.roles == {"metrics"}
    assert spec.capabilities == {"activity_streams", "prs", "training_load"}


def test_strava_env_enabled_tools_matches_enabled_tools_list():
    spec = strava.SOURCE_SPEC

    enabled_tools_env = spec.env["STRAVA_ENABLED_TOOLS"].split(",")

    assert enabled_tools_env == spec.enabled_tools
    for tool in spec.enabled_tools:
        assert tool in spec.env["STRAVA_ENABLED_TOOLS"]
