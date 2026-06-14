import re

import pytest

from coach.analysis.assemble import assemble

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

GOAL = {
    "id": "goal-5k-sub22",
    "title": "Sub-22:00 5K",
    "sport": "running",
    "goal_type": "event",
    "target_date": "2026-09-01",
    "target_metrics": {"time_seconds": 1320},
    "priority": "high",
    "status": "active",
    "created": "2026-01-01",
    "notes": "Build aerobic base first",
    "research_file": "goal-5k-sub22.md",
}


GARMIN_PLAN_NOTE = {
    "date": "2026-06-13",
    "sport": "running",
    "intent": "Z2 aerobic base",
    "rationale": "Easy aerobic day after yesterday's strength session",
    "goal_id": "goal-5k-sub22",
    "block_context": "base-building",
    "target_summary": "45 min easy run, HR < 150",
    "workout_ref": "wko_88213",
    "workout_source": "garmin",
}

STRAVA_PLAN_NOTE = {
    "date": "2026-06-13",
    "sport": "running",
    "intent": "Z2 aerobic base",
    "rationale": "Easy aerobic day after yesterday's strength session",
    "goal_id": "goal-5k-sub22",
    "block_context": "base-building",
    "target_summary": "45 min easy, keep it conversational",
    "workout_ref": "evt_8a91f2",
    "workout_source": "google_calendar",
}


GARMIN_ACTUAL_ACTIVITY = {
    "activity_id": "19283746",
    "duration_min": 47,
    "distance_km": 7.9,
    "avg_hr": 154,
    "training_effect": {"aerobic": 2.8, "anaerobic": 0.4},
    "execution_score": "completed",
}

STRAVA_ACTUAL_ACTIVITY = {
    "activity_id": "19283746",
    "duration_min": 47,
    "distance_km": 7.9,
    "avg_hr": 154,
}

RECENT_ACTIVITIES = [
    {"date": "2026-06-12", "type": "strength", "duration_min": 40},
    {"date": "2026-06-10", "type": "running", "duration_min": 35},
]

GARMIN_READINESS = {
    "training_readiness": 68,
    "hrv_status": "balanced",
    "sleep_score": 74,
}


def test_garmin_path_full_capability():
    output = assemble(
        date="2026-06-13",
        goal=GOAL,
        plan_note=GARMIN_PLAN_NOTE,
        actual_activity=GARMIN_ACTUAL_ACTIVITY,
        recent_activities=RECENT_ACTIVITIES,
        readiness=GARMIN_READINESS,
        capabilities=GARMIN_CAPABILITIES,
    )

    assert output["date"] == "2026-06-13"

    # goal projected down to id/title/target_date
    assert output["goal"] == {
        "id": "goal-5k-sub22",
        "title": "Sub-22:00 5K",
        "target_date": "2026-09-01",
    }

    # plan projected down to intent/target_summary/workout_ref/workout_source
    assert output["plan"] == {
        "intent": "Z2 aerobic base",
        "target_summary": "45 min easy run, HR < 150",
        "workout_ref": "wko_88213",
        "workout_source": "garmin",
    }

    # actual includes training_effect + execution_score, no avg_pace_min_km
    actual = output["actual"]
    assert actual["activity_id"] == "19283746"
    assert actual["duration_min"] == 47
    assert actual["distance_km"] == 7.9
    assert actual["avg_hr"] == 154
    assert actual["training_effect"] == {"aerobic": 2.8, "anaerobic": 0.4}
    assert actual["execution_score"] == "completed"
    assert "avg_pace_min_km" not in actual

    # readiness present and projected
    assert output["readiness"] == {
        "training_readiness": 68,
        "hrv_status": "balanced",
        "sleep_score": 74,
    }

    # recent_load present and sorted by date
    assert [item["date"] for item in output["recent_load"]] == ["2026-06-10", "2026-06-12"]
    assert {item["type"] for item in output["recent_load"]} == {"strength", "running"}


