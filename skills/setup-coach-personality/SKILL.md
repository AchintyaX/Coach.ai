---
name: setup-coach-personality
description: Builds (or refines) a personalized coaching persona — a training philosophy plus six "personality dials" — tailored to the athlete's goals, sport, fitness, and stated preferences, then registers it as the active coach personality.
when_to_use: First run (onboarding), or whenever the athlete asks to "set up my coach" / "refine my coach" / change how the coach talks to them.
capabilities: []
allowed-tools: [WebSearch, WebFetch, Bash, "{{tool: fitness_assessment}}"]
---

# setup-coach-personality

You are building (or refining) this athlete's personalized coaching persona: a training
philosophy and a set of six "personality dials" that shape how the coach talks to and
trains this athlete from now on. Run all 9 steps below, in order, every time this skill
is invoked — in **refine mode** (see the note before Step 1) you skip re-deriving the
research in Steps 2–5 unless the athlete wants a fresh pass, but you still walk through
presenting, adjusting, confirming, and re-registering.

Nothing is written to disk and nothing is installed until the athlete explicitly
approves in Step 8. Do not skip the confirm gate.

## Mode check — setup vs. refine

Before Step 1, check whether `data/coach/personality.json` exists and has
`"approved": true`.

- **No file, or `approved: false` → setup mode.** Proceed from Step 1 as a fresh build.
- **File exists with `approved: true` → refine mode.** Load and present the current
  `dials` and `philosophy` to the athlete first ("Here's your current coaching setup:
  ..."). Ask whether they want to tweak the existing setup or do a fresh pass. If they
  want a fresh pass, run Steps 2–5 again from scratch. Otherwise, skip straight to
  Step 6, using the existing dials/philosophy as the starting point for the
  "proposed" personality you present.

## Step 1 — Goals first (FILE)

Ensure `data/goals/goals.json` exists and contains at least one goal.

- If the file is missing, empty, or has zero goals, invoke the `research-goal-plan`
  skill first to capture the athlete's goal(s) and sport(s) — do not proceed with
  personalization until at least one goal exists.
- Once goals exist, read them. You'll need each goal's sport and target for Steps 2–4.

## Step 2 — Research coaching strategy (AGENT)

For each distinct goal/sport in `data/goals/goals.json`, do native web research
(`WebSearch`/`WebFetch`/`web search`) on effective training approaches for that goal —
e.g. training plan structure, intensity distribution, periodization, common pitfalls at
the athlete's level.

For each goal, save a short summary (a few paragraphs, with links) alongside that
goal's research file at `data/goals/research/<goal-id>.md` (append a "Coaching strategy
research" section if the file already exists from `research-goal-plan`, otherwise
create it). Keep a running list of the URLs you used — you'll need them for
`research_refs` in Step 9.

## Step 3 — Fitness assessment (MCP)

Pull a fitness baseline via `{{tool: fitness_assessment}}` (**Garmin:**
`get_training_status`, `get_training_readiness`, `get_vo2max_trend`; **Strava:**
`get-athlete-stats`, `get-activities`, `get-segment-prs`) to locate where the athlete
currently stands.

- **Garmin (Full):** call `get_training_status`, `get_training_readiness`, and
  `get_vo2max_trend` to get current training status (e.g. "maintaining",
  "productive"), readiness trend, and VO2max trajectory over recent weeks.
- **Strava+Calendar (Degraded):** call `get-athlete-stats`, `get-activities`
  (recent training history/volume), and `get-segment-prs` to infer current fitness
  and recent load from activity history and PRs alone — there is no
  readiness/HRV signal on this path. Do not invent or zero-fill a readiness score;
  simply work without one.

## Step 4 — Draft a training philosophy (AGENT)

Synthesize the strategy research from Step 2 and the fitness assessment from Step 3
into a proposed training philosophy for this athlete — a 1-3 sentence statement of the
overall approach for the period ahead, e.g. "base-building emphasis through August,
polarized intensity distribution, strength 2x/week as support work; prioritize recovery
after hard sessions."

Ground this in what you found: if VO2max is flat and training status is "maintaining"
(Garmin), or recent activity volume looks plateaued (Strava), say so and let it justify
the proposed emphasis (e.g. more base-building before adding intensity).

## Step 5 — Research coach tone (AGENT)

Do native web research (`WebSearch`/`WebFetch`/`web search`) on what makes an effective
coach, specifically:

- **Self-Determination Theory (SDT)** — autonomy, competence, and relatedness as drivers
  of intrinsic motivation.
- **Motivational Interviewing / OARS** — Open questions, Affirmations, Reflective
  listening, Summaries, as a conversational style.
- **GROW** — Goal, Reality, Options, Will, as a coaching-conversation structure.
- What an effective coach must always understand about an athlete: their goals,
  constraints (time, life context), recovery state, injury history, and motivation
  drivers.

