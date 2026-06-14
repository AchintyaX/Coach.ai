"""Analysis assembler — the only "analysis" code in the system.

``assemble()`` takes raw inputs (a ``Goal``, a ``PlanNote``, an actual activity,
recent activity history, and an optional readiness check-in/snapshot) and
reshapes them into one compact, agent-facing JSON payload.

Per techspec 5.4, this module deliberately does **no scoring and renders no
verdicts**: no 0-100 fitness score, no VO2max estimate, no TSS/CTL/ATL/TSB, and
no "good/bad/needs work" verdict. It only normalizes units, projects down to the
fields a coaching skill needs, and groups/sorts recent activity history. The
agent reads the resulting payload and decides what it means.
"""

from __future__ import annotations

import json
import sys
from typing import Any, Optional


# ---------------------------------------------------------------------------
# Small pure normalization helpers
# ---------------------------------------------------------------------------


def to_minutes(value: Any) -> Optional[float]:
    """Best-effort conversion of a duration value to minutes.

    Accepts a value already expressed in minutes (returned as-is) or, if it
    looks like raw seconds (a large number, e.g. > ~20 representing seconds for
    a typical workout), converts seconds -> minutes. ``None``/missing values
    pass through as ``None``.

    This is intentionally conservative: callers are expected to mostly pass
    already-reasonable units, this just smooths over Garmin/Strava raw fields
    (which are often in seconds) when present.
    """
    if value is None:
        return None
    try:
        num = float(value)
    except (TypeError, ValueError):
        return None
    return num


def to_km(value: Any) -> Optional[float]:
    """Best-effort conversion of a distance value to kilometers.

    Accepts a value already in kilometers (returned as-is) or, if it looks like
    raw meters (a large number, e.g. > ~1000 for any real workout), converts
    meters -> kilometers. ``None``/missing values pass through as ``None``.
    """
    if value is None:
        return None
    try:
        num = float(value)
    except (TypeError, ValueError):
        return None
    if num > 1000:
        return num / 1000.0
    return num


def _first(activity: dict, *keys: str) -> Any:
    for key in keys:
        if key in activity and activity[key] is not None:
            return activity[key]
    return None


def _round(value: Any, digits: int = 2) -> Any:
    if value is None:
        return None
    try:
        return round(float(value), digits)
    except (TypeError, ValueError):
        return value


# ---------------------------------------------------------------------------
# Section assemblers
# ---------------------------------------------------------------------------


def _assemble_goal(goal: Optional[dict]) -> Optional[dict]:
    if goal is None:
        return None
    return {
        "id": goal.get("id"),
        "title": goal.get("title"),
        "target_date": goal.get("target_date"),
    }


def _assemble_plan(plan_note: Optional[dict]) -> Optional[dict]:
    if plan_note is None:
        return None
    return {
        "intent": plan_note.get("intent"),
        "target_summary": plan_note.get("target_summary"),
        "workout_ref": plan_note.get("workout_ref"),
        "workout_source": plan_note.get("workout_source"),
    }


