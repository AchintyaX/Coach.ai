from __future__ import annotations

import json
import os
import time as _time
from dataclasses import dataclass, field
from datetime import datetime, time
from pathlib import Path

TIME_FORMATS = ["%I:%M %p", "%I %p", "%H:%M"]

# Skill identifiers that are part of the morning loop — used to detect overlap.
_LOOP_SKILL_IDS = frozenset({"readiness-check", "generate-daily-workout"})
_LOOP_SKILL_SUBSTRINGS = ("readiness-check", "generate-daily-workout")


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


# ---------------------------------------------------------------------------
# Claude Desktop scheduling (real format, reverse-engineered from live Desktop)
# ---------------------------------------------------------------------------


class ScheduleFileError(Exception):
    """Raised when Desktop's scheduled-tasks.json cannot be parsed safely."""


@dataclass
class LocateResult:
    """Result of locate_scheduled_tasks_json."""

    path: Path | None       # best candidate (most-recently-modified), or None
    all_paths: list[Path]   # all matches (empty when path is None)


@dataclass
class ClaudeScheduleResult:
    """Return value of write_claude_scheduled_task."""

    skill_md_path: Path
    tasks_json_path: Path | None
    registered: bool
    action: str             # "created" | "updated" | "skill_only"
    reason: str | None      # "no_desktop_routine" | "json_unreadable" | None
    ambiguous: bool = False
    disabled_ids: list[str] = field(default_factory=list)


def write_claude_skill_md(
    project_dir: Path,
    *,
    task_id: str = "coach-daily-loop",
    description: str = "Daily readiness check and workout generation for Coach AI",
    home: Path | None = None,
) -> Path:
    """Write ~/.claude/scheduled-tasks/<task_id>/SKILL.md in the real Desktop format.

    Frontmatter contains only ``name`` and ``description``.  The ``schedule`` /
    ``mode`` fields the old writer used are ignored by Desktop and are omitted.
    Overwrite-idempotent.
    """
    home = home or Path.home()
    path = home / ".claude" / "scheduled-tasks" / task_id / "SKILL.md"
    content = (
        f"---\n"
        f"name: {task_id}\n"
        f"description: {description}\n"
        f"---\n"
        f"\n"
        f"Open the Coach AI project at {project_dir}.\n"
        f"Run the `readiness-check` skill, then the `generate-daily-workout` skill, for today.\n"
    )
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content)
    return path


def read_garmin_approved_permissions(project_dir: Path) -> list[dict]:
    """Seed approvedPermissions from the project's .mcp.json (best-effort).

    Reads ``mcpServers.garmin.env.GARMIN_ENABLED_TOOLS``, splits on commas, and
    maps each tool name to ``{"toolName": "mcp__garmin__<tool>"}``.  Returns ``[]``
    if the file is missing, unparseable, or the garmin key / env var is absent.
    """
    try:
        data = json.loads(
            (project_dir / ".mcp.json").read_text(encoding="utf-8")
        )
        tools_str: str = (
            data.get("mcpServers", {})
            .get("garmin", {})
            .get("env", {})
            .get("GARMIN_ENABLED_TOOLS", "")
        )
        raw_tools = [t.strip() for t in tools_str.split(",") if t.strip()]
        # dedupe preserving order
        seen: set[str] = set()
        unique: list[str] = []
        for t in raw_tools:
            if t not in seen:
                seen.add(t)
                unique.append(t)
        return [{"toolName": f"mcp__garmin__{t}"} for t in unique]
    except Exception:
        return []


def locate_scheduled_tasks_json(
    claude_support_dir: Path | None = None,
) -> LocateResult:
    """Find Desktop's scheduled-tasks.json under the Application Support tree.

    Globs ``claude-code-sessions/*/*/scheduled-tasks.json``.  On >1 match the
    most recently modified file is chosen; ``all_paths`` is always populated so
    the caller can detect ambiguity.
    """
    base = claude_support_dir or (
        Path.home() / "Library" / "Application Support" / "Claude"
    )
    matches = sorted(base.glob("claude-code-sessions/*/*/scheduled-tasks.json"))
    if not matches:
        return LocateResult(path=None, all_paths=[])
    if len(matches) == 1:
        return LocateResult(path=matches[0], all_paths=list(matches))
    best = max(matches, key=lambda p: p.stat().st_mtime)
    return LocateResult(path=best, all_paths=list(matches))


def _is_loop_entry(entry: dict) -> bool:
    """Return True if an existing task entry overlaps with the morning-loop skills."""
    entry_id: str = entry.get("id", "")
    file_path: str = entry.get("filePath", "")
    if entry_id in _LOOP_SKILL_IDS:
        return True
    return any(sub in file_path for sub in _LOOP_SKILL_SUBSTRINGS)


