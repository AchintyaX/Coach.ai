import pytest

from coach.sources.base import SourceSpec
from coach.sources.registry import SOURCES, get, register, resolve_capabilities, resolve_roles


@pytest.fixture(autouse=True)
def _clean_registry():
    original = dict(SOURCES)
    SOURCES.clear()
    yield
    SOURCES.clear()
    SOURCES.update(original)


def _make_spec(
    name: str,
    roles: set[str],
    capabilities: set[str],
) -> SourceSpec:
    return SourceSpec(
        name=name,
        mcp_server_name=name,
        command="uvx",
        args=["--from", f"git+https://example.com/{name}", f"{name}-mcp"],
        env={},
        enabled_tools=[],
        roles=roles,
        capabilities=capabilities,
        auth_steps=[],
        status="scaffold",
    )


def test_register_and_get_roundtrip():
    spec = _make_spec("stub", roles={"metrics"}, capabilities={"activity_streams", "prs"})

    register(spec)

    assert get("stub") == spec


def test_get_missing_returns_none():
    assert get("does_not_exist") is None


def test_resolve_capabilities_union():
    spec_a = _make_spec("stub_a", roles={"metrics"}, capabilities={"activity_streams", "prs"})
    spec_b = _make_spec(
        "stub_b",
        roles={"workout_calendar"},
        capabilities={"prs", "free_text_workouts"},
    )

    result = resolve_capabilities([spec_a, spec_b])

    assert result == {"activity_streams", "prs", "free_text_workouts"}


def test_resolve_roles_union():
    spec_a = _make_spec("stub_a", roles={"metrics"}, capabilities={"activity_streams"})
    spec_b = _make_spec(
        "stub_b",
        roles={"workout_calendar", "metrics"},
        capabilities={"free_text_workouts"},
    )

    result = resolve_roles([spec_a, spec_b])

    assert result == {"metrics", "workout_calendar"}


def test_register_rejects_invalid_capability():
    spec = _make_spec("stub_bad", roles={"metrics"}, capabilities={"not_a_real_capability"})

    with pytest.raises(ValueError):
        register(spec)


def test_register_rejects_invalid_role():
    spec = _make_spec("stub_bad_role", roles={"not_a_real_role"}, capabilities={"prs"})

    with pytest.raises(ValueError):
        register(spec)
