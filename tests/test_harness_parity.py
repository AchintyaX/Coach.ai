"""Harness parity (techspec section 13).

A parametrized test that runs the *same resolved capability set* (both
Milestone-1 paths: Garmin, and Strava+Calendar) through ``ClaudeHarness`` and
``CodexHarness`` and asserts structural equivalence:

(a) the same set of skills get installed for a given capability set —
    ``.claude/skills/<name>/SKILL.md`` vs ``.codex/skills/<name>/SKILL.md``;
(b) their rendered bodies are identical — same ``{{tool: ...}}`` resolutions,
    installer output differs only in file location (CLAUDE.md vs AGENTS.md,
    .mcp.json vs config.toml, .claude/skills/ vs .codex/skills/, per
    section 5.1's file-target matrix);
(c) for a given ``SourceSpec``, ``register_mcp_server`` produces an MCP
    server entry with the same ``command``/``args``/``env`` semantics in both
    ``.mcp.json`` (``mcpServers.<name>``) and ``config.toml``
    (``[mcp_servers.<name>]``).
"""

from __future__ import annotations

import json

import pytest
import tomlkit

from coach.harness.claude import ClaudeHarness
from coach.harness.codex import CodexHarness
from coach.sources import garmin, google_calendar, strava
from tests.functional_helpers import (
    GARMIN_CAPABILITIES,
    STRAVA_CALENDAR_CAPABILITIES,
    SKILLS_DIR,
)

CAPABILITY_SETS = {
    "garmin": GARMIN_CAPABILITIES,
    "strava_calendar": STRAVA_CALENDAR_CAPABILITIES,
}


def _harnesses(tmp_path):
    claude_dir = tmp_path / "claude_project"
    codex_dir = tmp_path / "codex_project"
    codex_home = tmp_path / "codex_home"
    claude_dir.mkdir()
    codex_dir.mkdir()
    codex_home.mkdir()

    claude_harness = ClaudeHarness(claude_dir)
    codex_harness = CodexHarness(codex_dir, home=codex_home)
    return claude_harness, codex_harness


# ---------------------------------------------------------------------------
# (a) + (b): install_skills produces the same skill set and rendered bodies
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("capabilities_name", sorted(CAPABILITY_SETS))
def test_install_skills_same_set_and_rendered_bodies(tmp_path, capabilities_name):
    capabilities = CAPABILITY_SETS[capabilities_name]
    claude_harness, codex_harness = _harnesses(tmp_path)

    claude_written = claude_harness.install_skills(SKILLS_DIR, capabilities)
    codex_written = codex_harness.install_skills(SKILLS_DIR, capabilities)

    claude_by_name = {p.parent.name: p for p in claude_written}
    codex_by_name = {p.parent.name: p for p in codex_written}

    # (a) same set of skills installed
    assert set(claude_by_name) == set(codex_by_name)
    assert claude_by_name  # sanity: at least one skill installed

    for name in claude_by_name:
        claude_path = claude_by_name[name]
        codex_path = codex_by_name[name]

        # File targets differ per section 5.1's matrix.
        assert claude_path == claude_harness.project_dir / ".claude" / "skills" / name / "SKILL.md"
        assert codex_path == codex_harness.project_dir / ".codex" / "skills" / name / "SKILL.md"

        claude_content = claude_path.read_text(encoding="utf-8")
        codex_content = codex_path.read_text(encoding="utf-8")

        # (b) identical rendered bodies -> same {{tool: ...}} resolutions.
        assert claude_content == codex_content
        assert "{{tool:" not in claude_content
        assert "{{tool:" not in codex_content


# ---------------------------------------------------------------------------
# (c): register_mcp_server produces equivalent command/args/env in both
# .mcp.json (mcpServers.<name>) and config.toml ([mcp_servers.<name>])
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    "spec",
    [garmin.SOURCE_SPEC, strava.SOURCE_SPEC, google_calendar.SOURCE_SPEC],
    ids=lambda spec: spec.name,
)
def test_register_mcp_server_same_command_args_env(tmp_path, spec):
    claude_harness, codex_harness = _harnesses(tmp_path)

    claude_path = claude_harness.register_mcp_server(spec)
    codex_path = codex_harness.register_mcp_server(spec)

    assert claude_path == claude_harness.project_dir / ".mcp.json"
    assert codex_path == codex_harness.home / ".codex" / "config.toml"

    mcp_json = json.loads(claude_path.read_text(encoding="utf-8"))
    claude_entry = mcp_json["mcpServers"][spec.mcp_server_name]

    config_toml = tomlkit.parse(codex_path.read_text(encoding="utf-8"))
    codex_entry = config_toml["mcp_servers"][spec.mcp_server_name]

    # Same command/args/env semantics, different file formats/locations.
    assert claude_entry["command"] == codex_entry["command"] == spec.command
    assert list(claude_entry["args"]) == list(codex_entry["args"]) == spec.args

    if spec.env:
        assert dict(claude_entry["env"]) == dict(codex_entry["env"]) == spec.env
    else:
        assert "env" not in claude_entry
        assert "env" not in codex_entry


# ---------------------------------------------------------------------------
# Sanity: the two M1 capability sets route to the expected placeholder family
# ---------------------------------------------------------------------------


def test_capability_sets_route_to_expected_paths():
    assert "structured_workouts" in GARMIN_CAPABILITIES
    assert "free_text_workouts" not in GARMIN_CAPABILITIES

    assert "free_text_workouts" in STRAVA_CALENDAR_CAPABILITIES
    assert "structured_workouts" not in STRAVA_CALENDAR_CAPABILITIES