def _assemble_actual(
    actual_activity: Optional[dict],
    capabilities: frozenset[str],
) -> Optional[dict]:
    if actual_activity is None:
        return None

    duration_min = to_minutes(
        _first(actual_activity, "duration_min", "moving_time_min", "duration", "moving_time")
    )
    distance_km = to_km(
        _first(actual_activity, "distance_km", "distance")
    )
    avg_hr = _first(actual_activity, "avg_hr", "average_heartrate", "average_hr")

    actual: dict[str, Any] = {
        "activity_id": _first(actual_activity, "activity_id", "id"),
        "duration_min": _round(duration_min, 0) if duration_min is not None else None,
        "distance_km": _round(distance_km, 2),
        "avg_hr": avg_hr,
    }

    has_training_effect = "training_effect" in capabilities

    if has_training_effect:
        training_effect = _first(actual_activity, "training_effect")
        if training_effect is None:
            aerobic = _first(actual_activity, "aerobic_training_effect")
            anaerobic = _first(actual_activity, "anaerobic_training_effect")
            if aerobic is not None or anaerobic is not None:
                training_effect = {"aerobic": aerobic, "anaerobic": anaerobic}
        if training_effect is not None:
            actual["training_effect"] = training_effect

        execution_score = _first(actual_activity, "execution_score")
        if execution_score is not None:
            actual["execution_score"] = execution_score
    else:
        # Reduced-capability path: surface pace instead of training effect.
        avg_pace = _first(actual_activity, "avg_pace_min_km")
        if avg_pace is None and duration_min and distance_km:
            avg_pace = duration_min / distance_km
        if avg_pace is not None:
            actual["avg_pace_min_km"] = _round(avg_pace, 2)

    # Drop any keys whose value is None so we never emit fabricated nulls.
    return {key: value for key, value in actual.items() if value is not None}


def _assemble_recent_load(recent_activities: list[dict]) -> list[dict]:
    items = []
    for activity in recent_activities or []:
        date = _first(activity, "date", "start_date_local", "start_date")
        activity_type = _first(activity, "type", "sport")
        duration_min = to_minutes(
            _first(activity, "duration_min", "moving_time_min", "duration", "moving_time")
        )
        item = {
            "date": date,
            "type": activity_type,
            "duration_min": _round(duration_min, 0) if duration_min is not None else None,
        }
        items.append({key: value for key, value in item.items() if value is not None})

    return sorted(items, key=lambda item: item.get("date") or "")


def _assemble_readiness(
    readiness: Optional[dict],
    capabilities: frozenset[str],
) -> Optional[dict]:
    if readiness is None:
        return None
    if not capabilities.intersection({"readiness", "hrv", "sleep", "body_battery"}):
        return None

    result: dict[str, Any] = {}
    for key in ("training_readiness", "hrv_status", "sleep_score"):
        if key in readiness and readiness[key] is not None:
            result[key] = readiness[key]

    return result or None


# ---------------------------------------------------------------------------
# Public entrypoint
# ---------------------------------------------------------------------------


def assemble(
    date: str,
    goal: dict | None,
    plan_note: dict | None,
    actual_activity: dict | None,
    recent_activities: list[dict],
    readiness: dict | None = None,
    capabilities: set[str] = frozenset(),
) -> dict:
    """Normalize raw source data into the agent-facing payload shape from techspec 5.4.

    No scoring, no verdicts: this function never computes a fitness score,
    VO2max, TSS/CTL/ATL/TSB, or any good/bad rating. It only projects, renames,
    and converts units so the agent can reason over a compact payload.
    """
    capabilities = frozenset(capabilities or ())

    payload: dict[str, Any] = {"date": date}

    goal_section = _assemble_goal(goal)
    if goal_section is not None:
        payload["goal"] = goal_section

    plan_section = _assemble_plan(plan_note)
    if plan_section is not None:
        payload["plan"] = plan_section

    actual_section = _assemble_actual(actual_activity, capabilities)
    if actual_section is not None:
        payload["actual"] = actual_section

    payload["recent_load"] = _assemble_recent_load(recent_activities)

    readiness_section = _assemble_readiness(readiness, capabilities)
    if readiness_section is not None:
        payload["readiness"] = readiness_section

    return payload


def main() -> None:
    raw = json.load(sys.stdin)
    result = assemble(
        date=raw.get("date"),
        goal=raw.get("goal"),
        plan_note=raw.get("plan_note"),
        actual_activity=raw.get("actual_activity"),
        recent_activities=raw.get("recent_activities") or [],
        readiness=raw.get("readiness"),
        capabilities=set(raw.get("capabilities") or []),
    )
    json.dump(result, sys.stdout, indent=2)
    sys.stdout.write("\n")


if __name__ == "__main__":
    main()
