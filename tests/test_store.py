import json

from coach.storage.schema import Goal, MetricsSnapshot, PlanNote, ReadinessCheckin, Subjective
from coach.storage.store import (
    append_readiness,
    load_goals,
    load_personality,
    load_plan_note,
    load_profile,
    save_goals,
    save_personality,
    save_plan_note,
    save_research,
)


def test_load_goals_empty_when_missing(tmp_path):
    assert load_goals(data_dir=tmp_path) == []


def test_save_and_load_goals_round_trip(tmp_path):
    goals = [
        Goal(
            id="goal-5k-sub22",
            title="Sub-22:00 5K",
            sport="running",
            goal_type="event",
            target_date="2026-09-01",
            target_metrics={"time_seconds": 1320},
            priority="high",
            status="active",
            created="2026-06-01",
            notes="Focus on aerobic base first",
            research_file="goals/research/goal-5k-sub22.md",
        ),
        Goal(
            id="goal-deadlift",
            title="Deadlift 1.5x bodyweight",
            sport="strength",
            goal_type="metric",
            priority="medium",
            status="active",
            created="2026-06-01",
        ),
    ]

    save_goals(goals, data_dir=tmp_path)

    path = tmp_path / "goals" / "goals.json"
    assert path.exists()

    loaded = load_goals(data_dir=tmp_path)
    assert loaded == goals


def test_save_research_writes_markdown_file(tmp_path):
    path = save_research("goal-5k-sub22", "# Research\n\nSome notes.", data_dir=tmp_path)

    assert path == tmp_path / "goals" / "research" / "goal-5k-sub22.md"
    assert path.exists()
    assert path.read_text() == "# Research\n\nSome notes."


def test_save_and_load_plan_note_round_trip(tmp_path):
    note = PlanNote(
        date="2026-06-13",
        sport="running",
        intent="Z2 aerobic base",
        rationale="Building aerobic capacity ahead of the 5K block",
        goal_id="goal-5k-sub22",
        block_context="base phase, week 3 of 6",
        target_summary="45 min easy run, HR < 150",
        workout_ref="wko_88213",
        workout_source="garmin",
    )

    path = save_plan_note("2026-06-13", note, data_dir=tmp_path)

    assert path == tmp_path / "plan" / "2026-06-13.json"
    assert path.exists()

    loaded = load_plan_note("2026-06-13", data_dir=tmp_path)
    assert loaded == note


def test_load_plan_note_returns_none_when_missing(tmp_path):
    assert load_plan_note("2026-06-13", data_dir=tmp_path) is None


def test_append_readiness_with_metrics_snapshot(tmp_path):
    checkin = ReadinessCheckin(
        date="2026-06-13",
        subjective=Subjective(energy=7, soreness=3, mood=8, sleep_quality=6, notes="Felt good"),
        metrics_snapshot=MetricsSnapshot(
            training_readiness=68,
            hrv=55.2,
            sleep={"score": 74, "duration_hours": 7.5},
            body_battery=82,
        ),
        recommendation="Proceed as planned.",
    )

    path = append_readiness("2026-06-13", checkin, data_dir=tmp_path)

    assert path == tmp_path / "logs" / "readiness" / "2026-06-13.json"
    raw = json.loads(path.read_text())
    assert raw["metrics_snapshot"]["training_readiness"] == 68


def test_append_readiness_without_metrics_snapshot(tmp_path):
    checkin = ReadinessCheckin(
        date="2026-06-13",
        subjective=Subjective(energy=5, soreness=4, mood=6, sleep_quality=5, notes=None),
        recommendation="Subjective only today.",
    )

    path = append_readiness("2026-06-13", checkin, data_dir=tmp_path)

    raw = json.loads(path.read_text())
    assert raw["metrics_snapshot"] is None


def test_load_profile_empty_when_missing(tmp_path):
    assert load_profile(data_dir=tmp_path) == {}


def test_load_profile_returns_contents(tmp_path):
    profile_path = tmp_path / "athlete" / "profile.json"
    profile_path.parent.mkdir(parents=True)
    profile_path.write_text(json.dumps({"name": "Athlete", "units": "metric"}))

    assert load_profile(data_dir=tmp_path) == {"name": "Athlete", "units": "metric"}


def test_load_personality_none_when_missing(tmp_path):
    assert load_personality(data_dir=tmp_path) is None


def test_save_and_load_personality_round_trip(tmp_path):
    personality = {
        "dials": {
            "push_style": "autonomy-supportive",
            "training_emphasis": "recovery-focused",
            "reasoning_style": "data-informed",
            "structure": "flexible",
            "feedback_warmth": "high-positive",
            "conversation_style": "questioning",
        },
        "philosophy": "Base-building emphasis through August.",
        "research_refs": ["https://example.com/a", "https://example.com/b"],
        "approved": True,
        "last_updated": "2026-06-13",
    }

    path = save_personality(personality, data_dir=tmp_path)

    assert path == tmp_path / "coach" / "personality.json"
    assert path.exists()

    loaded = load_personality(data_dir=tmp_path)
    assert loaded == personality
