from coach.sources.base import SourceSpec
from coach.sources.registry import register

# Workout-calendar tools: a workout is a calendar event, with the session
# plan living in the event's body field. No delete-event tool is exposed —
# update-event is preferred for adjustments.
ENABLED_TOOLS = [
    "list-events",
    "get-event",
    "create-event",
    "update-event",
]

SOURCE_SPEC = SourceSpec(
    name="outlook_calendar",
    mcp_server_name="outlook_calendar",
    command="npx",
    args=["-y", "@softeria/ms-365-mcp-server"],
    env={
        "MS365_TENANT_ID": "<azure-tenant-id>",
        "MS365_CLIENT_ID": "<azure-client-id>",
    },
    enabled_tools=ENABLED_TOOLS,
    roles={"workout_calendar"},
    capabilities={"free_text_workouts"},
    auth_steps=[
        "Register an Azure AD app with the Calendars.ReadWrite delegated scope",
        "coach setup --source outlook_calendar --tenant-id <azure-tenant-id> --client-id <azure-client-id>  # runs an MSAL device-code flow and caches the token",
    ],
    status="functional",
)

register(SOURCE_SPEC)
