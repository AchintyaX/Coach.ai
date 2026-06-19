# Installation

Requires **Python 3.12+** and [`uv`](https://docs.astral.sh/uv/).

```bash
git clone https://github.com/AchintyaX/Coach.ai.git
cd Coach.ai
uv sync
```

Everything below is **idempotent** — re-run any step any time your sources, skills, or personality change.

## 1. Authenticate a data source (one-time)

=== "Garmin path"

    Caches OAuth tokens at `~/.garminconnect` (valid ~6 months):

    ```bash
    uvx --python 3.12 --from git+https://github.com/Taxuspt/garmin_mcp garmin-mcp-auth
    ```

=== "Strava + Calendar path"

    ```bash
    # Strava — existing OAuth helper script
    uv run python scripts/setup_auth.py

    # Google Calendar — desktop OAuth via gcp-oauth.keys.json from Google Cloud Console
    coach setup --source google_calendar --credentials ./gcp-oauth.keys.json

    # — or — Outlook Calendar: Azure app registration + MSAL device-code flow
    coach setup --source outlook_calendar --tenant-id <azure-tenant-id> --client-id <azure-client-id>
    ```

## 2. Configure sources

=== "Garmin path"

    ```bash
    coach setup --source garmin
    ```

=== "Strava + Calendar path"

    ```bash
    coach setup --source strava
    coach setup --source google_calendar   # or: coach setup --source outlook_calendar
    ```

Each `coach setup --source <name>` registers that source's MCP server and records its `roles`/`capabilities` so
`coach install` can resolve the active capability set from their union — see
[Capabilities & paths](concepts/capabilities.md).

## 3. Install into your harness

```bash
coach install --harness claude   # Claude Code only
coach install --harness codex    # Codex CLI only
coach install --harness all      # Both
```

This writes the personality, registers MCP servers, and installs only the skills your configured sources support —
each rendered with that path's concrete tools (see [What gets written where](#what-gets-written-where) below).

## 4. Set up the daily loop (optional)

```bash
coach setup --schedule                  # interactive — asks what time to run
coach setup --schedule-time "7:00 AM"   # non-interactive
```

This writes **local-only** scheduling artifacts (your credentials never leave the machine):

- **Claude Code** →
  - `~/.claude/scheduled-tasks/coach-daily-loop/SKILL.md` — minimal prompt file
    (frontmatter: `name` + `description` only; no `schedule`/`mode` fields).
  - `~/Library/Application Support/Claude/claude-code-sessions/…/scheduled-tasks.json` —
    the cron entry Desktop actually executes, upserted with `permissionMode: "auto"` and
    `approvedPermissions` pre-seeded from `.mcp.json` so unattended Garmin tool calls
    don't stall. Requires Claude Desktop to be running; falls back to SKILL.md-only with
    instructions if no Desktop schedule file exists yet.
- **Codex Desktop** → `./.codex/automations/daily-coach-loop.toml`
- **Codex CLI without Desktop** → a launchd plist (macOS) / crontab entry running `codex exec --full-auto "..."`

!!! warning "Local-only by design"
    A run is skipped if this machine is asleep or Claude Desktop isn't open at the scheduled
    time — it simply runs at the next opportunity. The cloud/remote scheduling modes offered
    by Claude Code and Codex CLI are not used, because that sandbox doesn't have this
    machine's Garmin/Strava/calendar OAuth caches.

!!! tip "Restart Desktop after first run"
    If the new `coach-daily-loop` schedule doesn't appear under **Routines** immediately,
    restart Claude Desktop — it reads `scheduled-tasks.json` at startup.

## Verifying the install

- In Claude Code, run `/mcp` and confirm your source(s) are listed and connected.
- Confirm `WebSearch`/`WebFetch` (Claude) or `web_search` (Codex) are permitted — these power `research-goal-plan`
  and `setup-coach-personality`, no third-party search dependency required.
- Run `/setup-coach-personality` to walk through the dial-based personality setup (confirm-gated — nothing is
  written to `CLAUDE.md`/`AGENTS.md` until you approve).
- Run `/readiness-check` and `/generate-daily-workout` and confirm `data/logs/readiness/<today>.json` and
  `data/plan/<today>.json` are written, and a workout appears on your active workout-calendar source.

---

## What gets written where

| | Claude Code | Codex CLI |
|---|---|---|
| Personality | `./CLAUDE.md` (marked `<!-- coach:start -->`/`<!-- coach:end -->` block) | `./AGENTS.md` (same marker block) |
| MCP servers | `./.mcp.json` → `mcpServers.<name>` | `~/.codex/config.toml` → `[mcp_servers.<name>]` |
| Skills | `./.claude/skills/<skill>/SKILL.md` | `./.codex/skills/<skill>/SKILL.md` + `[skills.config.N]` |
| Web research tools | `./.claude/settings.json` → `permissions.allow` incl. `WebSearch`, `WebFetch`, `Bash` | `~/.codex/config.toml` → `[tools]` `web_search = true` (Bash/exec is native) |
| Daily loop | `~/.claude/scheduled-tasks/coach-daily-loop/SKILL.md` + Desktop's `scheduled-tasks.json` (cron + `permissionMode:auto`) | `./.codex/automations/daily-coach-loop.toml` or launchd/cron |

Local data — never committed, created on first run:

```text
data/
├── athlete/profile.json              # name, units, equipment, constraints, injuries
├── coach/
│   ├── personality.md                # rendered persona injected into CLAUDE.md / AGENTS.md
│   └── personality.json              # dials, philosophy, research refs, approved, last_updated
├── goals/
│   ├── goals.json                    # list of Goal objects
│   └── research/<goal-id>.md         # agent-written research backing each goal
├── plan/<YYYY-MM-DD>.json            # PlanNote — thin coaching layer, not an executable workout
└── logs/readiness/<YYYY-MM-DD>.json  # ReadinessCheckin — subjective + (capability-dependent) metrics snapshot
```

### Generated config — Claude Code

`./.mcp.json` (Garmin path):

```json
{
  "mcpServers": {
    "garmin": {
      "command": "uvx",
      "args": ["--python", "3.12", "--from", "git+https://github.com/Taxuspt/garmin_mcp", "garmin-mcp"],
      "env": {
        "GARMIN_ENABLED_TOOLS": "get_training_readiness,get_morning_training_readiness,get_hrv_data,get_sleep_data,get_body_battery,get_stress_summary,get_steps_data,get_activities,get_activity,get_training_status,get_training_load_trend,get_vo2max_trend,get_stats,create_walk_run_workout,create_z2_walk_workout,create_strength_workout,schedule_workout,schedule_week,get_workouts,get_scheduled_workouts,unschedule_workout"
      }
    }
  }
}
```

`./.claude/settings.json` (excerpt):

```json
{
  "enableAllProjectMcpServers": true,
  "permissions": {
    "allow": [
      "Read(./data/**)", "Write(./data/**)",
      "WebSearch", "WebFetch", "Bash"
    ]
  }
}
```

### Generated config — Codex CLI

`~/.codex/config.toml` (excerpt):

```toml
[tools]
web_search = true   # native web search for research-goal-plan / setup-coach-personality; Bash/exec is native

[mcp_servers.garmin]
command = "uvx"
args = ["--python", "3.12", "--from", "git+https://github.com/Taxuspt/garmin_mcp", "garmin-mcp"]

[mcp_servers.garmin.env]
GARMIN_ENABLED_TOOLS = "get_training_readiness,get_morning_training_readiness,get_hrv_data,..."

[skills.config.0]
path = "./.codex/skills/setup-coach-personality"
enabled = true

# ... one [skills.config.N] entry per skill the active capability set supports
```
