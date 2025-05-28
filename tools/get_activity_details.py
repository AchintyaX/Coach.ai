import os
from datetime import datetime
from typing import Optional, Dict, Any
import requests

# Helper Functions (Metric Only)
def format_duration(seconds: Optional[int]) -> str:
    if seconds is None or seconds < 0:
        return 'N/A'
    hours, remainder = divmod(seconds, 3600)
    minutes, secs = divmod(remainder, 60)
    parts = []
    if hours > 0:
        parts.append(f"{hours:02}")
    parts.append(f"{minutes:02}")
    parts.append(f"{secs:02}")
    return ":".join(parts)

def format_distance(meters: Optional[float]) -> str:
    if meters is None:
        return 'N/A'
    return f"{meters / 1000:.2f} km"

def format_elevation(meters: Optional[float]) -> str:
    if meters is None:
        return 'N/A'
    return f"{round(meters)} m"

def format_speed(mps: Optional[float]) -> str:
    if mps is None:
        return 'N/A'
    return f"{mps * 3.6:.1f} km/h"

def format_pace(mps: Optional[float]) -> str:
    if mps is None or mps <= 0:
        return 'N/A'
    minutes_per_km = 1000 / (mps * 60)
    minutes = int(minutes_per_km)
    seconds = round((minutes_per_km - minutes) * 60)
    return f"{minutes}:{seconds:02} /km"

# Format activity details (Metric Only)
from dateutil.parser import parse

# Format activity details (Metric Only)
def format_activity_details(activity: Dict[str, Any]) -> str:
    try:
        # Use dateutil.parser.parse to handle various date formats
        date = parse(activity["start_date_local"]).strftime("%Y-%m-%d %H:%M:%S")
    except (ValueError, TypeError, KeyError):
        date = "Invalid Date"

    moving_time = format_duration(activity.get("moving_time"))
    elapsed_time = format_duration(activity.get("elapsed_time"))
    distance = format_distance(activity.get("distance"))
    elevation = format_elevation(activity.get("total_elevation_gain"))
    avg_speed = format_speed(activity.get("average_speed"))
    max_speed = format_speed(activity.get("max_speed"))
    avg_pace = format_pace(activity.get("average_speed"))

    details = f"🏃 **{activity['name']}** (ID: {activity['id']})\n"
    details += f"   - Type: {activity['type']} ({activity['sport_type']})\n"
    details += f"   - Date: {date}\n"
    details += f"   - Moving Time: {moving_time}, Elapsed Time: {elapsed_time}\n"
    if "distance" in activity:
        details += f"   - Distance: {distance}\n"
    if "total_elevation_gain" in activity:
        details += f"   - Elevation Gain: {elevation}\n"
    if "average_speed" in activity:
        details += f"   - Average Speed: {avg_speed}"
        if activity["type"] == "Run":
            details += f" (Pace: {avg_pace})"
        details += "\n"
    if "max_speed" in activity:
        details += f"   - Max Speed: {max_speed}\n"
    if "average_cadence" in activity:
        details += f"   - Avg Cadence: {activity['average_cadence']:.1f}\n"
    if "average_watts" in activity:
        details += f"   - Avg Watts: {activity['average_watts']:.1f}\n"
    if "average_heartrate" in activity:
        details += f"   - Avg Heart Rate: {activity['average_heartrate']:.1f} bpm\n"
    if "max_heartrate" in activity:
        details += f"   - Max Heart Rate: {activity['max_heartrate']:.0f} bpm\n"
    if "calories" in activity:
        details += f"   - Calories: {activity['calories']:.0f}\n"
    if "description" in activity:
        details += f"   - Description: {activity['description']}\n"
    if "gear" in activity:
        details += f"   - Gear: {activity['gear']['name']}\n"

    return details
# Tool definition
def get_activity_details(activity_id: int) -> Dict[str, Any]:
    token = os.getenv("STRAVA_ACCESS_TOKEN")

    if not token:
        print("Missing STRAVA_ACCESS_TOKEN environment variable.", flush=True)
        return {
            "content": [{"type": "text", "text": "Configuration error: Missing Strava access token."}],
            "isError": True
        }

    try:
        print(f"Fetching details for activity ID: {activity_id}...", flush=True)
        headers = {"Authorization": f"Bearer {token}"}
        response = requests.get(f"https://www.strava.com/api/v3/activities/{activity_id}", headers=headers)
        response.raise_for_status()
        activity = response.json()
        activity_details_text = format_activity_details(activity)

        print(f"Successfully fetched details for activity: {activity['name']}", flush=True)
        return {"content": [{"type": "text", "text": activity_details_text}]}
    except requests.exceptions.RequestException as error:
        error_message = str(error)
        print(f"Error fetching activity {activity_id}: {error_message}", flush=True)
        user_friendly_message = (
            f"Activity with ID {activity_id} not found."
            if "404" in error_message
            else f"An unexpected error occurred while fetching activity details for ID {activity_id}. Details: {error_message}"
        )
        return {
            "content": [{"type": "text", "text": f"❌ {user_friendly_message}"}],
            "isError": True
        }