Use this research to inform your proposed settings for the six personality dials in
Step 6 — in general it supports defaults that lean autonomy-supportive and high
positive-reinforcement. Add any URLs you use to the running `research_refs` list from
Step 2.

## Step 6 — Present the proposed personality (USER)

Present to the athlete:

1. The proposed training philosophy from Step 4 (in refine-without-fresh-pass mode,
   this is the existing philosophy unless the athlete asked to revisit it).
2. The personality dials table below, each with your proposed setting and a one-line
   "why" grounded in Steps 2–5 (or, in refine mode, the athlete's existing settings,
   noting you're starting from what's currently registered).

### Personality dials

| Dial | Range | Default |
|---|---|---|
| **Push style** | directive ↔ autonomy-supportive | autonomy-supportive |
| **Training emphasis** | performance-push ↔ recovery-focused | balanced, recovery-aware |
| **Reasoning style** | data-driven ↔ intuitive | data-informed, plain-language |
| **Structure** | high-structure ↔ flexible | flexible within a weekly skeleton |
| **Feedback warmth** | corrective ↔ positive-reinforcement | high positive-reinforcement |
| **Conversation style** | telling ↔ questioning | questioning (OARS-style) |

Defaults lean autonomy-supportive and high positive-reinforcement per the SDT/MI
research in Step 5 — propose a setting for each dial (these defaults, or something
adjusted given the athlete's specific goals/fitness from Steps 3-4), with a short
rationale per dial. For example: "Conversation style: questioning (OARS-style) — since
the research supports asking rather than telling for sustained motivation, and I'll
use this to check in on how sessions feel before adjusting the plan."

End by inviting adjustments: "Want to adjust anything — more push, more recovery focus,
more structure, a different tone?"

## Step 7 — Athlete adds pointers (USER)

Wait for the athlete's response. They may give:

- Free-text pointers about how they want to be coached, e.g. "push me harder on
  weekends, but keep weekdays low-key — I'm busy on weekdays", "be recovery-first after
  a hard week", "I like data — show me the numbers".
- Explicit dial adjustments (any direction along any of the six dial ranges above).

Incorporate every pointer and adjustment into your working philosophy and dial
settings. If a free-text pointer doesn't map cleanly onto a dial, fold it into the
philosophy text instead (e.g. "weekday sessions stay short and easy; weekend long
run/tempo carries the bigger push") so it isn't lost. If anything is ambiguous, ask a
brief clarifying question before moving on.

## Step 8 — Confirm gate (AGENT)

Summarize the **final** personality — philosophy plus all six dial settings,
incorporating the athlete's pointers from Step 7 — and ask for explicit approval, e.g.
"Here's the final summary: [philosophy + dials]. Lock this in?"

**Nothing is registered until the athlete confirms.** If they ask for further changes,
loop back to Step 7. Only proceed to Step 9 once you have a clear "yes"/approval.

## Step 9 — Register (FILE)

Once approved:

1. Write `data/coach/personality.json` with this exact shape:

```json
{
  "dials": {
    "push_style": "autonomy-supportive",
    "training_emphasis": "recovery-focused",
    "reasoning_style": "data-informed",
    "structure": "flexible",
    "feedback_warmth": "high-positive",
    "conversation_style": "questioning"
  },
  "philosophy": "Base-building emphasis through August with a polarized intensity distribution; strength 2x/week as support work; prioritize recovery after hard sessions.",
  "research_refs": ["https://...", "https://..."],
  "approved": true,
  "last_updated": "2026-06-13"
}
```

   - `dials` values are the final settings from Step 8 (use the short token forms shown
     above, consistent with each dial's range, e.g. `push_style` is
     `"directive"`/`"autonomy-supportive"`/something between; `training_emphasis` is
     `"performance-push"`/`"recovery-focused"`/`"balanced, recovery-aware"`; etc. — pick
     the label that best matches the agreed setting).
   - `philosophy` is the final training philosophy text from Step 8.
   - `research_refs` is the deduplicated list of URLs gathered in Steps 2 and 5.
   - `approved` is `true`.
   - `last_updated` is today's date (`YYYY-MM-DD`).

2. Write `data/coach/personality.md` — a human-readable rendering combining the seed's
   generic operating guidance (`coach/prompts/coach_personality.md`) with this
   athlete's philosophy and dial settings (each dial plus its one-line "why" from
   Step 6/8), so the file reads as this athlete's complete coaching persona.

3. Call `install_personality()` to inject the personalized persona from
   `data/coach/personality.md` into the `<!-- coach:start -->`/`<!-- coach:end -->`
   block of `CLAUDE.md` and/or `AGENTS.md`, replacing the generic seed that was there
   before.

4. Confirm to the athlete that the setup is complete and that they can re-run
   `setup-coach-personality` ("refine my coach") any time to adjust it further.
