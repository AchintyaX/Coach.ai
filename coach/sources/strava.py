from coach.sources.base import SourceSpec
from coach.sources.registry import register

# Curated read-only tool allowlist (Section 6b).
ENABLED_TOOLS = [
    "get-activities",
    "get-activity-streams",
    "get-athlete-stats",
    "get-segment-prs",
    "get-athlete-zones",
]

SOURCE_SPEC = SourceSpec(
    name="strava",
    mcp_server_name="strava",
    command="uv",
    args=["run", "python", "strava/strava_server.py"],
    env={"STRAVA_ENABLED_TOOLS": ",".join(ENABLED_TOOLS)},
    enabled_tools=ENABLED_TOOLS,
    # Read-only by design: Strava's API has no planned/structured-workout
    # endpoint, so it never carries "workout_calendar" (Section 6b).
    roles={"metrics"},
    capabilities={
        "activity_streams",
        "prs",
        "training_load",  # derived from streams, not Strava-computed
    },
    auth_steps=[
        "uv run python scripts/setup_auth.py  # reuses existing Strava OAuth flow"
    ],
    status="functional",
)

register(SOURCE_SPEC)
