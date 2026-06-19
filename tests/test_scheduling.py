from __future__ import annotations

import json
import os
from datetime import time
from pathlib import Path

import pytest

from coach.scheduling import (
    TIME_FORMATS,
    ClaudeScheduleResult,
    LocateResult,
    ScheduleFileError,
    locate_scheduled_tasks_json,
    parse_time_of_day,
    read_garmin_approved_permissions,
    to_cron,
    upsert_scheduled_task,
    write_claude_scheduled_task,
    write_claude_skill_md,
    write_codex_automation,
    write_cron_fallback,
)


# ---------------------------------------------------------------------------
# parse_time_of_day / to_cron  (unchanged)
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    "raw",
    ["7:00 AM", "7 AM", "07:00", "7 am"],
)
def test_parse_time_of_day_valid_formats(raw):
    assert parse_time_of_day(raw) == time(7, 0)


def test_parse_time_of_day_covers_all_time_formats():
    assert len(TIME_FORMATS) == 3


def test_parse_time_of_day_invalid_raises_helpful_error():
    with pytest.raises(ValueError) as exc_info:
        parse_time_of_day("not a time")
    message = str(exc_info.value)
    for fmt in TIME_FORMATS:
        assert fmt in message


def test_to_cron():
    assert to_cron(time(7, 0)) == "0 7 * * *"


# ---------------------------------------------------------------------------
# write_claude_skill_md
# ---------------------------------------------------------------------------


def test_write_claude_skill_md(tmp_path):
    project_dir = tmp_path / "project"
    home = tmp_path / "home"
    project_dir.mkdir()

    path = write_claude_skill_md(project_dir, home=home)

    expected_path = home / ".claude" / "scheduled-tasks" / "coach-daily-loop" / "SKILL.md"
    assert path == expected_path
    assert path.exists()

    content = path.read_text()
    # Must have name and description
    assert "name: coach-daily-loop" in content
    assert "description: Daily readiness check and workout generation for Coach AI" in content
    # Must NOT have the old ignored fields
    assert "schedule:" not in content
    assert "mode:" not in content
    # Body must reference both skills and the project dir
    assert "readiness-check" in content
    assert "generate-daily-workout" in content
    assert str(project_dir) in content


def test_write_claude_skill_md_idempotent_overwrite(tmp_path):
    project_dir = tmp_path / "project"
    home = tmp_path / "home"
    project_dir.mkdir()

    path1 = write_claude_skill_md(project_dir, home=home)
    path2 = write_claude_skill_md(project_dir, home=home)

    assert path1 == path2
    assert path2.exists()


# ---------------------------------------------------------------------------
# read_garmin_approved_permissions
# ---------------------------------------------------------------------------


def _write_mcp_json(project_dir: Path, tools: str) -> None:
    data = {
        "mcpServers": {
            "garmin": {
                "command": "uvx",
                "args": [],
                "env": {"GARMIN_ENABLED_TOOLS": tools},
            }
        }
    }
    (project_dir / ".mcp.json").write_text(json.dumps(data))


def test_read_garmin_approved_permissions_returns_tools(tmp_path):
    _write_mcp_json(tmp_path, "get_morning_training_readiness,get_hrv_data")
    result = read_garmin_approved_permissions(tmp_path)
    assert result == [
        {"toolName": "mcp__garmin__get_morning_training_readiness"},
        {"toolName": "mcp__garmin__get_hrv_data"},
    ]


def test_read_garmin_approved_permissions_missing_mcp_json_returns_empty(tmp_path):
    assert read_garmin_approved_permissions(tmp_path) == []


def test_read_garmin_approved_permissions_no_garmin_server_returns_empty(tmp_path):
    (tmp_path / ".mcp.json").write_text(json.dumps({"mcpServers": {}}))
    assert read_garmin_approved_permissions(tmp_path) == []


