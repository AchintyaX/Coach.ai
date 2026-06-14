# Development & testing

## Repository structure

Everything the installer and skills need lives in two top-level trees: `coach/` (the Python installer/configurator
package) and `skills/` (shared, harness-agnostic skill definitions). `data/` is created on first run and gitignored.

```text
coach/                          # Python package (installer + sources)
├── __init__.py
├── cli.py                      # `coach setup`, `coach setup --source <name>`, `coach install --harness ...`
├── harness/
│   ├── base.py                 # BaseHarness ABC
│   ├── claude.py               # ClaudeHarness
│   └── codex.py                # CodexHarness
├── sources/
│   ├── registry.py             # SOURCES registry (garmin/strava/google_calendar/outlook_calendar functional; rest scaffolded)
│   ├── base.py                 # SourceSpec dataclass + CAPABILITIES vocabulary constant
│   ├── garmin.py                # Garmin source (Taxuspt/garmin_mcp) — metrics + workout_calendar
│   ├── strava.py                # Strava source (reuses scripts/setup_auth.py + strava_server.py) — metrics only
│   ├── google_calendar.py        # Google Calendar source (nspady/google-calendar-mcp) — workout_calendar
│   └── outlook_calendar.py       # Outlook Calendar source (softeria/ms-365-mcp-server) — workout_calendar
├── storage/
│   ├── schema.py                # Goal / PlanNote / ReadinessCheckin Pydantic models
│   └── store.py                  # file-based read/write helpers over data/ tree (+ personality)
├── analysis/
│   └── assemble.py               # context assembler → agent-friendly payload (NO scoring/verdicts)
├── scheduling.py                  # parse_time_of_day/to_cron + local-only writers for Claude/Codex/launchd
└── prompts/
    └── coach_personality.md       # base coach persona seed

skills/                          # shared SKILL.md folders, authored once, installed to each harness
├── setup-coach-personality/SKILL.md  # one skill, two modes — setup + refine
├── research-goal-plan/SKILL.md
├── evaluate-training/SKILL.md
├── generate-daily-workout/SKILL.md
├── readiness-check/SKILL.md
├── adjust-workout/SKILL.md
└── body-checkin/SKILL.md

data/                            # local store (gitignored), created on first run
├── athlete/profile.json
├── coach/{personality.md, personality.json}
├── goals/{goals.json, research/*.md}
├── plan/<YYYY-MM-DD>.json
└── logs/readiness/<YYYY-MM-DD>.json

strava/                           # Strava metrics-source assets
├── strava_server.py
├── strava_client.py
├── format_workout_file.py
└── (tools/get_*.py, explore_segments.py, get_route.py, export_route_*.py)

scripts/
└── setup_auth.py                  # Strava OAuth CLI flow

tests/                             # schema, store, assemble, registry, harness installers
├── test_schema.py
├── test_store.py
├── test_assemble.py
├── test_registry.py
└── test_harness.py

pyproject.toml                     # deps + `coach` console entry-point
```

## Running the tests

```bash
uv sync
uv run pytest -q
```

## Functional testing strategy

Most of Coach AI's "logic" lives in `SKILL.md` and `CLAUDE.md`/`AGENTS.md` — instructions an LLM reads, not code
whose *reasoning* can be unit-tested. The strategy below tests everything that *is* code (schema, store, capability
resolution, harness installers, scheduling, `assemble.py`) thoroughly and automatically, and treats agent reasoning
as something verified structurally — did the right files get written, the right tools get called? — plus a manual
walkthrough per milestone.

### Four layers