def test_strava_calendar_path_reduced_capability():
    output = assemble(
        date="2026-06-13",
        goal=GOAL,
        plan_note=STRAVA_PLAN_NOTE,
        actual_activity=STRAVA_ACTUAL_ACTIVITY,
        recent_activities=RECENT_ACTIVITIES,
        readiness=None,
        capabilities=STRAVA_CALENDAR_CAPABILITIES,
    )

    assert output["date"] == "2026-06-13"

    assert output["goal"] == {
        "id": "goal-5k-sub22",
        "title": "Sub-22:00 5K",
        "target_date": "2026-09-01",
    }

    assert output["plan"] == {
        "intent": "Z2 aerobic base",
        "target_summary": "45 min easy, keep it conversational",
        "workout_ref": "evt_8a91f2",
        "workout_source": "google_calendar",
    }

    actual = output["actual"]
    assert "training_effect" not in actual
    assert "execution_score" not in actual
    assert actual["avg_pace_min_km"] == pytest.approx(47 / 7.9, rel=1e-3)

    # no readiness key at all (not null)
    assert "readiness" not in output

    assert {item["type"] for item in output["recent_load"]} == {"strength", "running"}


def test_goal_none_and_plan_note_none_omit_keys():
    output = assemble(
        date="2026-06-13",
        goal=None,
        plan_note=None,
        actual_activity=GARMIN_ACTUAL_ACTIVITY,
        recent_activities=[],
        readiness=None,
        capabilities=GARMIN_CAPABILITIES,
    )

    assert "goal" not in output
    assert "plan" not in output
    # confirm they are truly absent, not None
    assert output.get("goal", "sentinel") == "sentinel"
    assert output.get("plan", "sentinel") == "sentinel"


def test_actual_activity_none_omits_actual_key():
    output = assemble(
        date="2026-06-13",
        goal=GOAL,
        plan_note=GARMIN_PLAN_NOTE,
        actual_activity=None,
        recent_activities=[],
        readiness=None,
        capabilities=GARMIN_CAPABILITIES,
    )

    assert "actual" not in output


def test_readiness_omitted_without_supporting_capability():
    # Even if a readiness dict is supplied, it should be omitted if none of
    # readiness/hrv/sleep/body_battery are in the capability set.
    output = assemble(
        date="2026-06-13",
        goal=GOAL,
        plan_note=STRAVA_PLAN_NOTE,
        actual_activity=STRAVA_ACTUAL_ACTIVITY,
        recent_activities=[],
        readiness=GARMIN_READINESS,
        capabilities=STRAVA_CALENDAR_CAPABILITIES,
    )

    assert "readiness" not in output


# Allow-list: execution_score and sleep_score are explicitly part of the
# techspec 5.4 example payload and are not forbidden "verdict"/"score" fields
# (sleep_score is a pass-through of Garmin's own sleep score, not a Python
# verdict).
_ALLOWED_SCORE_KEYS = {"execution_score", "sleep_score"}
_FORBIDDEN_PATTERN = re.compile(r"score|verdict|rating|vo2|tss|ctl|atl|tsb", re.IGNORECASE)


def _walk_keys(obj):
    if isinstance(obj, dict):
        for key, value in obj.items():
            yield key
            yield from _walk_keys(value)
    elif isinstance(obj, list):
        for item in obj:
            yield from _walk_keys(item)


@pytest.mark.parametrize(
    "capabilities, actual_activity, readiness",
    [
        (GARMIN_CAPABILITIES, GARMIN_ACTUAL_ACTIVITY, GARMIN_READINESS),
        (STRAVA_CALENDAR_CAPABILITIES, STRAVA_ACTUAL_ACTIVITY, None),
    ],
)
def test_no_python_verdicts_or_scores(capabilities, actual_activity, readiness):
    output = assemble(
        date="2026-06-13",
        goal=GOAL,
        plan_note=GARMIN_PLAN_NOTE if "training_effect" in capabilities else STRAVA_PLAN_NOTE,
        actual_activity=actual_activity,
        recent_activities=RECENT_ACTIVITIES,
        readiness=readiness,
        capabilities=capabilities,
    )

    for key in _walk_keys(output):
        if key in _ALLOWED_SCORE_KEYS:
            continue
        assert not _FORBIDDEN_PATTERN.search(key), f"forbidden key found: {key!r}"