def test_read_garmin_approved_permissions_empty_tools_string_returns_empty(tmp_path):
    _write_mcp_json(tmp_path, "")
    assert read_garmin_approved_permissions(tmp_path) == []


def test_read_garmin_approved_permissions_strips_whitespace_and_dedupes(tmp_path):
    _write_mcp_json(tmp_path, " get_hrv_data , get_hrv_data , get_sleep_data ")
    result = read_garmin_approved_permissions(tmp_path)
    assert result == [
        {"toolName": "mcp__garmin__get_hrv_data"},
        {"toolName": "mcp__garmin__get_sleep_data"},
    ]


# ---------------------------------------------------------------------------
# locate_scheduled_tasks_json
# ---------------------------------------------------------------------------


def _seed_tasks_json(support_dir: Path, acct: str, sub: str, content: dict) -> Path:
    p = support_dir / "claude-code-sessions" / acct / sub / "scheduled-tasks.json"
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(json.dumps(content))
    return p


def test_locate_scheduled_tasks_json_no_match_returns_none(tmp_path):
    result = locate_scheduled_tasks_json(tmp_path)
    assert result.path is None
    assert result.all_paths == []


def test_locate_scheduled_tasks_json_one_match_returns_path(tmp_path):
    p = _seed_tasks_json(tmp_path, "acct", "sub", {"scheduledTasks": [], "recordedSkips": {}})
    result = locate_scheduled_tasks_json(tmp_path)
    assert result.path == p
    assert result.all_paths == [p]


def test_locate_scheduled_tasks_json_multiple_returns_most_recent(tmp_path):
    p1 = _seed_tasks_json(tmp_path, "acct", "sub1", {"scheduledTasks": [], "recordedSkips": {}})
    p2 = _seed_tasks_json(tmp_path, "acct", "sub2", {"scheduledTasks": [], "recordedSkips": {}})
    # Make p2 newer
    os.utime(p1, (1_000_000, 1_000_000))
    os.utime(p2, (2_000_000, 2_000_000))

    result = locate_scheduled_tasks_json(tmp_path)
    assert result.path == p2
    assert set(result.all_paths) == {p1, p2}


# ---------------------------------------------------------------------------
# upsert_scheduled_task
# ---------------------------------------------------------------------------


def _make_tasks_json(directory: Path, tasks: list[dict] | None = None) -> Path:
    p = directory / "scheduled-tasks.json"
    p.write_text(json.dumps({"scheduledTasks": tasks or [], "recordedSkips": {}}))
    return p


def test_upsert_creates_new_entry(tmp_path):
    tasks_json = _make_tasks_json(tmp_path)
    skill_md = tmp_path / "SKILL.md"
    skill_md.write_text("")

    result = upsert_scheduled_task(
        tasks_json,
        task_id="coach-daily-loop",
        cron="30 10 * * *",
        skill_md_path=skill_md,
        cwd=tmp_path,
        approved_permissions=[{"toolName": "mcp__garmin__get_hrv_data"}],
        now_ms=999_000,
    )

    assert result["action"] == "created"
    data = json.loads(tasks_json.read_text())
    entry = next(e for e in data["scheduledTasks"] if e["id"] == "coach-daily-loop")
    assert entry["cronExpression"] == "30 10 * * *"
    assert entry["createdAt"] == 999_000
    assert entry["enabled"] is True
    assert entry["useWorktree"] is False
    assert entry["permissionMode"] == "auto"
    assert entry["approvedPermissions"] == [{"toolName": "mcp__garmin__get_hrv_data"}]
    assert entry["filePath"] == str(skill_md)
    assert entry["cwd"] == str(tmp_path)


