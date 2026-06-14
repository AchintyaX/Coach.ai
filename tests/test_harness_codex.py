from pathlib import Path

import tomlkit

from coach.harness.codex import CodexHarness
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


def _harness(tmp_path: Path) -> CodexHarness:
    project_dir = tmp_path / "project"
    project_dir.mkdir(parents=True, exist_ok=True)
    home = tmp_path / "home"
    home.mkdir(parents=True, exist_ok=True)
    return CodexHarness(project_dir, home=home)


# ---------------------------------------------------------------------------
# install_personality
# ---------------------------------------------------------------------------


def test_install_personality_creates_agents_md(tmp_path):
    harness = _harness(tmp_path)

    path = harness.install_personality("# Coach Personality\n\nBe direct.")

    assert path == harness.project_dir / "AGENTS.md"
    content = path.read_text(encoding="utf-8")
    assert "<!-- coach:start -->" in content
    assert "<!-- coach:end -->" in content
    assert "Be direct." in content


def test_install_personality_idempotent_replace(tmp_path):
    harness = _harness(tmp_path)

    agents_md = harness.project_dir / "AGENTS.md"
    agents_md.write_text(
        "# My Project Notes\n\nSome unrelated content before.\n\n"
        "<!-- coach:start -->\nOld personality text\n<!-- coach:end -->\n\n"
        "More unrelated content after.\n",
        encoding="utf-8",
    )

    harness.install_personality("New personality text")

    content = agents_md.read_text(encoding="utf-8")
    assert "Old personality text" not in content
    assert "New personality text" in content
    assert "Some unrelated content before." in content
    assert "More unrelated content after." in content
    assert content.count("<!-- coach:start -->") == 1
    assert content.count("<!-- coach:end -->") == 1


def test_install_personality_appends_when_no_markers(tmp_path):
    harness = _harness(tmp_path)

    agents_md = harness.project_dir / "AGENTS.md"
    agents_md.write_text("# Existing project instructions\n\nDo not break things.\n", encoding="utf-8")

    harness.install_personality("Coach personality body")

    content = agents_md.read_text(encoding="utf-8")
    assert "# Existing project instructions" in content
    assert "Do not break things." in content
    assert "<!-- coach:start -->" in content
    assert "Coach personality body" in content
    assert "<!-- coach:end -->" in content
    assert content.index("Do not break things.") < content.index("<!-- coach:start -->")


# ---------------------------------------------------------------------------
# register_mcp_server
# ---------------------------------------------------------------------------


def test_register_mcp_server_writes_config_toml(tmp_path):
    harness = _harness(tmp_path)
    spec = _garmin_spec()

    path = harness.register_mcp_server(spec)

    assert path == harness.home / ".codex" / "config.toml"
    config = tomlkit.parse(path.read_text(encoding="utf-8"))

    entry = config["mcp_servers"]["garmin"]
    assert entry["command"] == spec.command
    assert list(entry["args"]) == spec.args
    assert dict(entry["env"]) == spec.env


def test_register_mcp_server_preserves_existing_entries(tmp_path):
    harness = _harness(tmp_path)

    harness.register_mcp_server(_strava_spec())
    harness.register_mcp_server(_google_calendar_spec())

    config = tomlkit.parse(harness.codex_config_path.read_text(encoding="utf-8"))
    servers = config["mcp_servers"]

    assert set(servers.keys()) == {"strava", "google_calendar"}
    assert servers["strava"]["command"] == "uv"
    assert list(servers["strava"]["args"]) == ["run", "python", "strava/strava_server.py"]
    assert servers["google_calendar"]["command"] == "npx"
    assert dict(servers["google_calendar"]["env"]) == {"GOOGLE_OAUTH_CREDENTIALS": "./gcp-oauth.keys.json"}


def test_register_mcp_server_preserves_unrelated_tables(tmp_path):
    harness = _harness(tmp_path)

    harness.codex_config_path.parent.mkdir(parents=True, exist_ok=True)
    harness.codex_config_path.write_text(
        '[tools]\nweb_search = true\n',
        encoding="utf-8",
    )

    harness.register_mcp_server(_garmin_spec())

    config = tomlkit.parse(harness.codex_config_path.read_text(encoding="utf-8"))
    assert config["tools"]["web_search"] is True
    assert "garmin" in config["mcp_servers"]


# ---------------------------------------------------------------------------
# install_skills
# ---------------------------------------------------------------------------


EXPECTED_SKILL_NAMES = {
    "adjust-workout",
    "body-checkin",
    "evaluate-training",
    "generate-daily-workout",
    "readiness-check",
    "research-goal-plan",
    "setup-coach-personality",
}


