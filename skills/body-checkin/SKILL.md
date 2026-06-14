---
name: body-checkin
description: A short, warm conversational check-in on how the athlete's body feels right now — energy, soreness, fatigue, any flags — that appends a subjective-only update to today's ReadinessCheckin. Suitable as the entire prompt body for a remote or scheduled midday check-in.
when_to_use: "Remote / scheduled, via /schedule or a midday check-in automation; also usable on request"
capabilities: []
allowed-tools: ["{{tool: body_battery_optional}}"]
---

# Body Check-in

This is the lightest skill in the catalog — a brief, conversational pulse-check, not a full readiness assessment.
It's designed to work standalone as the entire prompt body for a scheduled/remote midday automation (Section 5.7),
or to be invoked on request any time during the day. Follow these steps in order.

1. **Open with a warm, brief prompt.**
   If `data/coach/personality.json` exists and `approved: true`, read its dials/tone (e.g. positive-reinforcement
   level, questioning/OARS style) and let them shape your phrasing. Otherwise, default to a supportive,
   open-ended, OARS-style question.

   Ask how the athlete's body feels right now — energy, soreness, any flags. For example:
   - "How's your body feeling this afternoon? Any soreness or fatigue I should know about?"
   - "Quick check-in — how are you holding up right now? Energy, soreness, anything nagging?"

   Keep it short. This is a check-in, not an interrogation.

2. **Optionally add a data point.**
   Call `{{tool: body_battery_optional}}` (Garmin only, only if the `body_battery` capability is present —
   `get_body_battery`). Use this purely to add color to the conversation, never as a requirement.

   - **Garmin, `body_battery` present:** Call `get_body_battery` for today and weave the result into the
     conversation naturally, e.g. "I see your body battery is at 42% right now — does that match how you're
     feeling?"
   - **Strava+Calendar (or `body_battery` absent):** No tool to call — proceed with the subjective
     conversation only. Do not mention body battery at all.

3. **FILE — Append the subjective response to today's readiness check-in.**
   Write to `data/logs/readiness/<date>.json` (where `<date>` is today's date, `YYYY-MM-DD`):

   - **If a `ReadinessCheckin` already exists for today** (e.g. written earlier by `readiness-check`):
     - Merge the athlete's response into the existing `subjective` fields — update `energy`, `soreness`, `mood`
       as appropriate based on what they just told you, and append a short note to `subjective.notes` giving the
       time-of-day context, e.g. `"midday check-in: legs feeling fresher after lunch, energy up from this
       morning"`.
     - Leave `metrics_snapshot` and `recommendation` as they were unless the new information meaningfully changes
       your guidance (see step 4) — if it does, you may append a brief addendum to `recommendation` rather than
       rewriting it.

   - **If no `ReadinessCheckin` exists for today yet:**
     - Create a new `ReadinessCheckin` with:
       - `date`: today's date
       - `subjective`: populated from this conversation — `{energy, soreness, mood, sleep_quality, notes}`. If
         `sleep_quality` wasn't discussed (it's a midday check-in, not a morning one), leave it as a short
         placeholder like `"not assessed (midday check-in)"` rather than guessing.
       - `metrics_snapshot`: leave minimal — populate only with the body-battery reading from step 2 if you got
         one (Garmin), otherwise omit the key entirely (do not zero-fill).
       - `recommendation`: a brief acknowledgement rather than a full plan-affecting recommendation, e.g. "Logged
         midday check-in — no changes to today's plan."

4. **Acknowledge and close the loop.**
   Briefly acknowledge what the athlete shared — this is a check-in, not a full readiness assessment or workout
   re-plan. A short, warm reflection is enough, e.g. "Got it, glad the legs are feeling better — thanks for the
   update."

   - **If something concerning comes up** (e.g. injury-level pain, sharp/localized pain, or a flag that suggests
     today's session should change), gently suggest the athlete consider running `adjust-workout` to revisit
     today's plan — don't attempt the re-plan yourself here.

## Note on scheduling

This skill is intentionally self-contained and lightweight enough to be the **entire prompt body** for a local
scheduled task or automation (Section 5.7) — e.g. "Run the `body-checkin` skill" as a midday entry, if the athlete
opts into a midday check during `coach setup --schedule`. No other context or setup is required for it to run.
