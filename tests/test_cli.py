import json
from pathlib import Path

import pytest

from coach import cli
from coach.harness.claude import COACH_END, COACH_START

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


# ---------------------------------------------------------------------------
# coach setup --source <name>
# ---------------------------------------------------------------------------


def test_setup_source_garmin_writes_config(tmp_path):
    cli.setup_source("garmin", project_dir=tmp_path)

    config = cli.load_config(tmp_path)
    assert "garmin" in config["sources"]

    config_path = tmp_path / ".coach" / "config.json"
    assert config_path.exists()
    on_disk = json.loads(config_path.read_text())
    assert "garmin" in on_disk["sources"]


def test_setup_source_garmin_is_idempotent(tmp_path):
    cli.setup_source("garmin", project_dir=tmp_path)
    cli.setup_source("garmin", project_dir=tmp_path)

    config = cli.load_config(tmp_path)
    assert list(config["sources"].keys()).count("garmin") == 1


def test_setup_source_unknown_raises(tmp_path):
    with pytest.raises(ValueError):
        cli.setup_source("bogus", project_dir=tmp_path)


def test_setup_source_google_calendar_stores_extra_params(tmp_path):
    cli.setup_source(
        "google_calendar",
        project_dir=tmp_path,
        credentials="./gcp-oauth.keys.json",
    )

    config = cli.load_config(tmp_path)
    assert config["sources"]["google_calendar"]["credentials"] == "./gcp-oauth.keys.json"


def test_setup_source_outlook_calendar_stores_tenant_and_client_id(tmp_path):
    cli.setup_source(
        "outlook_calendar",
        project_dir=tmp_path,
        tenant_id="tenant-123",
        client_id="client-456",
    )

    config = cli.load_config(tmp_path)
    extra = config["sources"]["outlook_calendar"]
    assert extra["tenant_id"] == "tenant-123"
    assert extra["client_id"] == "client-456"


# ---------------------------------------------------------------------------
# coach setup --schedule-time / --schedule
# ---------------------------------------------------------------------------


def _seed_support_tasks_json(support_dir: Path, tasks: list | None = None) -> Path:
    """Helper: create a minimal scheduled-tasks.json in a tmp Application Support tree."""
    p = support_dir / "claude-code-sessions" / "acct" / "sub" / "scheduled-tasks.json"
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(json.dumps({"scheduledTasks": tasks or [], "recordedSkips": {}}))
    return p


def test_setup_schedule_time_writes_all_artifacts(tmp_path):
    project_dir = tmp_path / "project"
    project_dir.mkdir()
    home = tmp_path / "home"
    support = tmp_path / "support"
    tasks_json = _seed_support_tasks_json(support)

    written = cli.setup_schedule(
        "7:00 AM", project_dir=project_dir, home=home,
        claude_support_dir=support, now_ms=123_000,
    )

    claude_path = home / ".claude" / "scheduled-tasks" / "coach-daily-loop" / "SKILL.md"
    codex_path = project_dir / ".codex" / "automations" / "daily-coach-loop.toml"
    cron_path = home / "Library" / "LaunchAgents" / "com.coachai.dailyloop.plist"

    # Return shape
    assert written["claude"].skill_md_path == claude_path
    assert written["codex_automation"] == codex_path
    assert written["cron_fallback"] == cron_path

    # Files exist
    assert claude_path.exists()
    assert codex_path.exists()
    assert cron_path.exists()

    # SKILL.md must use the real Desktop format — no schedule/mode
    skill_content = claude_path.read_text()
    assert "name: coach-daily-loop" in skill_content
    assert "schedule:" not in skill_content
    assert "mode:" not in skill_content

    # Codex TOML still carries the cron (unchanged)
    assert 'schedule = "0 7 * * *"' in codex_path.read_text()

    # scheduled-tasks.json must have the registered entry
    data = json.loads(tasks_json.read_text())
    entry = next(
        (e for e in data["scheduledTasks"] if e["id"] == "coach-daily-loop"), None
    )
    assert entry is not None
    assert entry["cronExpression"] == "0 7 * * *"
    assert entry["permissionMode"] == "auto"
    assert entry["createdAt"] == 123_000

    # Result flags
    assert written["claude"].registered is True
    assert written["claude"].action == "created"


def test_setup_schedule_interactive_uses_input(tmp_path, monkeypatch):
    project_dir = tmp_path / "project"
    project_dir.mkdir()
    home = tmp_path / "home"
    support = tmp_path / "support"
    _seed_support_tasks_json(support)

    monkeypatch.setattr("builtins.input", lambda prompt="": "7:00 AM")

    written = cli.setup_schedule_interactive(
        project_dir=project_dir, home=home, claude_support_dir=support,
    )

    assert written["claude"].skill_md_path.exists()
    assert written["codex_automation"].exists()
    assert written["cron_fallback"].exists()


def test_setup_schedule_invalid_time_raises(tmp_path):
    with pytest.raises(ValueError):
        cli.setup_schedule("not a time", project_dir=tmp_path, home=tmp_path / "home")


# ---------------------------------------------------------------------------
# coach install --harness claude
# ---------------------------------------------------------------------------


def test_install_claude_no_sources_configured_raises(tmp_path):
    with pytest.raises(ValueError):
        cli.install("claude", project_dir=tmp_path)