def test_install_skills_garmin_path(tmp_path):
    harness = _harness(tmp_path)

    written = harness.install_skills(SKILLS_DIR, GARMIN_CAPABILITIES)

    skill_names = {p.parent.name for p in written}
    assert skill_names == EXPECTED_SKILL_NAMES

    for p in written:
        assert p == harness.project_dir / ".codex" / "skills" / p.parent.name / "SKILL.md"
        assert p.exists()
        content = p.read_text(encoding="utf-8")
        assert "{{tool:" not in content

    readiness_content = (
        harness.project_dir / ".codex" / "skills" / "readiness-check" / "SKILL.md"
    ).read_text(encoding="utf-8")
    assert "get_training_readiness" in readiness_content

    config = tomlkit.parse(harness.codex_config_path.read_text(encoding="utf-8"))
    skills_config = config["skills"]["config"]
    assert len(skills_config) == 7
    for entry in skills_config.values():
        assert entry["enabled"] is True
        assert (harness.project_dir / entry["path"]).exists()


def test_install_skills_strava_calendar_path(tmp_path):
    harness = _harness(tmp_path)

    written = harness.install_skills(SKILLS_DIR, STRAVA_CALENDAR_CAPABILITIES)

    skill_names = {p.parent.name for p in written}
    assert skill_names == EXPECTED_SKILL_NAMES

    for p in written:
        content = p.read_text(encoding="utf-8")
        assert "{{tool:" not in content

    readiness_content = (
        harness.project_dir / ".codex" / "skills" / "readiness-check" / "SKILL.md"
    ).read_text(encoding="utf-8")
    allowed_tools_line = next(
        line for line in readiness_content.splitlines() if line.startswith("allowed-tools:")
    )
    assert "get_training_readiness" not in allowed_tools_line
    assert "not available on this path" in allowed_tools_line or "skip this step" in allowed_tools_line


def test_install_skills_idempotent_no_duplicate_entries(tmp_path):
    harness = _harness(tmp_path)

    harness.install_skills(SKILLS_DIR, GARMIN_CAPABILITIES)
    harness.install_skills(SKILLS_DIR, GARMIN_CAPABILITIES)

    config = tomlkit.parse(harness.codex_config_path.read_text(encoding="utf-8"))
    skills_config = config["skills"]["config"]
    assert len(skills_config) == 7

    for entry in skills_config.values():
        assert entry["enabled"] is True


# ---------------------------------------------------------------------------
# verify
# ---------------------------------------------------------------------------


def test_verify_all_true_after_full_install(tmp_path):
    harness = _harness(tmp_path)

    harness.install_personality("Be a great coach.")
    harness.register_mcp_server(_garmin_spec())
    harness.install_skills(SKILLS_DIR, GARMIN_CAPABILITIES)

    status = harness.verify()

    assert status == {
        "personality": True,
        "mcp": True,
        "skills": True,
        "tools": True,
    }

    config = tomlkit.parse(harness.codex_config_path.read_text(encoding="utf-8"))
    assert config["tools"]["web_search"] is True


def test_verify_false_when_nothing_installed(tmp_path):
    harness = _harness(tmp_path)

    status = harness.verify()

    assert status["personality"] is False
    assert status["mcp"] is False
    assert status["skills"] is False
    # config.toml is written regardless, with the flag set
    assert status["tools"] is True


def test_verify_preserves_existing_tools_table(tmp_path):
    harness = _harness(tmp_path)

    harness.codex_config_path.parent.mkdir(parents=True, exist_ok=True)
    harness.codex_config_path.write_text(
        '[tools]\nweb_search = true\nsome_other_tool = "kept"\n',
        encoding="utf-8",
    )

    harness.verify()

    config = tomlkit.parse(harness.codex_config_path.read_text(encoding="utf-8"))
    assert config["tools"]["web_search"] is True
    assert config["tools"]["some_other_tool"] == "kept"


# ---------------------------------------------------------------------------
# setup_source
# ---------------------------------------------------------------------------


def test_setup_source_registers_mcp_server(tmp_path, capsys):
    harness = _harness(tmp_path)
    spec = _garmin_spec()

    harness.setup_source(spec)

    captured = capsys.readouterr()
    for step in spec.auth_steps:
        assert step in captured.out

    config = tomlkit.parse(harness.codex_config_path.read_text(encoding="utf-8"))
    assert "garmin" in config["mcp_servers"]


# Harness parity (Claude vs Codex, both capability sets) lives in
# tests/test_harness_parity.py.
