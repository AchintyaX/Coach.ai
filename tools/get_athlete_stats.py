from typing import Optional, Dict, Any
import os
import math

from pydantic import BaseModel, Field, ValidationError
from strava_client import get_athlete_stats as fetch_athlete_stats  # Import added

# Input schema: Now requires athlete_id
class GetAthleteStatsInput(BaseModel):
    athlete_id: int = Field(..., gt=0, description="The unique identifier of the athlete to fetch stats for. Obtain this ID first by calling the get-athlete-profile tool.")

# Helper function to format numbers as strings with labels (metric)
def format_stat(value: Optional[float], unit: str) -> str:
    if value is None:
        return "N/A"

    if unit == "km":
        formatted_value = f"{value / 1000:.2f}"
    elif unit == "m":
        formatted_value = f"{math.floor(value)}"
    elif unit == "hrs":
        formatted_value = f"{value / 3600:.1f}"
    else:
        formatted_value = str(value)

    return f"{formatted_value} {unit}"

# Format athlete stats (metric only)
def format_stats(stats: Dict[str, Any]) -> str:
    def format_line(label: str, total: Optional[float], unit: str, count: Optional[int] = None, time: Optional[float] = None) -> str:
        line = f"   - {label}: {format_stat(total, unit)}"
        if count is not None:
            line += f" ({count} activities)"
        if time is not None:
            line += f" / {format_stat(time, 'hrs')} hours"
        return line

    response = "📊 **Your Strava Stats:**\n"

    if "biggest_ride_distance" in stats:
        response += "**Rides:**\n"
        response += format_line("Biggest Ride", stats.get("biggest_ride_distance"), "km") + "\n"

    if "recent_ride_totals" in stats:
        response += "*Recent Rides (last 4 weeks):*\n"
        recent = stats["recent_ride_totals"]
        response += format_line("Distance", recent.get("distance"), "km", recent.get("count"), recent.get("moving_time")) + "\n"
        response += format_line("Elevation Gain", recent.get("elevation_gain"), "m") + "\n"

    if "ytd_ride_totals" in stats:
        response += "*Year-to-Date Rides:*\n"
        ytd = stats["ytd_ride_totals"]
        response += format_line("Distance", ytd.get("distance"), "km", ytd.get("count"), ytd.get("moving_time")) + "\n"
        response += format_line("Elevation Gain", ytd.get("elevation_gain"), "m") + "\n"

    if "all_ride_totals" in stats:
        response += "*All-Time Rides:*\n"
        all_time = stats["all_ride_totals"]
        response += format_line("Distance", all_time.get("distance"), "km", all_time.get("count"), all_time.get("moving_time")) + "\n"
        response += format_line("Elevation Gain", all_time.get("elevation_gain"), "m") + "\n"

    # Similar blocks for Runs and Swims if needed...
    if any(key in stats for key in ["recent_run_totals", "ytd_run_totals", "all_run_totals"]):
        response += "\n**Runs:**\n"
        if "recent_run_totals" in stats:
            response += "*Recent Runs (last 4 weeks):*\n"
            recent = stats["recent_run_totals"]
            response += format_line("Distance", recent.get("distance"), "km", recent.get("count"), recent.get("moving_time")) + "\n"
            response += format_line("Elevation Gain", recent.get("elevation_gain"), "m") + "\n"

        if "ytd_run_totals" in stats:
            response += "*Year-to-Date Runs:*\n"
            ytd = stats["ytd_run_totals"]
            response += format_line("Distance", ytd.get("distance"), "km", ytd.get("count"), ytd.get("moving_time")) + "\n"
            response += format_line("Elevation Gain", ytd.get("elevation_gain"), "m") + "\n"

        if "all_run_totals" in stats:
            response += "*All-Time Runs:*\n"
            all_time = stats["all_run_totals"]
            response += format_line("Distance", all_time.get("distance"), "km", all_time.get("count"), all_time.get("moving_time")) + "\n"
            response += format_line("Elevation Gain", all_time.get("elevation_gain"), "m") + "\n"

    # Add Swims similarly if needed

    return response

# Tool definition
def get_athlete_stats_tool(athelete_id: int) -> Dict[str, Any]:
   
    token = os.getenv("STRAVA_ACCESS_TOKEN")
    if not token:
        print("Missing STRAVA_ACCESS_TOKEN environment variable.")
        return {
            "content": [{"type": "text", "text": "Configuration error: Missing Strava access token."}],
            "isError": True
        }

    athlete_id = int(athelete_id)  # Ensure athlete_id is an integer
    try:
        print(f"Fetching stats for athlete {athlete_id}...")
        stats = fetch_athlete_stats(token, athlete_id)  # Updated to use imported function
        formatted_stats = format_stats(stats)

        print(f"Successfully fetched stats for athlete {athlete_id}.")
        return {"content": [{"type": "text", "text": formatted_stats}]}
    except Exception as error:
        error_message = str(error)
        print(f"Error fetching stats for athlete {athlete_id}: {error_message}")
        user_friendly_message = (
            f"Athlete with ID {athlete_id} not found (when fetching stats)."
            if "Record Not Found" in error_message or "404" in error_message
            else f"An unexpected error occurred while fetching stats for athlete {athlete_id}. Details: {error_message}"
        )
        return {
            "content": [{"type": "text", "text": f"❌ {user_friendly_message}"}],
            "isError": True
        }
