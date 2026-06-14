---
name: adjust-workout
description: Modifies today's scheduled workout in place when the athlete reports how they feel (fatigue, soreness, lack of time, schedule conflict). Reasons about an appropriate adjustment, rewrites the workout on the active workout-calendar source, and records the change and rationale in the plan file.
when_to_use: 'On request ("my legs are wrecked", "tight on time today", "move today to tomorrow")'
capabilities: []
allowed-tools: ["{{tool: find_scheduled_workout}}", "{{tool: modify_workout}}"]
---

# Adjust Workout

Run this whenever the athlete reports something that should change today's planned session — fatigue,
soreness, a time crunch, illness, or a request to move/swap a workout. Follow these steps in order.

1. **Find today's scheduled workout.**
   Call `{{tool: find_scheduled_workout}}` to locate today's session — both paths find the same thing.

   - **Garmin:** call `get_scheduled_workouts` for today's date to get the scheduled workout's id and details.
   - **Calendar (Google/Outlook):** call `list-events` for today, then `get-event` on the matching workout
     event to read its `description` (Google) or `body` (Outlook) for the planned session.

2. **Read context from file.**
   Read `data/plan/<date>.json` (today's `PlanNote`) for the intent/rationale behind today's session. If
   `data/logs/readiness/<date>.json` exists for today, read it too — it may already contain a recommendation
   relevant to the athlete's complaint.

3. **Decide the adjustment.**
   Read `data/goals/goals.json` so the adjustment stays consistent with the athlete's goals and current
   training block. Based on what the athlete told you, the planned session, and any readiness context, decide
   how to adjust today's workout — for example:
   - Reduce volume or intensity (e.g. swap a tempo run for a Z2 recovery run).
   - Swap the modality entirely (e.g. run → easy walk, or strength → mobility).
   - Move today's session to rest, and optionally reschedule the displaced session to another day later in
     the week (if you do this, you'll need a second pass of step 4 for that other date/event).
   - Adjust timing only (e.g. shorten the session to fit a tight schedule) without changing the modality.

   Tell the athlete your proposed adjustment and the reasoning behind it before making changes, in plain
   language — e.g. "Given yesterday's session and how your legs feel, I'll swap today to a 30-min Z2 recovery
   run and move the tempo session to Thursday."

4. **Apply the adjustment via `{{tool: modify_workout}}`.**
   - **Garmin:** this is multi-step —
     1. `unschedule_workout(scheduled_workout_id)` to remove today's existing scheduled workout.
     2. `create_*` (`create_walk_run_workout`, `create_z2_walk_workout`, or `create_strength_workout`,
        whichever matches the revised session) to build the new workout and obtain a `workout_id`.
     3. `schedule_workout(workout_id, date)` to place the revised session on today's date.
     If the original session is being moved to a different day rather than dropped, also call
     `schedule_workout(original_workout_id_or_new_workout_id, new_date)` for that day.
   - **Calendar (Google/Outlook):** this is a single call —
     `update-event(event_id, description/body=<revised plan>, start/end=<new time if changed>)`. Because
     there's no builder schema enforcing structure here (unlike Garmin's `create_*` tools), write the revised
     `description`/`body` as a clear, well-structured free-text plan — session name, duration/distance,
     target pace/HR or effort, and any notes — so the athlete (and any future read of this event) gets the
     same clarity a Garmin structured workout would provide. If the session is being moved to another day,
     make a second `update-event` call for that day's event (creating one with `create-event` first if it
     doesn't yet exist).

5. **Update the plan file.**
   Write the revised `PlanNote` to `data/plan/<date>.json`:
   - `workout_ref`: the new identifier for today's session —
     - **Garmin:** the new `workout_id` returned from `create_*` in step 4.
     - **Calendar:** unchanged (`update-event` modifies the existing event in place, so the `event_id` stays
       the same) — unless the workout moved to a different calendar/system, which shouldn't happen mid-adjustment.
   - `workout_source`: unchanged unless the workout moved to a different calendar/system (which shouldn't
     happen mid-adjustment).
   - `rationale`: a free-text entry explaining why the change was made — e.g. "swapped tempo for recovery run
     due to leg soreness + low HRV (58)".
   - Keep the rest of the `PlanNote` (`sport`, `intent`, `goal_id`, `block_context`, `target_summary`, etc.)
     consistent with the revised session — update `intent`/`target_summary` if the session itself changed.

   If a displaced session was rescheduled to another day, also update (or create) that day's
   `data/plan/<other-date>.json` with its own `workout_ref`/`workout_source`/`rationale`.

6. **Confirm with the athlete.**
   Tell the athlete what changed in plain language and confirm it's reflected on their calendar/device — e.g.
   "Done — today's calendar now shows a 30-min easy run, and Thursday has your tempo session. I've noted the
   reason in your plan file."
