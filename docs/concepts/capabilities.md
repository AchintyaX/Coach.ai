# Capabilities & paths

Every data provider — Garmin, Strava, Google/Outlook Calendar, Apple Health, Whoop — is described by a single
`SourceSpec`. The registry is a plain dict; `coach setup --source <name>` looks up the spec, runs its auth steps, and
hands it to the active harness's `register_mcp_server()`. Two fields — `roles` and `capabilities` — are what make the
system **capability-aware** rather than just "connected / not connected".

```python title="coach/sources/base.py"
@dataclass
class SourceSpec:
    name: str                      # "garmin"
    mcp_server_name: str           # key used in mcp config, e.g. "garmin"
    command: str                   # "uvx"
    args: list[str]                # ["--python", "3.12", "--from", "git+...", "garmin-mcp"]
    env: dict[str, str]            # {"GARMIN_ENABLED_TOOLS": "get_training_readiness,..."}
    enabled_tools: list[str]       # used to render env + docs
    roles: set[str]                # subset of {"metrics", "workout_calendar"}
    capabilities: set[str]         # subset of CAPABILITIES (below)
    auth_steps: list[str]          # human-readable / runnable setup commands
    status: Literal["functional", "scaffold"]
```

## Capability vocabulary

<div class="pill-row" markdown>
`readiness` `hrv` `sleep` `body_battery` `stress` `training_load` `vo2max` `training_effect` `activity_streams`
`prs` `structured_workouts` `free_text_workouts`
</div>

A **path** is one `metrics` source + one `workout_calendar` source (Garmin can be both). The **active capability set
= the union** of the selected sources' `capabilities`, and it's what `install_skills()` and `assemble.py` key off of.

## Source registry

| Source | Status | Role(s) | Transport | Capabilities | Notes |
|---|---|---|---|---|---|
| `garmin` | :material-check-circle: functional | `metrics` + `workout_calendar` | stdio (`uvx` + `Taxuspt/garmin_mcp`) | `readiness, hrv, sleep, body_battery, stress, training_load, vo2max, training_effect, structured_workouts` | Full read/write — see [Garmin integration](../sources/garmin.md). One source covers both roles. |
| `strava` | :material-check-circle: functional | `metrics` | stdio (`r-huijts/strava-mcp` or existing `strava_server.py`) | `activity_streams, prs, training_load` (derived) | **Read-only** — Strava's API has no planned/structured-workout endpoint, so it never carries `workout_calendar`. |
| `google_calendar` | :material-check-circle: functional | `workout_calendar` | stdio (`nspady/google-calendar-mcp`) | `free_text_workouts` | **Lead** calendar binding — desktop OAuth + `gcp-oauth.keys.json`. |
| `outlook_calendar` | :material-check-circle: functional | `workout_calendar` | stdio (`softeria/ms-365-mcp-server`) | `free_text_workouts` | Second calendar binding — Azure app registration + MSAL device-code auth. |
| `apple_health` / `whoop` | :material-progress-wrench: scaffold | `metrics` | TBD | *future* | No public MCP yet; placeholder specs document the intended shape. Not part of M1. |

## Capabilities × source

| Capability | `garmin` | `strava` | `google_calendar` / `outlook_calendar` |
|---|---|---|---|
| `readiness` | ✓ | — | — |
| `hrv` | ✓ | — | — |
| `sleep` | ✓ | — | — |
| `body_battery` | ✓ | — | — |
| `stress` | ✓ | — | — |
| `training_load` | ✓ (Garmin-computed) | ✓ (derived from streams) | — |
| `vo2max` | ✓ | — | — |
| `training_effect` | ✓ (per-activity) | — | — |
| `activity_streams` (HR/power/pace) | ✓ | ✓ | — |
| `prs` (personal records) | ✓ | ✓ | — |
| `structured_workouts` (scheduled, builder-defined) | ✓ | — | — |
| `free_text_workouts` (calendar event description/body) | — | — | ✓ |

!!! warning "The two paths are not equal"
    `garmin` alone covers nine of twelve capabilities, including everything subjective-readiness and
    structured-workout related. `strava + google_calendar` covers three. This is a real trade-off, not a UI gap —
    the table below shows exactly which skills run **Full**, **Degraded**, or are **Unavailable** on each path, and
    the coach states this up front during onboarding (see [Daily workflow](../workflow.md)).

Because the shape is uniform, adding a real source later is: write its `SourceSpec` (including
`roles`/`capabilities`), implement `auth_steps`, flip `status` to `"functional"`, and run
`coach setup --source <name>` — no changes to `BaseHarness` or storage are required, and skills automatically adapt
via the capability set.

## Skill path support

The **Path support** column reflects the capability matrix above: **Full** = same experience either way,
**Degraded** = installed but a step is reduced or skipped, **Unavailable** = not installed at all.

| Skill | Garmin | Strava + Calendar | Why |
|---|---|---|---|
| `research-goal-plan` | Full | Full | Capability-independent — native web research only. |
| `setup-coach-personality` | Full | Degraded | Fitness assessment from activities/PRs/zones, no readiness/HRV. |
| `generate-daily-workout` | Full | Degraded | Plans from recent activities only (no training-status/readiness); writes a free-text calendar event instead of a structured workout. |
| `readiness-check` | Full | Degraded | Subjective-only check-in + yesterday's load; no objective `metrics_snapshot`. |
| `evaluate-training` | Full | Degraded | HR/power/pace only — no training effect or execution score. |
| `adjust-workout` | Full | Full | Modify-in-place is the hard requirement — holds on both paths (Garmin reschedule vs. calendar `update-event`). |
| `body-checkin` | Full | Full | Subjective only, capability-independent. |

See the full [Skills catalog](../skills.md) for trigger conditions, inputs, tools, and file outputs per skill.
