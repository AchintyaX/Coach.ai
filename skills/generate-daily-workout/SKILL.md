---
name: generate-daily-workout
description: Generates and schedules today's training session — reads goals and recent training load (plus today's readiness, if available), decides the session's sport/intent/structure, creates it on the active workout-calendar source, and writes a PlanNote linking the two. Invoke this daily during the morning loop, after readiness-check.
when_to_use: "Daily, via /loop"
capabilities: []
allowed-tools: ["{{tool: recent_training_load}}", "{{tool: structured_workout_create}}", "{{tool: schedule_workout}}"]
---

# Generate Daily Workout

Run this once each morning, after `readiness-check`. Follow these steps in order.

1. **Read goals and recent plan notes for context.**
   Both paths:
   ```bash
   cat data/goals/goals.json 2>/dev/null || echo "[]"
   ls data/plan/*.json 2>/dev/null | sort | tail -5
   ```
   Read the most recent 3-5 `data/plan/<date>.json` files (if any exist) to understand what's been planned and how the training is progressing — which sessions/sports have been used recently, what intents have been called out, and which `goal_id` they served. Use this to avoid repeating the same session type too many days in a row and to keep progression (e.g. don't schedule three hard days back-to-back).

2. **Pull recent training load from the active metrics source.**
   Call `{{tool: recent_training_load}}`.

   - **Garmin (Full):** Call `get_training_status`, `get_training_load_trend`, and `get_activities`. Note the current training status label (e.g. "productive", "overreaching", "maintaining"), the acute/chronic load trend, and what was actually done over the last several days.
   - **Strava+Calendar (Degraded):** Call `get-activities` and `get-activity-streams` for the most recent activity/activities. There is no training-status or readiness signal on this path — reason from recent activity load (type, duration, intensity via HR/pace) alone.

3. **Optionally read today's readiness check-in.**
   If `readiness-check` already ran today, read it:
   ```bash
   cat data/logs/readiness/<date>.json 2>/dev/null
   ```
   where `<date>` is today's date (`YYYY-MM-DD`). If the file doesn't exist, proceed without it — don't block on this, and don't run `readiness-check` yourself.

4. **Decide today's session.**
   Using the goals (step 1), recent plan notes (step 1), and recent training load (step 2) — plus today's readiness (step 3), if available — decide:
   - **Sport** for today's session (e.g. running, strength, cycling), chosen to fit the goal(s) in `data/goals/goals.json` and the weekly structure implied by their research notes.
   - **Intent** — the short purpose of the session (e.g. "Z2 aerobic base", "VO2max intervals", "Lower body strength A", "recovery walk").
   - **Structure** — the concrete session shape (duration/distance targets, intervals with work/rest, pace/HR zones, or exercises with sets/reps/rest).

   - **Garmin (Full):** Let training status and readiness directly inform intensity. If training status is "overreaching" or readiness was poor, favor an easy/recovery session regardless of what the broader plan called for, and note this in the `rationale` you write in step 7. Otherwise, follow the progression from recent plan notes toward the active goal(s).
   - **Strava+Calendar (Degraded):** Inform the decision from recent activity load only (step 2) — e.g. back off intensity after a hard or long session in the last 1-2 days, or progress as planned if recent load looks light/moderate. Note in the `rationale` that this decision was made without a training-status or readiness signal.