| Layer | What's tested | How | Runs |
|---|---|---|---|
| **1. Unit** | Pydantic schema round-trips, `store.py` CRUD, `to_cron`/`parse_time_of_day`, capability-set resolution | plain `pytest`, temp dirs, no network/MCP | every commit |
| **2. Functional (fixture-driven)** | `install_skills()` renders the right `SKILL.md` per path; harness writers produce correct `.mcp.json`/`CLAUDE.md`/`config.toml`; `assemble.py` normalizes recorded MCP responses into the right shape (incl. fields omitted on Strava+Calendar); scheduling writers produce correct artifacts for a given time | `pytest` against recorded MCP-response fixtures (`tests/fixtures/`) and temp project dirs — asserts on **file contents**, never on agent output | every commit |
| **3. Integration (live MCP)** | real Garmin/Strava/Google/Outlook MCP servers launch, authenticate, and respond to one read tool each | opt-in `pytest` marker (`--run-integration`), needs real OAuth caches/credentials in the environment | manual, before a milestone ships |
| **4. Agent-in-the-loop** | a skill, run by a real agent in Claude Code/Codex, produces the expected `data/` writes, calendar mutations, and a coherent recommendation | the annotated examples and end-to-end diagram in [Daily workflow](workflow.md), run as a manual script — same steps as the installation verification checklist | manual, once per path × harness, before a milestone ships |

### Fixture library

One JSON fixture per MCP read tool actually consumed by a skill, captured once from real accounts with personal data
scrubbed, checked in, and reused across every Layer-2 test:

```text
tests/fixtures/
├── garmin/
│   ├── training_readiness.json    # get_training_readiness / get_morning_training_readiness
│   ├── hrv.json                    # get_hrv_data
│   ├── sleep.json                  # get_sleep_data
│   ├── body_battery.json           # get_body_battery
│   ├── activities.json             # get_activities / get_activity (incl. trainingEffect)
│   ├── training_status.json        # get_training_status / get_vo2max_trend
│   └── scheduled_workouts.json     # get_scheduled_workouts / get_workouts
├── strava/
│   ├── activities.json             # get-activities / get-activity-streams
│   ├── athlete_stats.json          # get-athlete-stats
│   └── segment_prs.json            # get-segment-prs / get-athlete-zones
├── google_calendar/
│   ├── list_events.json            # list-events
│   └── event.json                  # get-event / create-event / update-event
└── outlook_calendar/
    ├── list_events.json
    └── event.json
```

### The skill × path functional-test matrix

Layer-2 tests run every row below twice — once with Garmin fixtures, once with Strava+Calendar fixtures — and assert
the rendered `SKILL.md` and/or `assemble.py` output match the Full/Degraded/Unavailable behavior from
[Capabilities & paths](concepts/capabilities.md):

| Skill | Garmin-path assertion | Strava+Calendar-path assertion |
|---|---|---|
| `research-goal-plan` | capability-independent — rendered `SKILL.md` identical on both paths | same |
| `setup-coach-personality` | step 3 resolves to `get_training_status`/`get_training_readiness`/`get_vo2max_trend` | **Degraded** — step 3 resolves to `get-athlete-stats`/`get-activities`/`get-segment-prs` |
| `readiness-check` | `assemble.py` output includes a populated `metrics_snapshot` from the Garmin fixtures | **Degraded** — output has **no** `metrics_snapshot` key (omitted, not null/zero) |
| `generate-daily-workout` | `{{tool: structured_workout_create}}` resolves to `create_strength_workout`/`create_z2_walk_workout` → `schedule_workout` | **Degraded** — resolves to `create-event`; plan note has `workout_source: "google_calendar"` |
| `evaluate-training` | `assemble.py` includes `training_effect` from `get_activity` | **Degraded** — `training_effect` absent; HR/power streams present instead |
| `adjust-workout` | `{{tool: workout_modify}}` resolves to `unschedule_workout` → `create_*` → `schedule_workout` | **Full** — resolves to a single `update-event` call |
| `body-checkin` | capability-independent — **Full** on both paths | same |

### Harness parity

