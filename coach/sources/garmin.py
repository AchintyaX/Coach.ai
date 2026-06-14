from coach.sources.base import SourceSpec
from coach.sources.registry import register

# Read tools: subjective readiness, recovery, and trend metrics.
_READ_TOOLS = [
    "get_training_readiness",
    "get_morning_training_readiness",
    "get_hrv_data",
    "get_sleep_data",
    "get_body_battery",
    "get_stress_summary",
    "get_steps_data",
    "get_activities",
    "get_activity",
    "get_training_status",
    "get_training_load_trend",
    "get_vo2max_trend",
    "get_stats",
]

# Write tools: workout creation and calendar scheduling.
_WRITE_TOOLS = [
    "create_walk_run_workout",
    "create_z2_walk_workout",
    "create_strength_workout",
    "schedule_workout",
    "schedule_week",
    "get_workouts",
    "get_scheduled_workouts",
    "unschedule_workout",
]

ENABLED_TOOLS = _READ_TOOLS + _WRITE_TOOLS

SOURCE_SPEC = SourceSpec(
    name="garmin",
    mcp_server_name="garmin",
    command="uvx",
    args=["--python", "3.12", "--from", "git+https://github.com/Taxuspt/garmin_mcp", "garmin-mcp"],
    env={"GARMIN_ENABLED_TOOLS": ",".join(ENABLED_TOOLS)},
    enabled_tools=ENABLED_TOOLS,
    roles={"metrics", "workout_calendar"},
    capabilities={
        "readiness",
        "hrv",
        "sleep",
        "body_battery",
        "stress",
        "training_load",
        "vo2max",
        "training_effect",
        "structured_workouts",
    },
    auth_steps=[
        "uvx --python 3.12 --from git+https://github.com/Taxuspt/garmin_mcp garmin-mcp-auth"
        "  # caches OAuth tokens at ~/.garminconnect (valid ~6 months)"
    ],
    status="functional",
)

register(SOURCE_SPEC)
