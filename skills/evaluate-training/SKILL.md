---
name: evaluate-training
description: Reviews how a planned session actually went — pulls the matching activity from the active metrics source, normalizes it alongside the plan, recent load, and goal via assemble.py, and reasons in conversation about execution quality, fatigue trend, and progress toward the goal. Invoke on request ("how did yesterday's run go?") or automatically the day after a planned session.
when_to_use: "On request, or automatically the day after a planned session"
capabilities: []
allowed-tools: ["{{tool: activity_detail}}", "{{tool: recent_load_context}}", Bash]
---

# Evaluate Training

Run this to review how a planned session actually went, compared to what was intended. Follow these steps in order.

1. **Read the plan.**
   Read `data/plan/<date>.json` for the date being evaluated (default: yesterday, or the most recent date with a `plan/<date>.json` that hasn't yet been evaluated, unless the athlete names a different date). From the `PlanNote`, note the `intent`, `target_summary`, `workout_ref`, and `workout_source` — this is what was *supposed* to happen.

2. **Pull the matching actual activity.**
   Call `{{tool: activity_detail}}` to find the activity that corresponds to the planned session (match by date and, where possible, activity type/duration).

   - **Garmin (Full):** Call `get_activities` to find the matching activity for the date, then `get_activity` for its full detail — this includes `training_effect` (aerobic/anaerobic) and `execution_score` (e.g. `"completed"`, `"completed_with_modifications"`).
   - **Strava (Degraded):** Call `get-activities` to find the matching activity for the date, then `get-activity-streams` for its HR/power/pace detail. There is no training-effect or execution-score field on this path — reason from HR/power/pace alone.

3. **Pull recent load context.**
   Call `{{tool: recent_load_context}}` for the last 7–14 days, so you can place this session in the context of recent fatigue/training load.

   - **Garmin (Full):** `get_training_load_trend`.
   - **Strava (Degraded):** `get-athlete-stats` and/or recent `get-activities` for the same window.

4. **Assemble the payload.**
   Run `coach/analysis/assemble.py` via Bash, passing the plan, the actual activity from step 2, the recent-load context from step 3, and the relevant `Goal` from `data/goals/goals.json` (and a `ReadinessCheckin` if `data/logs/readiness/<date>.json` exists for that date). It prints one compact JSON payload to stdout — this is your input for step 5.

   `assemble.py` does **no scoring and renders no verdicts**. It only normalizes units, pairs the plan with the matching activity, and trims the payload to what's actually available on the active path. The two shapes below are reference examples of what it can produce — your actual payload's exact fields depend on the active path, but the *shape* (and what's present vs. absent) will look like one of these.

   **Garmin (Full) — example payload:**
   ```json
   {
     "date": "2026-06-13",
     "goal": {"id": "goal-5k-sub22", "title": "Sub-22:00 5K", "target_date": "2026-09-01"},
     "plan": {"intent": "Z2 aerobic base", "target_summary": "45 min easy run, HR < 150", "workout_ref": "wko_88213", "workout_source": "garmin"},
     "actual": {
       "activity_id": "19283746", "duration_min": 47, "distance_km": 7.9,
       "avg_hr": 154, "training_effect": {"aerobic": 2.8, "anaerobic": 0.4},
       "execution_score": "completed"
     },
     "recent_load": [{"date": "2026-06-12", "type": "strength", "duration_min": 40}, ...],
     "readiness": {"training_readiness": 68, "hrv_status": "balanced", "sleep_score": 74}
   }
   ```

   **Strava + Calendar (Degraded) — example payload:**
   ```json
   {
     "date": "2026-06-13",
     "goal": {"id": "goal-5k-sub22", "title": "Sub-22:00 5K", "target_date": "2026-09-01"},
     "plan": {"intent": "Z2 aerobic base", "target_summary": "45 min easy, keep it conversational", "workout_ref": "evt_8a91f2", "workout_source": "google_calendar"},
     "actual": {
       "activity_id": "19283746", "duration_min": 47, "distance_km": 7.9,
       "avg_hr": 154, "avg_pace_min_km": 5.95
     },
     "recent_load": [{"date": "2026-06-12", "type": "strength", "duration_min": 40}, ...]
   }
   ```

   Note what's **absent, not zero-filled** on the Strava+Calendar path: no `training_effect`/`execution_score` keys in `actual` (Garmin-only capability), and no top-level `readiness` key (no readiness/HRV/sleep/body-battery capability on this path). Don't infer or fill in values for missing keys — just reason from what's there.

5. **Reason about the session — never compute a score.**
   Compare the `plan` against `actual`, using `recent_load` (and `readiness`, if present) for context. Think about:
   - **Execution quality** — did the athlete hit the intended target (duration, distance, HR zone, pace)? If they ran hotter/slower/shorter than planned, why might that be — carryover fatigue from a recent session, heat, terrain, etc.?
   - **Fatigue trend** — does this session, in light of `recent_load`, suggest the athlete is absorbing the training well or accumulating fatigue?
   - **Progress toward the goal** — does this session move the athlete toward `goal`, or flag something that needs adjusting in upcoming sessions?

   This reasoning **is** the evaluation. You must **never**:
   - Compute or state a numeric score, a 0–100 rating, or any derived metric like VO2max, TSS, CTL, ATL, or TSB.
   - Render a "good/bad/needs work" verdict computed by code.

   Instead, describe **what happened** and **what it means in context** — qualitative, narrative feedback grounded in the payload and the athlete's goal.

   - **Garmin (Full) example reasoning:** "Plan called for 45 min Z2 (HR < 150). Actual was 47 min, avg HR 154, aerobic training effect 2.8, marked 'completed'. Ran a touch hot — likely carryover fatigue from Tuesday's strength session in `recent_load`. Nothing concerning."
   - **Strava+Calendar (Degraded) example reasoning:** "Plan called for 45 min easy, conversational pace. Actual was 47 min, avg HR 154 — a bit above where an easy-pace HR would normally sit, similar story to the Garmin case but reasoned from HR/pace alone, without a training-effect figure to lean on."

6. **Deliver feedback, and optionally note the outcome.**
   - **Both paths:** Tell the athlete, in plain conversational language, how the session went relative to plan, what it suggests about their fatigue/recovery, and any implication for upcoming sessions (e.g. "keep tomorrow easy"). Keep it concise and specific — reference the actual numbers from the payload.
     - **Garmin (Full):** You can cite training effect and execution score directly, e.g. "...aerobic training effect 2.8, marked 'completed'..."
     - **Strava+Calendar (Degraded):** Cite HR/pace only, e.g. "...your average HR was 154 for 47 minutes, a bit above your easy-pace zone..." — the coaching conclusion can be the same as on Garmin, just reasoned from fewer inputs.
   - **Optional file note:** You may append your narrative summary to `data/plan/<date>.json` as an additive `outcome_notes` free-text field on the existing `PlanNote` (e.g. `"outcome_notes": "Ran a touch hot (avg HR 154 vs target <150) — likely carryover fatigue from Tuesday's strength session. Kept tomorrow easy."`). This is optional and additive — do not remove or restructure any existing fields on the `PlanNote`, and do not treat `outcome_notes` as a required field going forward.