def upsert_scheduled_task(
    tasks_json_path: Path,
    *,
    task_id: str,
    cron: str,
    skill_md_path: Path,
    cwd: Path,
    approved_permissions: list[dict],
    now_ms: int | None = None,
) -> dict:
    """Read-modify-write Desktop's scheduled-tasks.json, upserting by task id.

    Returns ``{"data": <full JSON dict>, "action": "created"|"updated",
    "disabled_ids": [...]}``.

    Raises ``ScheduleFileError`` if the file cannot be parsed safely — never
    overwrites a file we can't read cleanly.  Writes atomically via a temp file
    + ``os.replace``.  Best-effort ``.bak`` snapshot written before modification.
    """
    try:
        raw = tasks_json_path.read_text(encoding="utf-8")
        data: dict = json.loads(raw)
    except json.JSONDecodeError as exc:
        raise ScheduleFileError(
            f"Could not parse {tasks_json_path}: {exc}"
        ) from exc
    except OSError as exc:
        raise ScheduleFileError(
            f"Could not read {tasks_json_path}: {exc}"
        ) from exc

    # Defensive defaults — preserve any unknown top-level keys verbatim.
    data.setdefault("scheduledTasks", [])
    data.setdefault("recordedSkips", {})

    tasks: list[dict] = data["scheduledTasks"]

    # --- upsert ---
    existing_idx = next(
        (i for i, e in enumerate(tasks) if e.get("id") == task_id), None
    )
    if existing_idx is not None:
        # Update in place — preserve createdAt and all Desktop-owned / unknown fields.
        entry = tasks[existing_idx]
        entry["cronExpression"] = cron
        entry["enabled"] = True
        entry["filePath"] = str(skill_md_path)
        entry["cwd"] = str(cwd)
        entry["permissionMode"] = "auto"
        entry["approvedPermissions"] = approved_permissions
        action = "updated"
    else:
        # Create a new entry.
        ts = now_ms if now_ms is not None else int(_time.time() * 1000)
        tasks.append(
            {
                "id": task_id,
                "cronExpression": cron,
                "enabled": True,
                "filePath": str(skill_md_path),
                "createdAt": ts,
                "cwd": str(cwd),
                "useWorktree": False,
                "permissionMode": "auto",
                "approvedPermissions": approved_permissions,
            }
        )
        action = "created"

    # --- auto-disable overlapping routines ---
    disabled_ids: list[str] = []
    for other in tasks:
        if other.get("id") == task_id:
            continue
        try:
            if other.get("enabled", False) and _is_loop_entry(other):
                other["enabled"] = False
                disabled_ids.append(str(other["id"]))
        except Exception:
            pass  # never let overlap detection block the write

    # --- atomic write with best-effort .bak snapshot ---
    bak_path = tasks_json_path.with_suffix(".json.bak")
    try:
        bak_path.write_text(raw, encoding="utf-8")
    except Exception:
        pass  # best-effort

    tmp_path = tasks_json_path.with_suffix(".json.tmp")
    try:
        tmp_path.write_text(json.dumps(data, indent=2), encoding="utf-8")
        os.replace(tmp_path, tasks_json_path)
    except Exception:
        try:
            tmp_path.unlink(missing_ok=True)
        except Exception:
            pass
        raise

    return {"data": data, "action": action, "disabled_ids": disabled_ids}


def write_claude_scheduled_task(
    t: time,
    project_dir: Path,
    *,
    home: Path | None = None,
    claude_support_dir: Path | None = None,
    now_ms: int | None = None,
) -> ClaudeScheduleResult:
    """Orchestrate the full Claude Desktop scheduled-task setup.

    1. Writes the minimal correct SKILL.md.
    2. Computes the cron expression.
    3. Seeds approvedPermissions from .mcp.json (best-effort).
    4. Locates Desktop's scheduled-tasks.json and upserts the entry.

    Falls back gracefully (returns ``registered=False``) when no JSON exists yet
    or it cannot be parsed safely.
    """
    skill_md_path = write_claude_skill_md(project_dir, home=home)
    cron = to_cron(t)
    approved = read_garmin_approved_permissions(project_dir)
    located = locate_scheduled_tasks_json(claude_support_dir)

    if located.path is None:
        return ClaudeScheduleResult(
            skill_md_path=skill_md_path,
            tasks_json_path=None,
            registered=False,
            action="skill_only",
            reason="no_desktop_routine",
        )

    try:
        result = upsert_scheduled_task(
            located.path,
            task_id="coach-daily-loop",
            cron=cron,
            skill_md_path=skill_md_path,
            cwd=project_dir,
            approved_permissions=approved,
            now_ms=now_ms,
        )
    except ScheduleFileError:
        return ClaudeScheduleResult(
            skill_md_path=skill_md_path,
            tasks_json_path=located.path,
            registered=False,
            action="skill_only",
            reason="json_unreadable",
        )

    return ClaudeScheduleResult(
        skill_md_path=skill_md_path,
        tasks_json_path=located.path,
        registered=True,
        action=result["action"],
        reason=None,
        ambiguous=len(located.all_paths) > 1,
        disabled_ids=result["disabled_ids"],
    )


# ---------------------------------------------------------------------------
# Codex + launchd writers (unchanged)
# ---------------------------------------------------------------------------


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