def test_upsert_updates_existing_entry_preserves_created_at(tmp_path):
    existing = {
        "id": "coach-daily-loop",
        "cronExpression": "0 7 * * *",
        "enabled": True,
        "filePath": "/old/path/SKILL.md",
        "createdAt": 12345,
        "cwd": "/old/cwd",
        "useWorktree": False,
        "permissionMode": "auto",
        "approvedPermissions": [],
        "lastRunAt": "2026-06-15T05:01:09.727Z",   # Desktop-owned field
        "lastScheduledFor": "2026-06-15T05:00:00.000Z",  # Desktop-owned field
        "unknownFutureField": "preserved",           # unknown field
    }
    tasks_json = _make_tasks_json(tmp_path, [existing])
    skill_md = tmp_path / "SKILL.md"
    skill_md.write_text("")

    result = upsert_scheduled_task(
        tasks_json,
        task_id="coach-daily-loop",
        cron="30 10 * * *",
        skill_md_path=skill_md,
        cwd=tmp_path,
        approved_permissions=[{"toolName": "mcp__garmin__get_hrv_data"}],
        now_ms=999_000,  # should NOT overwrite createdAt
    )

    assert result["action"] == "updated"
    data = json.loads(tasks_json.read_text())
    entry = next(e for e in data["scheduledTasks"] if e["id"] == "coach-daily-loop")
    assert entry["cronExpression"] == "30 10 * * *"
    assert entry["createdAt"] == 12345                         # preserved
    assert entry["lastRunAt"] == "2026-06-15T05:01:09.727Z"   # preserved
    assert entry["lastScheduledFor"] == "2026-06-15T05:00:00.000Z"  # preserved
    assert entry["unknownFutureField"] == "preserved"          # preserved
    assert entry["permissionMode"] == "auto"
    assert entry["approvedPermissions"] == [{"toolName": "mcp__garmin__get_hrv_data"}]


def test_upsert_preserves_sibling_entries_and_unknown_top_level_keys(tmp_path):
    sibling = {"id": "some-other-task", "cronExpression": "0 9 * * *", "enabled": True}
    tasks_json = _make_tasks_json(tmp_path, [sibling])
    # Add an unknown top-level key
    raw = json.loads(tasks_json.read_text())
    raw["futureTopLevelKey"] = "keep-me"
    tasks_json.write_text(json.dumps(raw))

    skill_md = tmp_path / "SKILL.md"
    skill_md.write_text("")

    upsert_scheduled_task(
        tasks_json,
        task_id="coach-daily-loop",
        cron="30 10 * * *",
        skill_md_path=skill_md,
        cwd=tmp_path,
        approved_permissions=[],
    )

    data = json.loads(tasks_json.read_text())
    assert data["futureTopLevelKey"] == "keep-me"   # top-level unknown key preserved
    assert any(e["id"] == "some-other-task" for e in data["scheduledTasks"])  # sibling preserved
    assert any(e["id"] == "coach-daily-loop" for e in data["scheduledTasks"])  # new entry added


def test_upsert_auto_disables_overlapping_entry(tmp_path):
    overlap = {
        "id": "readiness-check",
        "cronExpression": "30 10 * * *",
        "enabled": True,
        "filePath": "/home/.claude/scheduled-tasks/readiness-check/SKILL.md",
    }
    tasks_json = _make_tasks_json(tmp_path, [overlap])
    skill_md = tmp_path / "SKILL.md"
    skill_md.write_text("")

    result = upsert_scheduled_task(
        tasks_json,
        task_id="coach-daily-loop",
        cron="30 10 * * *",
        skill_md_path=skill_md,
        cwd=tmp_path,
        approved_permissions=[],
    )

    assert "readiness-check" in result["disabled_ids"]
    data = json.loads(tasks_json.read_text())
    overlap_entry = next(e for e in data["scheduledTasks"] if e["id"] == "readiness-check")
    assert overlap_entry["enabled"] is False