A separate parametrized test runs the **same resolved capability set** through `ClaudeHarness` and `CodexHarness` and
asserts structural equivalence — same set of skills installed, same `{{tool: ...}}` resolutions, same MCP server
entries (different file targets, per the [file-target matrix](concepts/architecture.md#file-target-matrix)). This is
what makes "Codex parity" in the installation verification checklist a quick re-run rather than a second
from-scratch verification.

!!! warning "Agent reasoning isn't unit-testable"
    Whether a recommendation is *good* coaching — "ease off because HRV is low and calves are sore" — depends on the
    LLM, the personality dials, and the moment. Layer 2 guarantees the agent *has the right data and tools* for each
    path; Layer 4 is the only place that confirms the agent *uses* them sensibly. Milestone 1 keeps Layer 4 manual; a
    future milestone could script it with an agent SDK driving a real session against fixture MCP servers.

### CI

```bash
# every commit — Layers 1+2, no credentials needed
uv run pytest

# before a milestone ships — adds Layer 3, needs real OAuth caches/env vars
uv run pytest --run-integration
```

## What survives the pivot

The pivot from the original LlamaIndex `ReActAgent` runtime is mostly subtractive, but several pieces of working code
moved forward, sometimes reshaped:

| Existing | Action |
|---|---|
| `tools/baseline_fitness.py` | Salvaged **only** normalization helpers (unit conversion, per-day/week grouping) into `coach/analysis/assemble.py`. **Dropped** VO2max estimation, TSS/CTL/ATL/TSB, strength-baseline, recovery-capacity, and the overall 0–100 fitness score — judgment moved to the agent. |
| `tools/user_profile_schema.py` | Reworked into `coach/storage/schema.py` as `Goal` / `PlanNote` / `ReadinessCheckin` — no monolithic profile, no embedded completed-workout list. |
| `tools/workout_db_tools.py` (TinyDB) | Dropped; replaced by `coach/storage/store.py` file-based helpers. |
| `prompts.py` (`FITNESS_COACH_SYSTEM_PROMPT`) | Seeded `coach/prompts/coach_personality.md` (stripped of ReAct scaffolding), then removed. |
| `scripts/setup_auth.py`, `strava_server.py`, `strava_client.py`, `tools/get_*.py`, `format_workout_file.py` | Kept, moved under `strava/` as `coach/sources/strava.py`'s assets — **functional** as the metrics source on the Strava + Calendar path. `format_workout_file.py` remains available for ad-hoc `.zwo` export but is outside the core skill flows. |
| `main.py`, `workout_db_server.py` | Removed — LlamaIndex runtime and TinyDB MCP server retired. |
| `pyproject.toml` | Dropped `llama-index*`, `mcp[cli]`, `tinydb`, `duckduckgo`, and `tavily` — research now runs on the harness's **native** `WebSearch`/`WebFetch`/`web search` tools, so no third-party search dependency remains. Added a `coach` console entry-point; kept `pydantic`, `requests`, `python-dotenv`. |
| `tests/` | Replaced with schema round-trip, store CRUD, `assemble.py`, registry, and harness-installer tests — run against **both** Garmin and Strava + Calendar fixtures. |

### New, not reused — MCP servers for the Strava + Calendar path

The Strava + Calendar path adds two or three small TypeScript/stdio MCP servers that have no Python codebase analog.
They are configuration, not code this repo maintains:

- [`r-huijts/strava-mcp`](https://github.com/r-huijts/strava-mcp) — optional alternative to the existing
  `strava_server.py` for the metrics role; either works against the same Strava API.
- [`nspady/google-calendar-mcp`](https://github.com/nspady/google-calendar-mcp) — workout-calendar role, lead
  binding. Requires a one-time `gcp-oauth.keys.json` desktop OAuth setup.
- [`softeria/ms-365-mcp-server`](https://github.com/softeria/ms-365-mcp-server) — workout-calendar role, second
  binding (Outlook). Requires an Azure app registration with `Calendars.ReadWrite`.

## Contributing

Issues and PRs are welcome — please [open an issue](https://github.com/AchintyaX/Coach.ai/issues) first for new
sources, skills, or larger changes so we can align on approach. Priority areas: new `SourceSpec`s (Apple Health,
Whoop, Polar, Oura), additional harness support beyond Claude Code/Codex, and refinements to the skill catalog.