5. **Create the structured workout.**
   Call `{{tool: structured_workout_create}}`.

   - **Garmin (Full):** Call the builder tool matching today's sport/intent:
     - Running/cardio with intervals or run/walk structure → `create_walk_run_workout`
     - Easy aerobic/Z2 **running** → also `create_walk_run_workout`, as a single continuous
       interval: `run_seconds` = full session duration in seconds, `walk_seconds: 0`,
       `repeats: 1`, `hr_zone: "Z2"`, `warmup_min`/`cooldown_min: 0` (or non-zero if a
       distinct warmup/cooldown is wanted). **Do not use `create_z2_walk_workout` for
       running sessions** — despite the "Z2" name, it creates a workout tagged with sport
       `walking` on Garmin, not `running`, which then shows up wrong on the athlete's
       calendar/device. Reserve `create_z2_walk_workout` for genuine walking sessions
       (e.g. recovery walks).
     - Walking (e.g. recovery walk, Z2 walk) → `create_z2_walk_workout`
     - Strength sessions → `create_strength_workout(name, exercises)`, where each exercise is `{"name": ..., "sets": ..., "reps": ..., "rest_seconds": ...}`. For example:
       ```
       create_strength_workout(
         name="Lower Body Strength A",
         exercises=[
           {"name": "Barbell Back Squat", "sets": 4, "reps": 6, "rest_seconds": 120},
           {"name": "Romanian Deadlift", "sets": 3, "reps": 8, "rest_seconds": 90},
           {"name": "Walking Lunge", "sets": 3, "reps": 10, "rest_seconds": 60}
         ]
       )
       ```
       Exercise names don't need to match a fixed list — unrecognized names fall back to a generic category with the name preserved, so name exercises naturally.
     Each call returns `{status, workout_id, name, message}`. Keep the `workout_id` for step 6.
   - **Strava+Calendar (Degraded):** There's no builder schema — draft the session as **structured free text** for the calendar event's `description` (Google Calendar) or `body` (Outlook Calendar). Use this fixed template every time so the format stays consistent day to day (this is the structured artifact for this path — there is no separate "workout_id"):
     ```
     Session: <intent, e.g. "Z2 aerobic base run">
     Target: <duration and/or distance, e.g. "45 min, ~7-8 km">
     Effort: <target zone/pace/HR or RPE, e.g. "Z2, HR < 150, conversational pace">

     Structure:
     - Warm-up: <e.g. "10 min easy jog">
     - Main: <e.g. "30 min steady Z2" or interval breakdown, e.g. "6 x (3 min @ 5K pace / 2 min easy jog)">
     - Cool-down: <e.g. "5 min easy jog + stretch">

     Notes: <rationale/context for the athlete, e.g. "Easy day after yesterday's long ride — keep it conversational.">
     ```
     For strength sessions, replace the "Structure" block with an exercise list, one line per exercise: `- <Exercise name>: <sets> x <reps>, rest <rest_seconds>s`. Keep this draft text ready to pass as the event `description`/`body` in step 6.

6. **Schedule the workout on the active workout-calendar source.**
   Call `{{tool: schedule_workout}}`.

   - **Garmin (Full):** Call `schedule_workout(workout_id, date)` with today's date and the `workout_id` from step 5. (If generating a batch for the week, use `schedule_week([{date, workout_id}, ...])` instead — it's idempotent and skips days that already have a scheduled workout.) This call places the workout on the Garmin calendar; no separate "create event" step is needed.
   - **Strava+Calendar (Degraded):** Call `create-event(title, start, end, description/body)`:
     - `title`: a short human-readable name for the session (e.g. "Z2 Run — Aerobic Base")
     - `start`/`end`: today's date with a sensible time window for the session's target duration
     - `description` (Google Calendar) or `body` (Outlook Calendar): the structured free-text block drafted in step 5
     This call both creates and schedules the workout in one step, and returns an `event_id`.

   Keep whichever identifier you got back (`workout_id` from step 5 on Garmin, or `event_id` from this step on Calendar) — you'll write it into the `PlanNote` in step 7.

7. **Write the plan note.**
   Write `data/plan/<date>.json` (where `<date>` is today's date, `YYYY-MM-DD`) as a `PlanNote`:
   - `date`: today's date
   - `sport`: the sport chosen in step 4
   - `intent`: the short purpose of the session (e.g. "Z2 aerobic base")
   - `rationale`: free text explaining *why* this session today — tie it back to recent load, readiness (if available), and the goal's progression. Include any "backed off because..." or "progressing toward..." reasoning from step 4.
   - `goal_id`: the `id` of the goal (from `data/goals/goals.json`) this session primarily serves
   - `block_context`: a short note on where this sits in the broader training block/week (e.g. "week 3 of base phase, 2nd quality session this week")
   - `target_summary`: a short human-readable summary of the session's target (e.g. "45 min easy run, HR < 150" or "4x6 back squat @ moderate load")
   - `workout_ref`: the `workout_id` (Garmin) or `event_id` (Calendar) from step 6
   - `workout_source`: `"garmin"`, `"google_calendar"`, or `"outlook_calendar"` — matching the active workout-calendar source

   Write pretty-printed JSON (2-space indent) to `data/plan/<date>.json`, creating the `data/plan/` directory if it doesn't exist.

8. **Tell the athlete what's planned.**
   Summarize today's session in plain language — sport, intent, and the target/structure — and confirm it's been placed on their calendar/Garmin device.
   - **Garmin (Full) example:** "Today's session: Z2 aerobic base run, 45 min easy, keep HR under 150. It's on your Garmin calendar for today — should show up on your device."
   - **Strava+Calendar (Degraded) example:** "Today's session: Z2 aerobic base run, ~45 min / 7-8 km, conversational pace. I've added it to your calendar with the full structure in the event description."
