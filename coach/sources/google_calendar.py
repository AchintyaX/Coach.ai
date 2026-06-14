from coach.sources.base import SourceSpec
from coach.sources.registry import register

# Workout-calendar tools: a workout is a calendar event, with the session
# plan (warm-up, intervals, target paces/HR, notes) living in the event's
# free-text description.
ENABLED_TOOLS = [
    "list-events",
    "get-event",
    "create-event",
    "update-event",
    "delete-event",
]

SOURCE_SPEC = SourceSpec(
    name="google_calendar",
    mcp_server_name="google_calendar",
    command="npx",
    args=["-y", "@nspady/google-calendar-mcp"],
    env={"GOOGLE_OAUTH_CREDENTIALS": "./gcp-oauth.keys.json"},
    enabled_tools=ENABLED_TOOLS,
    roles={"workout_calendar"},
    capabilities={"free_text_workouts"},
    auth_steps=[
        "Create an OAuth client of type 'Desktop app' in Google Cloud Console and download it as gcp-oauth.keys.json",
        "coach setup --source google_calendar --credentials ./gcp-oauth.keys.json  # runs a local browser consent flow once and caches the refresh token",
    ],
    status="functional",
)

register(SOURCE_SPEC)
