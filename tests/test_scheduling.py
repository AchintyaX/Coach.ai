from datetime import time
from pathlib import Path

import pytest

from coach.scheduling import (
    TIME_FORMATS,
    parse_time_of_day,
    to_cron,
    write_claude_scheduled_task,
    write_codex_automation,
    write_cron_fallback,
)


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


def test_write_claude_scheduled_task(tmp_path):
    project_dir = tmp_path / "project"
    home = tmp_path / "home"
    project_dir.mkdir()

    path = write_claude_scheduled_task(time(7, 0), project_dir, home=home)

    expected_path = home / ".claude" / "scheduled-tasks" / "coach-daily-loop" / "SKILL.md"
    assert path == expected_path
    assert path.exists()

    expected_content = f"""---
name: coach-daily-loop
description: Daily readiness check and workout generation for Coach AI
schedule: "0 7 * * *"
mode: local
---

Open the Coach AI project at {project_dir}.
Run the `readiness-check` skill, then the `generate-daily-workout` skill, for today.
"""
    assert path.read_text() == expected_content


def test_write_claude_scheduled_task_idempotent_overwrite(tmp_path):
    project_dir = tmp_path / "project"
    home = tmp_path / "home"
    project_dir.mkdir()

    path1 = write_claude_scheduled_task(time(7, 0), project_dir, home=home)
    path2 = write_claude_scheduled_task(time(18, 30), project_dir, home=home)

    assert path1 == path2
    content = path2.read_text()
    assert 'schedule: "30 18 * * *"' in content
    assert "0 7 * * *" not in content


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
