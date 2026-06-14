from coach.sources import garmin
from coach.sources.base import CAPABILITIES, ROLES
from coach.sources.registry import SOURCES


def test_garmin_registered_on_import():
    assert "garmin" in SOURCES
    assert SOURCES["garmin"] is garmin.SOURCE_SPEC


def test_garmin_roles_and_capabilities():
    spec = garmin.SOURCE_SPEC

    assert spec.capabilities <= CAPABILITIES
    assert spec.roles <= ROLES

    assert spec.roles == {"metrics", "workout_calendar"}
    assert spec.capabilities == {
        "readiness",
        "hrv",
        "sleep",
        "body_battery",
        "stress",
        "training_load",
        "vo2max",
        "training_effect",
        "structured_workouts",
    }


def test_garmin_env_enabled_tools_matches_enabled_tools_list():
    spec = garmin.SOURCE_SPEC

    enabled_tools_env = spec.env["GARMIN_ENABLED_TOOLS"].split(",")

    assert enabled_tools_env == spec.enabled_tools
    for tool in spec.enabled_tools:
        assert tool in spec.env["GARMIN_ENABLED_TOOLS"]
