---
name: readiness-check
description: Runs the athlete's morning readiness check-in — combines overnight recovery metrics (where available) with a short subjective prompt, reasons about today's training implications, and writes a ReadinessCheckin record. Invoke this daily during the morning loop, before generate-daily-workout.
when_to_use: "Daily, via /loop (morning)"
capabilities: []
allowed-tools: ["{{tool: readiness_metrics}}"]
---

# Readiness Check

Run this once each morning, before `generate-daily-workout`. Follow these steps in order.

1. **Pull overnight metrics.**
   Call `{{tool: readiness_metrics}}` for today (Garmin: `get_training_readiness`, `get_morning_training_readiness`, `get_hrv_data`, `get_sleep_data`, `get_body_battery`; Strava+Calendar: **this capability does not exist — skip this step entirely**, do not call any tool).

   - **Garmin (Full):** Call all four/five tools and note the results — training readiness score, HRV status, sleep score/stages, and body battery level. These will inform your reasoning in step 3.
   - **Strava+Calendar (Degraded):** Skip this step entirely. Do not attempt to call any readiness/HRV/sleep/body-battery tool — none exist on this path. Move straight to step 2.

2. **Ask the athlete a short subjective check-in.**
   Both paths: ask the athlete a brief, conversational question covering:
   - Energy level
   - Soreness (and where, if relevant)
   - Mood
   - Sleep quality
   - Anything else they want to note (free-text)

   - **Garmin (Full):** You can frame this as a follow-up to the metrics you just pulled, e.g. "Training readiness is 58 (moderate), HRV is unbalanced, sleep score 61 — how are you feeling? Energy, soreness, mood, sleep quality?"
   - **Strava+Calendar (Degraded):** Lead with the fact that you have no overnight metrics on this setup, e.g. "No overnight metrics on this setup — how's your body feeling this morning? Energy, soreness, mood, sleep quality?"

   Capture the athlete's answers as free text/short values for `subjective.energy`, `subjective.soreness`, `subjective.mood`, `subjective.sleep_quality`, and `subjective.notes`.

3. **Reason about today's training implications.**
   - **Garmin (Full):** Combine the overnight metrics from step 1 with the subjective answers from step 2. Read `data/goals/goals.json` and the latest `data/plan/*.json` to understand current goals and what's planned. Reason about whether today's planned session still makes sense given readiness + how the athlete feels — e.g. low HRV plus reported soreness might mean easing off a planned tempo run in favor of a Z2 recovery session or rest.
   - **Strava+Calendar (Degraded):** No overnight metrics are available. Reason from the subjective answers alone plus yesterday's training load (recent activities from the active metrics source) — e.g. a long ride yesterday plus "flat" energy today is expected and doesn't necessarily warrant backing off further.

4. **Write the readiness check-in to file.**
   Write `data/logs/readiness/<date>.json` (where `<date>` is today's date, `YYYY-MM-DD`) as a `ReadinessCheckin`:
   - `date`: today's date
   - `subjective`: always populated — `{energy, soreness, mood, sleep_quality, notes}` from step 2
   - `metrics_snapshot`:
     - **Garmin (Full):** populate `{training_readiness, hrv, sleep, body_battery}` from step 1
     - **Strava+Calendar (Degraded):** **omit this key entirely** — do not write it as `null`, an empty object, or zero-filled values. The key must be absent from the JSON.
   - `recommendation`: your free-text guidance for today's training, from step 3

5. **Surface the recommendation conversationally.**
   Tell the athlete your recommendation in plain language, tying it back to what they told you and (on Garmin) the metrics you pulled.
   - **Garmin (Full) example:** "Given the low HRV and sore calves, I'd ease off the planned tempo run today — let's shift to a Z2 recovery run or rest, and reassess tomorrow. I've logged this check-in."
   - **Strava+Calendar (Degraded) example:** "Yesterday was a longer ride, so some flatness tracks. Nothing in your recent load suggests backing off further — let's keep today's easy run as planned. I've logged this check-in."
