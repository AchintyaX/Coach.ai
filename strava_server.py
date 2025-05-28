from mcp.server.fastmcp import FastMCP
from dotenv import load_dotenv
from tools.get_athlete_profile import get_athlete_profile
from tools.get_athlete_stats import get_athlete_stats_tool
from tools.get_activity_details import get_activity_details
from tools.get_recent_activities import get_recent_activities_tool
from tools.get_activity_streams import get_activity_streams, get_activity_streams_descriptions
from tools.export_route_gpx import export_route_gpx
from tools.export_route_tcx import export_route_tcx
from tools.get_athlete_zones import get_athlete_zones
from tools.explore_segments import explore_segments
from tools.get_activity_laps import get_activity_laps
from tools.get_route import get_route_tool

load_dotenv()
# Initialize FastMCP server

mcp = FastMCP(name="Strava Server", version="1.0.0")

# Register tools
@mcp.tool(
    name="get-athlete-profile",
    description="Fetches the profile information for the authenticated athlete, including their unique numeric ID needed for other tools like get-athlete-stats.",
)
def get_athlete_profile_tool():
    return get_athlete_profile()


@mcp.tool(
    name="get-athlete-stats",
    description="Fetches the activity statistics (recent, YTD, all-time) for a specific athlete using their ID. Requires the athlete_id obtained from the get-athlete-profile tool."
)
def get_athlete_stats_tool(athlete_id: int):
    return get_athlete_stats_tool(athlete_id=athlete_id)


@mcp.tool(
    name="get-recent-activities",
    description="Fetches the most recent activities for the authenticated athlete. Returns a list of activities with details like distance, moving time, and type.",
)
def get_recent_activity_tool(per_page: int = 100):
    return get_recent_activities_tool(per_page=per_page)


@mcp.tool(
    name="get-activity-details",
    description="Fetches detailed information about a specific activity using its ID. Returns data like distance, moving time, and type.",
)
def get_activity_details_tool(activity_id: int):
    return get_activity_details(activity_id=activity_id)


@mcp.tool(
    name="get-activity-streams",
    description=get_activity_streams_descriptions
)
def get_activity_streams_tool(activity_id: int, types: str = ["latlng","altitude","heartrate","cadence","watts"], resolution: str = 'medium', series_type: str = "distance"):
    return get_activity_streams(activity_id=activity_id, types=types)


@mcp.tool(
    name="get-athlete-zones",
    description="Fetches the athlete's heart rate and power zones. Useful for understanding training intensities and performance metrics.",
)
def get_athlete_zones_tool():
    return get_athlete_zones()



if __name__ == "__main__":
    # Start the server
    print("🚀Starting server... ")

    # Debug Mode
    #  uv run mcp dev server.py

    # Production Mode
    # uv run server.py --server_type=sse


    #args = parser.parse_args()
    mcp.run(transport="sse")