# Skills catalog

Each skill is a `SKILL.md` folder under [`skills/`](https://github.com/AchintyaX/Coach.ai/tree/main/skills), authored
once and installed into every harness via `install_skills(skills_dir, capabilities)` (see
[Architecture & principles](concepts/architecture.md)). Frontmatter (`description`, `when_to_use`, `allowed-tools`)
lets the harness decide when to invoke a skill; the body is the step-by-step procedure for the agent, with
`{{tool: ...}}` placeholders resolved to the active path's concrete tools at install time.

The **Path support** column reflects the [capability matrix](concepts/capabilities.md#skill-path-support):
**Full** = same experience either way, **Degraded** = installed but a step is reduced or skipped, **Unavailable** =
not installed at all.

## research-goal-plan

| | |
|---|---|
| **Trigger / when** | New or updated goal; on request ("help me plan for...") |
| **Inputs** | Athlete's stated goal, profile, native web research |
| **Tools (active path)** | `WebSearch`/`WebFetch` (Claude), `web search` (Codex), `Bash` — no source/MCP tools needed |
| **File outputs** | `goals/research/<goal-id>.md`, updates `goals/goals.json` |
| **Path support** | Garmin: **Full** · Strava+Cal: **Full** — capability-independent |

## setup-coach-personality

| | |
|---|---|
| **Trigger / when** | First run (onboarding), or on request ("set up my coach" / "refine my coach") |
| **Inputs** | `goals/goals.json`, fitness assessment from the active metrics source, native web research (coaching strategy + tone) |
| **Tools (active path)** | `WebSearch`/`WebFetch`/`Bash` + `{{tool: fitness_assessment}}` (Garmin `get_training_status`/`get_training_readiness`/`get_vo2max_trend`, or Strava `get-athlete-stats`/`get-activities`/`get-segment-prs`) + `store.py` |
| **File outputs** | `data/coach/personality.{md,json}`; on confirm, `install_personality()` updates `CLAUDE.md`/`AGENTS.md` |
| **Path support** | Garmin: **Full** · Strava+Cal: **Degraded** — assessment from activities/PRs, no readiness/HRV |

## generate-daily-workout

| | |
|---|---|
| **Trigger / when** | Daily, via `/loop` |
| **Inputs** | `goals.json`, recent training load from the active metrics source, today's readiness (if available) |
| **Tools (active path)** | `{{tool: recent_training_load}}` (Garmin `get_training_status`/`get_activities`/`get_training_load_trend`, or Strava `get-activities` + streams) → `{{tool: structured_workout_create}}` + `{{tool: schedule_workout}}` (Garmin `create_walk_run_workout`/`create_z2_walk_workout`/`create_strength_workout` → `schedule_workout`/`schedule_week`; or Calendar `create-event` with the session in `description`/`body`) |
| **File outputs** | `plan/<date>.json` (`workout_ref` + `workout_source`); workout written to the active workout-calendar source |
| **Path support** | Garmin: **Full** · Strava+Cal: **Degraded** — plans from recent activities only; free-text calendar event |

## readiness-check

| | |
|---|---|
| **Trigger / when** | Daily, via `/loop` (morning) |
| **Inputs** | Live metrics from the active metrics source (where `readiness`/`hrv`/`sleep`/`body_battery` capabilities exist) + a short subjective prompt |
| **Tools (active path)** | `get_training_readiness`, `get_morning_training_readiness`, `get_hrv_data`, `get_sleep_data`, `get_body_battery` — none of these capabilities exist on Strava+Calendar, so this part of the step is skipped entirely |
| **File outputs** | `logs/readiness/<date>.json` (`metrics_snapshot` populated on Garmin; omitted, not zero-filled, on Strava+Cal) |
| **Path support** | Garmin: **Full** · Strava+Cal: **Degraded** — subjective-only + yesterday's load |

## evaluate-training

| | |
|---|---|
| **Trigger / when** | On request, or automatically the day after a planned session |
| **Inputs** | `plan/<date>.json`, actual activity from the active metrics source, recent activities, goals |
| **Tools (active path)** | Garmin `get_activity` (incl. training effect + execution score), `get_activities`, `get_training_load_trend`; or Strava `get-activity-streams` (HR/power/pace), `get-activities`; `assemble.py` |
| **File outputs** | Coaching feedback to the athlete (no file write required, but may update `plan/<date>.json` notes) |
| **Path support** | Garmin: **Full** · Strava+Cal: **Degraded** — HR/power/pace only, no training effect or execution score |

## adjust-workout

| | |
|---|---|
| **Trigger / when** | On request ("my legs are wrecked", "move today to tomorrow") |
| **Inputs** | Today's scheduled workout from the active workout-calendar source, latest readiness (if available) |
| **Tools (active path)** | Garmin `get_scheduled_workouts` → `unschedule_workout` → `create_*` → `schedule_workout`; or Calendar `list-events`/`get-event` → `update-event` (rewrites `description`/`body`) |
| **File outputs** | Updated entry on the active workout-calendar source + revised `plan/<date>.json` (new `workout_ref` + `rationale`) |
| **Path support** | Garmin: **Full** · Strava+Cal: **Full** — modify-in-place is the hard requirement and holds on both paths |

## body-checkin

| | |
|---|---|
| **Trigger / when** | Remote / scheduled, via `/schedule` or `.claude/loop.md` |
| **Inputs** | Short conversational prompt ("how does your body feel?") |
| **Tools (active path)** | None required (optionally Garmin `get_body_battery` if the `body_battery` capability is present) |
| **File outputs** | Appends to `logs/readiness/<date>.json` (subjective-only update) |
| **Path support** | Garmin: **Full** · Strava+Cal: **Full** |

!!! note
    An earlier draft included a `log-workout` skill. It was removed once the active workout-calendar source was
    confirmed as the workout system-of-record — there is nothing left for it to log.