def test_upsert_atomic_write_no_tmp_file_left(tmp_path):
    tasks_json = _make_tasks_json(tmp_path)
    skill_md = tmp_path / "SKILL.md"
    skill_md.write_text("")

    upsert_scheduled_task(
        tasks_json,
        task_id="coach-daily-loop",
        cron="30 10 * * *",
        skill_md_path=skill_md,
        cwd=tmp_path,
        approved_permissions=[],
    )

    assert not (tmp_path / "scheduled-tasks.json.tmp").exists()
    # Verify result is valid JSON
    json.loads(tasks_json.read_text())


def test_upsert_writes_bak_file(tmp_path):
    tasks_json = _make_tasks_json(tmp_path)
    original = tasks_json.read_text()
    skill_md = tmp_path / "SKILL.md"
    skill_md.write_text("")

    upsert_scheduled_task(
        tasks_json,
        task_id="coach-daily-loop",
        cron="30 10 * * *",
        skill_md_path=skill_md,
        cwd=tmp_path,
        approved_permissions=[],
    )

    bak = tmp_path / "scheduled-tasks.json.bak"
    assert bak.exists()
    assert bak.read_text() == original


def test_upsert_corrupt_json_raises_schedule_file_error(tmp_path):
    tasks_json = tmp_path / "scheduled-tasks.json"
    tasks_json.write_text("{not valid json")

    skill_md = tmp_path / "SKILL.md"
    skill_md.write_text("")

    with pytest.raises(ScheduleFileError):
        upsert_scheduled_task(
            tasks_json,
            task_id="coach-daily-loop",
            cron="30 10 * * *",
            skill_md_path=skill_md,
            cwd=tmp_path,
            approved_permissions=[],
        )

    # Original corrupt file must be left untouched
    assert tasks_json.read_text() == "{not valid json"


# ---------------------------------------------------------------------------
# write_claude_scheduled_task (orchestrator)
# ---------------------------------------------------------------------------


def test_write_claude_scheduled_task_fallback_no_json(tmp_path):
    project_dir = tmp_path / "project"
    home = tmp_path / "home"
    empty_support = tmp_path / "support"
    project_dir.mkdir()

    result = write_claude_scheduled_task(
        time(10, 30), project_dir,
        home=home, claude_support_dir=empty_support,
    )

    assert isinstance(result, ClaudeScheduleResult)
    assert result.registered is False
    assert result.action == "skill_only"
    assert result.reason == "no_desktop_routine"
    assert result.skill_md_path.exists()
    # SKILL.md must use real Desktop format (no schedule/mode)
    content = result.skill_md_path.read_text()
    assert "schedule:" not in content
    assert "mode:" not in content


def test_write_claude_scheduled_task_registers_when_json_exists(tmp_path):
    project_dir = tmp_path / "project"
    home = tmp_path / "home"
    support = tmp_path / "support"
    project_dir.mkdir()
    _write_mcp_json(project_dir, "get_hrv_data,get_sleep_data")

    tasks_json = _seed_tasks_json(support, "acct", "sub", {"scheduledTasks": [], "recordedSkips": {}})

    result = write_claude_scheduled_task(
        time(10, 30), project_dir,
        home=home, claude_support_dir=support, now_ms=555_000,
    )

    assert result.registered is True
    assert result.action == "created"
    assert result.tasks_json_path == tasks_json

    data = json.loads(tasks_json.read_text())
    entry = next(e for e in data["scheduledTasks"] if e["id"] == "coach-daily-loop")
    assert entry["cronExpression"] == "30 10 * * *"
    assert entry["permissionMode"] == "auto"
    assert {"toolName": "mcp__garmin__get_hrv_data"} in entry["approvedPermissions"]
    assert {"toolName": "mcp__garmin__get_sleep_data"} in entry["approvedPermissions"]


