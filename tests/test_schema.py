import json

from coach.storage.schema import Goal, MetricsSnapshot, PlanNote, ReadinessCheckin, Subjective


def test_goal_round_trip():
    goal = Goal(
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
    )

    restored = Goal.model_validate(json.loads(goal.model_dump_json()))

    assert restored == goal


def test_goal_round_trip_minimal_fields():
    goal = Goal(
        id="goal-deadlift",
        title="Deadlift 1.5x bodyweight",
        sport="strength",
        goal_type="metric",
        priority="medium",
        status="active",
        created="2026-06-01",
    )

    restored = Goal.model_validate(goal.model_dump())

    assert restored == goal
    assert restored.target_date is None
    assert restored.notes is None
    assert restored.research_file is None


def test_plan_note_round_trip_garmin():
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

    restored = PlanNote.model_validate(json.loads(note.model_dump_json()))

    assert restored == note
    assert restored.workout_source == "garmin"


def test_plan_note_round_trip_calendar_sources():
    for source in ("google_calendar", "outlook_calendar"):
        note = PlanNote(
            date="2026-06-13",
            sport="running",
            intent="Z2 aerobic base",
            rationale="Keep it conversational",
            goal_id="goal-5k-sub22",
            block_context="base phase",
            target_summary="45 min easy, keep it conversational",
            workout_ref="evt_8a91f2",
            workout_source=source,
        )

        restored = PlanNote.model_validate(json.loads(note.model_dump_json()))

        assert restored == note
        assert restored.workout_source == source


def test_readiness_checkin_round_trip_with_metrics_snapshot():
    checkin = ReadinessCheckin(
        date="2026-06-13",
        subjective=Subjective(energy=7, soreness=3, mood=8, sleep_quality=6, notes="Felt good"),
        metrics_snapshot=MetricsSnapshot(
            training_readiness=68,
            hrv=55.2,
            sleep={"score": 74, "duration_hours": 7.5},
            body_battery=82,
        ),
        recommendation="Proceed as planned with an easy aerobic session.",
    )

    restored = ReadinessCheckin.model_validate(json.loads(checkin.model_dump_json()))

    assert restored == checkin
    assert restored.metrics_snapshot is not None
    assert restored.metrics_snapshot.training_readiness == 68


def test_readiness_checkin_round_trip_without_metrics_snapshot():
    checkin = ReadinessCheckin(
        date="2026-06-13",
        subjective=Subjective(energy=5, soreness=4, mood=6, sleep_quality=5, notes=None),
        recommendation="No device metrics available; rely on subjective feel today.",
    )

    dumped = checkin.model_dump()
    assert dumped["metrics_snapshot"] is None

    restored = ReadinessCheckin.model_validate(json.loads(checkin.model_dump_json()))

    assert restored == checkin
    assert restored.metrics_snapshot is None