def test_install_claude_garmin(tmp_path):
    cli.setup_source("garmin", project_dir=tmp_path)

    results = cli.install("claude", project_dir=tmp_path)

    assert "claude" in results
    status = results["claude"]
    assert status["personality"] is True
    assert status["mcp"] is True
    assert status["skills"] is True
    assert status["settings"] is True

    # CLAUDE.md with coach:start/end block containing seed personality text
    claude_md = (tmp_path / "CLAUDE.md").read_text(encoding="utf-8")
    assert COACH_START in claude_md
    assert COACH_END in claude_md
    personality_text = cli.PERSONALITY_PATH.read_text(encoding="utf-8")
    # check a distinctive line from the seed personality is present
    first_line = personality_text.strip().splitlines()[0]
    assert first_line in claude_md

    # .mcp.json with mcpServers.garmin
    mcp_config = json.loads((tmp_path / ".mcp.json").read_text(encoding="utf-8"))
    assert "garmin" in mcp_config["mcpServers"]

    # .claude/skills/*/SKILL.md - 7 skills for Garmin capability set
    skills_dir = tmp_path / ".claude" / "skills"
    skill_files = sorted(skills_dir.glob("*/SKILL.md"))
    assert len(skill_files) == 7

    # placeholders resolved to Garmin tools (e.g. {{tool: readiness_metrics}})
    for skill_file in skill_files:
        content = skill_file.read_text(encoding="utf-8")
        assert "{{tool:" not in content

    # at least one skill should mention a garmin-specific tool name
    combined = "\n".join(f.read_text(encoding="utf-8") for f in skill_files)
    assert "get_training_readiness" in combined

    # .claude/settings.json with enableAllProjectMcpServers: true
    settings = json.loads((tmp_path / ".claude" / "settings.json").read_text(encoding="utf-8"))
    assert settings["enableAllProjectMcpServers"] is True


# ---------------------------------------------------------------------------
# coach install --harness codex
# ---------------------------------------------------------------------------


def test_install_codex_strava_and_google_calendar(tmp_path):
    project_dir = tmp_path / "project"
    project_dir.mkdir()
    home = tmp_path / "home"

    cli.setup_source("strava", project_dir=project_dir)
    cli.setup_source("google_calendar", project_dir=project_dir, credentials="./gcp-oauth.keys.json")

    results = cli.install("codex", project_dir=project_dir, home=home)

    assert "codex" in results
    status = results["codex"]
    assert status["personality"] is True
    assert status["mcp"] is True
    assert status["skills"] is True

    # AGENTS.md
    agents_md = (project_dir / "AGENTS.md").read_text(encoding="utf-8")
    assert COACH_START in agents_md
    assert COACH_END in agents_md

    # <home>/.codex/config.toml with [mcp_servers.strava] and [mcp_servers.google_calendar]
    import tomlkit

    config_toml = home / ".codex" / "config.toml"
    assert config_toml.exists()
    config = tomlkit.parse(config_toml.read_text(encoding="utf-8"))
    assert "strava" in config["mcp_servers"]
    assert "google_calendar" in config["mcp_servers"]

    # .codex/skills/*/SKILL.md rendered for the strava+calendar capability set
    skills_dir = project_dir / ".codex" / "skills"
    skill_files = sorted(skills_dir.glob("*/SKILL.md"))
    assert len(skill_files) > 0

    for skill_file in skill_files:
        content = skill_file.read_text(encoding="utf-8")
        assert "{{tool:" not in content


# ---------------------------------------------------------------------------
# coach install --harness all
# ---------------------------------------------------------------------------


def test_install_all_runs_both_harnesses(tmp_path):
    project_dir = tmp_path / "project"
    project_dir.mkdir()
    home = tmp_path / "home"

    cli.setup_source("garmin", project_dir=project_dir)

    results = cli.install("all", project_dir=project_dir, home=home)

    assert "claude" in results
    assert "codex" in results
    assert (project_dir / "CLAUDE.md").exists()
    assert (project_dir / "AGENTS.md").exists()


# ---------------------------------------------------------------------------
# CLI argparse entrypoint - error cases
# ---------------------------------------------------------------------------


def test_main_setup_with_no_args_returns_nonzero(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    code = cli.main(["setup"])
    assert code != 0


def test_main_install_no_sources_configured(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    code = cli.main(["install", "--harness", "claude"])
    assert code != 0


def test_main_setup_source_unknown(tmp_path, monkeypatch, capsys):
    monkeypatch.chdir(tmp_path)
    code = cli.main(["setup", "--source", "bogus"])
    assert code != 0


def test_main_setup_source_garmin(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    code = cli.main(["setup", "--source", "garmin"])
    assert code == 0

    config = cli.load_config(tmp_path)
    assert "garmin" in config["sources"]


def test_main_setup_schedule_time(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    # Prevent the CLI from touching real ~/Library/Application Support or ~/.claude
    import coach.scheduling as _sched
    monkeypatch.setattr(
        _sched, "locate_scheduled_tasks_json",
        lambda claude_support_dir=None: _sched.LocateResult(path=None, all_paths=[]),
    )
    monkeypatch.setattr(
        _sched, "write_claude_skill_md",
        lambda project_dir, **kw: tmp_path / "SKILL.md",
    )
    code = cli.main(["setup", "--schedule-time", "7:00 AM"])
    assert code == 0


def test_main_install_claude_after_setup(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    cli.main(["setup", "--source", "garmin"])
    code = cli.main(["install", "--harness", "claude"])
    assert code == 0
    assert (tmp_path / "CLAUDE.md").exists()