def test_write_claude_scheduled_task_auto_disables_overlap(tmp_path):
    project_dir = tmp_path / "project"
    home = tmp_path / "home"
    support = tmp_path / "support"
    project_dir.mkdir()

    overlap = {"id": "readiness-check", "enabled": True,
               "filePath": "/home/.claude/scheduled-tasks/readiness-check/SKILL.md",
               "cronExpression": "30 10 * * *"}
    _seed_tasks_json(support, "acct", "sub",
                     {"scheduledTasks": [overlap], "recordedSkips": {}})

    result = write_claude_scheduled_task(
        time(10, 30), project_dir,
        home=home, claude_support_dir=support,
    )

    assert "readiness-check" in result.disabled_ids


def test_write_claude_scheduled_task_fallback_corrupt_json(tmp_path):
    project_dir = tmp_path / "project"
    home = tmp_path / "home"
    support = tmp_path / "support"
    project_dir.mkdir()

    tasks_json = support / "claude-code-sessions" / "acct" / "sub" / "scheduled-tasks.json"
    tasks_json.parent.mkdir(parents=True, exist_ok=True)
    tasks_json.write_text("{bad json")

    result = write_claude_scheduled_task(
        time(10, 30), project_dir,
        home=home, claude_support_dir=support,
    )

    assert result.registered is False
    assert result.reason == "json_unreadable"
    # Corrupt file must be left untouched
    assert tasks_json.read_text() == "{bad json"


# ---------------------------------------------------------------------------
# write_codex_automation  (unchanged)
# ---------------------------------------------------------------------------


def test_write_codex_automation(tmp_path):
    project_dir = tmp_path / "project"
    project_dir.mkdir()

    path = write_codex_automation(time(7, 0), project_dir)

    expected_path = project_dir / ".codex" / "automations" / "daily-coach-loop.toml"
    assert path == expected_path
    assert path.exists()

    expected_content = """name = "daily-coach-loop"
prompt = "Run $readiness-check, then $generate-daily-workout, for today."
schedule = "0 7 * * *"
mode = "local"
"""
    assert path.read_text() == expected_content


def test_write_codex_automation_idempotent_overwrite(tmp_path):
    project_dir = tmp_path / "project"
    project_dir.mkdir()

    path1 = write_codex_automation(time(7, 0), project_dir)
    path2 = write_codex_automation(time(18, 30), project_dir)

    assert path1 == path2
    content = path2.read_text()
    assert 'schedule = "30 18 * * *"' in content
    assert "0 7 * * *" not in content


# ---------------------------------------------------------------------------
# write_cron_fallback  (unchanged)
# ---------------------------------------------------------------------------


def test_write_cron_fallback(tmp_path):
    project_dir = tmp_path / "project"
    home = tmp_path / "home"
    project_dir.mkdir()

    path = write_cron_fallback(time(7, 0), project_dir, home=home)

    expected_path = home / "Library" / "LaunchAgents" / "com.coachai.dailyloop.plist"
    assert path == expected_path
    assert path.exists()

    expected_content = f"""<?xml version="1.0" encoding="UTF-8"?>
<plist version="1.0"><dict>
  <key>Label</key><string>com.coachai.dailyloop</string>
  <key>ProgramArguments</key><array>
    <string>codex</string><string>exec</string><string>--full-auto</string>
    <string>Run readiness-check, then generate-daily-workout, for today.</string>
  </array>
  <key>WorkingDirectory</key><string>{project_dir}</string>
  <key>StartCalendarInterval</key><dict><key>Hour</key><integer>7</integer><key>Minute</key><integer>0</integer></dict>
</dict></plist>
"""
    assert path.read_text() == expected_content


def test_write_cron_fallback_idempotent_overwrite(tmp_path):
    project_dir = tmp_path / "project"
    home = tmp_path / "home"
    project_dir.mkdir()

    path1 = write_cron_fallback(time(7, 0), project_dir, home=home)
    path2 = write_cron_fallback(time(18, 30), project_dir, home=home)

    assert path1 == path2
    content = path2.read_text()
    assert "<integer>18</integer>" in content
    assert "<integer>30</integer>" in content
    assert "<integer>7</integer>" not in content
