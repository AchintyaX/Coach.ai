import json
from pathlib import Path

import pytest

from coach.harness.claude import ClaudeHarness
from coach.sources.base import SourceSpec

REPO_ROOT = Path(__file__).resolve().parent.parent
SKILLS_DIR = REPO_ROOT / "skills"

GARMIN_CAPABILITIES = {
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

STRAVA_CALENDAR_CAPABILITIES = {
    "activity_streams",
    "prs",
    "training_load",
    "free_text_workouts",
}


def _garmin_spec() -> SourceSpec:
    return SourceSpec(
        name="garmin",
        mcp_server_name="garmin",
        command="uvx",
        args=[
            "--python",
            "3.12",
            "--from",
            "git+https://github.com/Taxuspt/garmin_mcp",
            "garmin-mcp",
        ],
        env={"GARMIN_ENABLED_TOOLS": "get_training_readiness,get_activities"},
        enabled_tools=["get_training_readiness", "get_activities"],
        roles={"metrics", "workout_calendar"},
        capabilities=GARMIN_CAPABILITIES,
        auth_steps=[
            "uvx --python 3.12 --from git+https://github.com/Taxuspt/garmin_mcp garmin-mcp-auth",
        ],
        status="functional",
    )


def _strava_spec() -> SourceSpec:
    return SourceSpec(
        name="strava",
        mcp_server_name="strava",
        command="uv",
        args=["run", "python", "strava/strava_server.py"],
        env={"STRAVA_ENABLED_TOOLS": "get-activities,get-activity-streams"},
        enabled_tools=["get-activities", "get-activity-streams"],
        roles={"metrics"},
        capabilities={"activity_streams", "prs", "training_load"},
        auth_steps=["uv run python scripts/setup_auth.py"],
        status="functional",
    )


def _google_calendar_spec() -> SourceSpec:
    return SourceSpec(
        name="google_calendar",
        mcp_server_name="google_calendar",
        command="npx",
        args=["-y", "@nspady/google-calendar-mcp"],
        env={"GOOGLE_OAUTH_CREDENTIALS": "./gcp-oauth.keys.json"},
        enabled_tools=["list-events", "create-event", "update-event", "get-event"],
        roles={"workout_calendar"},
        capabilities={"free_text_workouts"},
        auth_steps=["coach setup --source google_calendar --credentials ./gcp-oauth.keys.json"],
        status="functional",
    )


# ---------------------------------------------------------------------------
# install_personality
# ---------------------------------------------------------------------------


def test_install_personality_creates_claude_md(tmp_path):
    harness = ClaudeHarness(tmp_path)

    path = harness.install_personality("# Coach Personality\n\nBe direct.")

    assert path == tmp_path / "CLAUDE.md"
    content = path.read_text(encoding="utf-8")
    assert "<!-- coach:start -->" in content
    assert "<!-- coach:end -->" in content
    assert "Be direct." in content


def test_install_personality_idempotent_replace(tmp_path):
    harness = ClaudeHarness(tmp_path)

    claude_md = tmp_path / "CLAUDE.md"
    claude_md.write_text(
        "# My Project Notes\n\nSome unrelated content before.\n\n"
        "<!-- coach:start -->\nOld personality text\n<!-- coach:end -->\n\n"
        "More unrelated content after.\n",
        encoding="utf-8",
    )

    harness.install_personality("New personality text")

    content = claude_md.read_text(encoding="utf-8")
    assert "Old personality text" not in content
    assert "New personality text" in content
    assert "Some unrelated content before." in content
    assert "More unrelated content after." in content
    # markers still present exactly once each
    assert content.count("<!-- coach:start -->") == 1
    assert content.count("<!-- coach:end -->") == 1


def test_install_personality_appends_when_no_markers(tmp_path):
    harness = ClaudeHarness(tmp_path)

    claude_md = tmp_path / "CLAUDE.md"
    claude_md.write_text("# Existing project instructions\n\nDo not break things.\n", encoding="utf-8")

    harness.install_personality("Coach personality body")

    content = claude_md.read_text(encoding="utf-8")
    assert "# Existing project instructions" in content
    assert "Do not break things." in content
    assert "<!-- coach:start -->" in content
    assert "Coach personality body" in content
    assert "<!-- coach:end -->" in content
    # the marked block comes after the existing content
    assert content.index("Do not break things.") < content.index("<!-- coach:start -->")


# ---------------------------------------------------------------------------
# register_mcp_server
# ---------------------------------------------------------------------------


def test_register_mcp_server_writes_mcp_json(tmp_path):
    harness = ClaudeHarness(tmp_path)
    spec = _garmin_spec()

    path = harness.register_mcp_server(spec)

    assert path == tmp_path / ".mcp.json"
    config = json.loads(path.read_text(encoding="utf-8"))

    entry = config["mcpServers"]["garmin"]
    assert entry["command"] == spec.command
    assert entry["args"] == spec.args
    assert entry["env"] == spec.env


def test_register_mcp_server_preserves_existing_entries(tmp_path):
    harness = ClaudeHarness(tmp_path)

    harness.register_mcp_server(_strava_spec())
    harness.register_mcp_server(_google_calendar_spec())

    config = json.loads((tmp_path / ".mcp.json").read_text(encoding="utf-8"))
    servers = config["mcpServers"]

    assert set(servers.keys()) == {"strava", "google_calendar"}
    assert servers["strava"]["command"] == "uv"
    assert servers["strava"]["args"] == ["run", "python", "strava/strava_server.py"]
    assert servers["google_calendar"]["command"] == "npx"
    assert servers["google_calendar"]["env"] == {"GOOGLE_OAUTH_CREDENTIALS": "./gcp-oauth.keys.json"}


# ---------------------------------------------------------------------------
# install_skills
# ---------------------------------------------------------------------------


def test_install_skills_garmin_path(tmp_path):
    harness = ClaudeHarness(tmp_path)

    written = harness.install_skills(SKILLS_DIR, GARMIN_CAPABILITIES)

    skill_names = {p.parent.name for p in written}
    expected_names = {
        "adjust-workout",
        "body-checkin",
        "evaluate-training",
        "generate-daily-workout",
        "readiness-check",
        "research-goal-plan",
        "setup-coach-personality",
    }
    assert skill_names == expected_names

    for p in written:
        assert p == tmp_path / ".claude" / "skills" / p.parent.name / "SKILL.md"
        assert p.exists()
        content = p.read_text(encoding="utf-8")
        assert "{{tool:" not in content

    readiness_content = (tmp_path / ".claude" / "skills" / "readiness-check" / "SKILL.md").read_text(
        encoding="utf-8"
    )
    assert "get_training_readiness" in readiness_content


def test_install_skills_strava_calendar_path(tmp_path):
    harness = ClaudeHarness(tmp_path)

    written = harness.install_skills(SKILLS_DIR, STRAVA_CALENDAR_CAPABILITIES)

    skill_names = {p.parent.name for p in written}
    expected_names = {
        "adjust-workout",
        "body-checkin",
        "evaluate-training",
        "generate-daily-workout",
        "readiness-check",
        "research-goal-plan",
        "setup-coach-personality",
    }
    assert skill_names == expected_names

    for p in written:
        content = p.read_text(encoding="utf-8")
        assert "{{tool:" not in content

    readiness_content = (tmp_path / ".claude" / "skills" / "readiness-check" / "SKILL.md").read_text(
        encoding="utf-8"
    )
    allowed_tools_line = next(
        line for line in readiness_content.splitlines() if line.startswith("allowed-tools:")
    )
    assert "get_training_readiness" not in allowed_tools_line
    assert "not available on this path" in allowed_tools_line or "skip this step" in allowed_tools_line


# ---------------------------------------------------------------------------
# verify
# ---------------------------------------------------------------------------


def test_verify_all_true_after_full_install(tmp_path):
    harness = ClaudeHarness(tmp_path)

    harness.install_personality("Be a great coach.")
    harness.register_mcp_server(_garmin_spec())
    harness.install_skills(SKILLS_DIR, GARMIN_CAPABILITIES)

    status = harness.verify()

    assert status == {
        "personality": True,
        "mcp": True,
        "skills": True,
        "settings": True,
    }

    settings_path = tmp_path / ".claude" / "settings.json"
    assert settings_path.exists()
    settings = json.loads(settings_path.read_text(encoding="utf-8"))

    assert settings["enableAllProjectMcpServers"] is True
    allow = settings["permissions"]["allow"]
    for expected in ["Read(./data/**)", "Write(./data/**)", "WebSearch", "WebFetch", "Bash"]:
        assert expected in allow


def test_verify_merges_existing_settings(tmp_path):
    harness = ClaudeHarness(tmp_path)

    claude_dir = tmp_path / ".claude"
    claude_dir.mkdir(parents=True)
    (claude_dir / "settings.json").write_text(
        json.dumps(
            {
                "someOtherKey": "preserved",
                "permissions": {"allow": ["CustomTool"], "deny": ["DangerousTool"]},
            }
        ),
        encoding="utf-8",
    )

    harness.install_personality("Personality text")
    harness.register_mcp_server(_garmin_spec())
    harness.install_skills(SKILLS_DIR, GARMIN_CAPABILITIES)

    harness.verify()

    settings = json.loads((claude_dir / "settings.json").read_text(encoding="utf-8"))
    assert settings["someOtherKey"] == "preserved"
    assert settings["enableAllProjectMcpServers"] is True
    assert "CustomTool" in settings["permissions"]["allow"]
    assert settings["permissions"]["deny"] == ["DangerousTool"]
    for expected in ["Read(./data/**)", "Write(./data/**)", "WebSearch", "WebFetch", "Bash"]:
        assert expected in settings["permissions"]["allow"]


def test_verify_false_when_nothing_installed(tmp_path):
    harness = ClaudeHarness(tmp_path)

    status = harness.verify()

    assert status["personality"] is False
    assert status["mcp"] is False
    assert status["skills"] is False
    # settings.json is written regardless, with the flag set
    assert status["settings"] is True


# ---------------------------------------------------------------------------
# setup_source
# ---------------------------------------------------------------------------


def test_setup_source_registers_mcp_server(tmp_path, capsys):
    harness = ClaudeHarness(tmp_path)
    spec = _garmin_spec()

    harness.setup_source(spec)

    captured = capsys.readouterr()
    for step in spec.auth_steps:
        assert step in captured.out

    config = json.loads((tmp_path / ".mcp.json").read_text(encoding="utf-8"))
    assert "garmin" in config["mcpServers"]
