---
name: research-goal-plan
description: Researches effective training approaches for an athlete's stated goal, writes a research note, and records or updates the goal in goals.json. Invoke when the athlete states a new or updated training goal, or asks for help planning toward one.
when_to_use: New or updated goal; on request ("help me plan for...")
capabilities: []
allowed-tools: [WebSearch, WebFetch, Bash]
---

# Research Goal & Plan

Use this procedure whenever the athlete states a new or updated training goal (e.g. "sub-22:00 5K by September", "deadlift 1.5×bodyweight", "run consistently 3×/week"), asks for help planning toward a goal, or when this skill is invoked as a sub-step of another skill or of onboarding because `data/goals/goals.json` is missing or empty. It works whether this is the start of the conversation or a sub-invocation partway through a larger flow — don't assume any prior steps have or haven't happened; check the filesystem.

## 1. Identify the goal(s) and sport(s)

- Look at the recent conversation for a stated goal — an event target (e.g. "sub-22:00 5K by September"), a metric target (e.g. "deadlift 1.5×bodyweight"), or a habit target (e.g. "run 3×/week consistently").
- If the goal is vague or missing, ask the athlete one or two concise clarifying questions to pin down:
  - The sport/activity (running, cycling, strength training, triathlon, etc.)
  - The type of goal — `event` (a race or specific session by a date), `metric` (a measurable performance target), or `habit` (a consistency/frequency target)
  - A target date, if there is one (events and many metrics have one; habits often don't)
  - Any specific numbers (time, distance, weight, frequency)
- If the athlete describes multiple distinct goals in one go, plan to repeat steps 3-5 for each goal separately — each gets its own research file and its own `Goal` entry.

## 2. Read the athlete's profile for context

Run:
```bash
cat data/athlete/profile.json
```

If the file exists, use it to ground the research — note equipment available, constraints, injuries, units (metric/imperial), and any other context that should shape the training approach (e.g. "no access to a pool", "history of knee issues", "only 3 days/week available"). If the file doesn't exist (e.g. very early in onboarding before `profile.json` has been created), proceed without it — don't block on this.

## 3. Conduct web research

For each goal identified in step 1, use `WebSearch`/`WebFetch` to research effective training approaches for that goal and sport. Aim to cover:

- Typical periodization/phasing appropriate for the goal and the time available until the target date (e.g. base-build-peak-taper for an event, progressive overload blocks for a strength metric, habit-formation tactics for a consistency goal)
- Key session types that should appear in a weekly structure (e.g. easy runs, intervals, tempo, long run, strength sessions, rest days)
- A realistic weekly structure / training frequency for someone at the athlete's apparent level
- Whether the stated target date is realistic given typical timelines for this kind of improvement, and what milestones along the way look like
- Any constraints from the athlete's profile (step 2) that should shape the approach (equipment, injuries, time availability)

Run enough searches to triangulate — don't rely on a single source. Note the URLs of the sources you found useful; you'll cite them in the research note.

## 4. Write the research note

For each goal, write a Markdown research note to `data/goals/research/<goal-id>.md` (create the `data/goals/research/` directory if it doesn't exist). Use a stable, slug-like `<goal-id>` derived from the goal (e.g. `goal-5k-sub22`, `goal-deadlift-1.5bw`, `goal-run-3x-week`) — this same id will be used in `goals.json` in step 5.

Structure the note as follows:

```markdown
# Research: <goal title>

## Goal summary
- Sport: <sport>
- Type: event | metric | habit
- Target: <the specific target, e.g. "5K in under 22:00">
- Target date: <YYYY-MM-DD or "none">

## Approach summary
<2-4 sentences summarizing the recommended overall approach for this goal,
given the athlete's profile and the time available.>

## Key principles
- <bullet list of the core training principles relevant to this goal>

## Suggested weekly structure
<A short weekly skeleton — e.g. a table or bullet list of session types per
week, with rough frequency/intensity guidance. Keep this as a flexible
skeleton, not a rigid prescribed plan — generate-daily-workout will fill in
specifics day by day.>

## Timeline & milestones
<Notes on whether the target date is realistic, and any suggested
intermediate milestones.>

## Constraints considered
<Notes on how the athlete's equipment/injuries/availability (from
profile.json, if present) shaped this research — or "No profile.json found;
no specific constraints considered" if it wasn't available.>

## Sources
- <URL 1>
- <URL 2>
- ...
```

Create the directory and write the file, e.g.:
```bash
mkdir -p data/goals/research
```
Then write the markdown content to `data/goals/research/<goal-id>.md`.

## 5. Create or update the goal in goals.json

Read the existing `data/goals/goals.json` if it exists:
```bash
mkdir -p data/goals
cat data/goals/goals.json 2>/dev/null || echo "[]"
```

`goals.json` holds a JSON list of `Goal` objects with exactly these fields (per the storage schema):

| Field | Type | Notes |
|---|---|---|
| `id` | string | Stable, slug-like id matching the research file, e.g. `goal-5k-sub22` |
| `title` | string | Short human-readable title, e.g. "Sub-22:00 5K" |
| `sport` | string | e.g. "running", "strength", "cycling" |
| `goal_type` | string | One of `event`, `metric`, or `habit` |
| `target_date` | string \| null | ISO date `YYYY-MM-DD`, or `null` if not applicable |
| `target_metrics` | object | Free-form key/value targets relevant to the goal, e.g. `{"distance_km": 5, "time_minutes": 22}` or `{"weight_multiple_of_bodyweight": 1.5}` or `{"sessions_per_week": 3}` |
| `priority` | string | e.g. `"high"`, `"medium"`, `"low"` — ask the athlete if unclear, default to `"medium"` |
| `status` | string | `"active"` for a new goal; preserve existing status when updating |
| `created` | string | ISO date the goal was first recorded; preserve on update |
| `notes` | string | Free-text notes — anything useful from the conversation that doesn't fit other fields |
| `research_file` | string | Path to the research note from step 4, e.g. `data/goals/research/goal-5k-sub22.md` |

For each goal from step 1:
- If a `Goal` with the same `id` already exists in `goals.json`, update it in place (preserve `created`, merge/update other fields as appropriate based on the new conversation).
- Otherwise, append a new `Goal` object with all fields populated, `status: "active"`, and `created` set to today's date (ISO format).

Write the updated list back to `data/goals/goals.json` as pretty-printed JSON (2-space indent).

## 6. Summarize back to the athlete

For each goal processed, tell the athlete:
- The goal as recorded (title, sport, type, target date, target metrics)
- A short summary of the research findings — the recommended approach, key principles, and the suggested weekly structure
- Where the full research note was saved (`data/goals/research/<goal-id>.md`)
- That the goal has been recorded in `data/goals/goals.json` for future planning

If this skill was invoked as a sub-step of another flow (e.g. `setup-coach-personality` or onboarding), keep the summary concise and hand control back to that flow rather than ending the conversation.
