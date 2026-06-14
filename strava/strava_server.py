from fastmcp import FastMCP
from dotenv import load_dotenv
from strava.get_athlete_profile import get_athlete_profile
from strava.get_athlete_stats import get_athlete_stats_tool
from strava.get_activity_details import get_activity_details
from strava.get_recent_activities import get_recent_activities_tool
from strava.get_activity_streams import get_activity_streams, get_activity_streams_descriptions
from strava.export_route_gpx import export_route_gpx
from strava.export_route_tcx import export_route_tcx
from strava.get_athlete_zones import get_athlete_zones
from strava.explore_segments import explore_segments
from strava.get_activity_laps import get_activity_laps
from strava.get_route import get_route_tool


# Plain, importable tool implementations.
# These stay as regular functions (independent of `mcp`/FastMCP) so they can be
# imported and called directly, both in production and in tests.
def get_athlete_profile_tool():
    return get_athlete_profile()


def get_athlete_stats_mcp_tool(athlete_id: int):
    return get_athlete_stats_tool(athlete_id=athlete_id)


def get_recent_activity_mcp_tool(per_page: int = 100):
    return get_recent_activities_tool(per_page=per_page)


def get_activity_details_mcp_tool(activity_id: int):
    return get_activity_details(activity_id=activity_id)


def get_activity_streams_mcp_tool(activity_id: int, types: list = ["latlng", "altitude", "heartrate", "cadence", "watts"], resolution: str = 'medium', series_type: str = "distance"):
    return get_activity_streams(activity_id=activity_id, types=types)


def get_athlete_zones_mcp_tool():
    return get_athlete_zones()


def create_server() -> FastMCP:
    """Build (and configure) the Strava FastMCP server instance.

    Side effects (loading environment variables, constructing the FastMCP
    server, and registering tools) are encapsulated here so that the module
    can be imported without unconditionally executing them against a real
    FastMCP instance - tests can patch `FastMCP`/`load_dotenv` and call this
    function to get a fresh, fully-registered server.
    """
    load_dotenv()

    server = FastMCP(name="Strava Server")

    server.tool(
        name="get-athlete-profile",
        description="Fetches the profile information for the authenticated athlete, including their unique numeric ID needed for other tools like get-athlete-stats.",
    )(get_athlete_profile_tool)

    server.tool(
        name="get-athlete-stats",
        description="Fetches the activity statistics (recent, YTD, all-time) for a specific athlete using their ID. Requires the athlete_id obtained from the get-athlete-profile tool."
    )(get_athlete_stats_mcp_tool)

    server.tool(
        name="get-recent-activities",
        description="Fetches the most recent activities for the authenticated athlete. Returns a list of activities with details like distance, moving time, and type.",
    )(get_recent_activity_mcp_tool)

    server.tool(
        name="get-activity-details",
        description="Fetches detailed information about a specific activity using its ID. Returns data like distance, moving time, and type.",
    )(get_activity_details_mcp_tool)

    server.tool(
        name="get-activity-streams",
        description=get_activity_streams_descriptions
    )(get_activity_streams_mcp_tool)

    server.tool(
        name="get-athlete-zones",
        description="Fetches the athlete's heart rate and power zones. Useful for understanding training intensities and performance metrics.",
    )(get_athlete_zones_mcp_tool)

    return server


# Initialize FastMCP server (real instance, with the 6 tools registered) on import.
mcp = create_server()


if __name__ == "__main__":
    # Start the server
    print("🚀Starting server... ")

    # Debug Mode
    #  uv run mcp dev server.py

    # Production Mode
    # uv run server.py --server_type=sse

    mcp.run(transport="sse")
