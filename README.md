# Coach AI

**Your coach, wherever your agent lives.**

Coach AI is not an app you run — it's a **portable coaching agent definition** that installs *into* agent harnesses
you already use (currently [Claude Code](https://docs.claude.com/en/docs/claude-code) and
[Codex CLI](https://github.com/openai/codex)). A small `coach` CLI configures a coach **personality**, a set of
**skills** (`SKILL.md` files), and live **MCP** connections to your fitness data. The harness's own reasoning,
memory, and scheduling (`/loop`, `/schedule`) do the rest.

📖 **[Full documentation](https://achintyax.github.io/Coach.ai/)** — architecture, capabilities, skills catalog,
source integrations, daily workflow, development & testing, and roadmap.

---

## Quickstart

Requires **Python 3.12+** and [`uv`](https://docs.astral.sh/uv/).

```bash
git clone https://github.com/AchintyaX/Coach.ai.git
cd Coach.ai
uv sync
```

Pick a path and authenticate its source(s) — see
[Installation](https://achintyax.github.io/Coach.ai/installation/) for the full one-time auth steps:

```bash
# Garmin path
coach setup --source garmin

# — or — Strava + Calendar path (pick one calendar)
coach setup --source strava
coach setup --source google_calendar   # or: coach setup --source outlook_calendar
```

Then install into your harness and (optionally) set up the daily loop:

```bash
coach install --harness claude   # or: codex, all
coach setup --schedule           # interactive — asks what time to run readiness-check + generate-daily-workout
```

Everything above is **idempotent** — re-run any step any time your sources, skills, or personality change. For what
each `coach` command writes and where, see
[Architecture & principles](https://achintyax.github.io/Coach.ai/concepts/architecture/) and
[Installation](https://achintyax.github.io/Coach.ai/installation/).

---

## Two functional paths

Coach AI ships **two functional paths** — a path is one **metrics** source plus one **workout-calendar** source
(Garmin covers both). The installer resolves your sources' combined capabilities and installs only the skills (and
tool resolutions) that capability set supports — nothing is faked when a capability is missing. See
[Capabilities & paths](https://achintyax.github.io/Coach.ai/concepts/capabilities/) for the full comparison.

- **Garmin** — full readiness/HRV/sleep/body-battery/training-load data, plus **structured workouts** pushed to and
  rescheduled on the Garmin calendar.
- **Strava + Google/Outlook Calendar** — Strava supplies activity streams and PRs; the calendar is the workout
  system-of-record, with each session written as a **free-text event**.

---

## Development & testing

```bash
uv sync
uv run pytest -q
```

See [Development & testing](https://achintyax.github.io/Coach.ai/development/) for the repository structure,
fixture-driven functional tests, and the full skill × path test matrix.

---

## Contributing

Issues and PRs are welcome — please [open an issue](https://github.com/AchintyaX/Coach.ai/issues) first for new
sources, skills, or larger changes so we can align on approach. Priority areas: new `SourceSpec`s (Apple Health,
Whoop, Polar, Oura), additional harness support beyond Claude Code/Codex, and refinements to the skill catalog.

## License

[MIT](./LICENSE)
