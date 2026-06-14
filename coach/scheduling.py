from datetime import datetime, time
from pathlib import Path

TIME_FORMATS = ["%I:%M %p", "%I %p", "%H:%M"]


def parse_time_of_day(raw: str) -> time:
    """Parse "7:00 AM" / "7 am" / "07:00" — first matching format wins.
    Raises ValueError with a helpful message if none match."""
    raw = raw.strip()
    for fmt in TIME_FORMATS:
        try:
            return datetime.strptime(raw, fmt).time()
        except ValueError:
            continue
    formats = ", ".join(TIME_FORMATS)
    raise ValueError(
        f'Could not parse time of day "{raw}". '
        f"Accepted formats: {formats} (e.g. \"7:00 AM\", \"7 AM\", \"07:00\")."
    )


def to_cron(t: time) -> str:
    """time(7, 0) -> "0 7 * * *" (daily)"""
    return f"{t.minute} {t.hour} * * *"


def write_claude_scheduled_task(t: time, project_dir: Path, home: Path | None = None) -> Path:
    """~/.claude/scheduled-tasks/coach-daily-loop/SKILL.md — local-mode task."""
    home = home or Path.home()
    cron = to_cron(t)
    path = home / ".claude" / "scheduled-tasks" / "coach-daily-loop" / "SKILL.md"
    content = f"""---
name: coach-daily-loop
description: Daily readiness check and workout generation for Coach AI
schedule: "{cron}"
mode: local
---

Open the Coach AI project at {project_dir}.
Run the `readiness-check` skill, then the `generate-daily-workout` skill, for today.
"""
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content)
    return path


def write_codex_automation(t: time, project_dir: Path) -> Path:
    """./.codex/automations/daily-coach-loop.toml — mode = "local"."""
    cron = to_cron(t)
    path = project_dir / ".codex" / "automations" / "daily-coach-loop.toml"
    content = f"""name = "daily-coach-loop"
prompt = "Run $readiness-check, then $generate-daily-workout, for today."
schedule = "{cron}"
mode = "local"
"""
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content)
    return path


def write_cron_fallback(t: time, project_dir: Path, home: Path | None = None) -> Path:
    """launchd plist (macOS) or crontab line — Codex CLI without Desktop."""
    home = home or Path.home()
    path = home / "Library" / "LaunchAgents" / "com.coachai.dailyloop.plist"
    content = f"""<?xml version="1.0" encoding="UTF-8"?>
<plist version="1.0"><dict>
  <key>Label</key><string>com.coachai.dailyloop</string>
  <key>ProgramArguments</key><array>
    <string>codex</string><string>exec</string><string>--full-auto</string>
    <string>Run readiness-check, then generate-daily-workout, for today.</string>
  </array>
  <key>WorkingDirectory</key><string>{project_dir}</string>
  <key>StartCalendarInterval</key><dict><key>Hour</key><integer>{t.hour}</integer><key>Minute</key><integer>{t.minute}</integer></dict>
</dict></plist>
"""
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content)
    return path
