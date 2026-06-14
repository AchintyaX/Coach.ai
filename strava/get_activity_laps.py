import os
import json
from typing import Any, Dict, List, Optional
import requests

# Helper function to format duration
def format_duration(seconds: Optional[int]) -> str:
    if seconds is None or seconds < 0:
        return "N/A"
    hours, remainder = divmod(seconds, 3600)
    minutes, secs = divmod(remainder, 60)
    parts = []
    if hours > 0:
        parts.append(f"{hours:02}")
    parts.append(f"{minutes:02}")
    parts.append(f"{secs:02}")
    return ":".join(parts)

# Tool definition
def get_activity_laps(activity_id: int) -> Dict[str, Any]:
    token = os.getenv("STRAVA_ACCESS_TOKEN")

    if not token:
        print("Missing STRAVA_ACCESS_TOKEN environment variable.", flush=True)
        return {
            "content": [{"type": "text", "text": "Configuration error: Missing Strava access token."}],
            "isError": True
        }

    try:
        print(f"Fetching laps for activity ID: {activity_id}...", flush=True)
        headers = {"Authorization": f"Bearer {token}"}
        response = requests.get(f"https://www.strava.com/api/v3/activities/{activity_id}/laps", headers=headers)
        response.raise_for_status()
        laps = response.json()

        if not laps:
            return {
                "content": [{"type": "text", "text": f"✅ No laps found for activity ID: {activity_id}"}]
            }

        # Generate human-readable summary
        lap_summaries = []
        for lap in laps:
            details = [
                f"Lap {lap.get('lap_index')}: {lap.get('name', 'Unnamed Lap')}",
                f"  Time: {format_duration(lap.get('elapsed_time'))} (Moving: {format_duration(lap.get('moving_time'))})",
                f"  Distance: {lap.get('distance', 0) / 1000:.2f} km",
                f"  Avg Speed: {lap.get('average_speed', 0) * 3.6:.2f} km/h" if lap.get('average_speed') else "N/A",
                f"  Max Speed: {lap.get('max_speed', 0) * 3.6:.2f} km/h" if lap.get('max_speed') else "N/A",
                f"  Elevation Gain: {lap.get('total_elevation_gain', 0):.1f} m" if lap.get('total_elevation_gain') else None,
                f"  Avg HR: {lap.get('average_heartrate', 0):.1f} bpm" if lap.get('average_heartrate') else None,
                f"  Max HR: {lap.get('max_heartrate', 0):.0f} bpm" if lap.get('max_heartrate') else None,
                f"  Avg Cadence: {lap.get('average_cadence', 0):.1f} rpm" if lap.get('average_cadence') else None,
                f"  Avg Power: {lap.get('average_watts', 0):.1f} W {'(Sensor)' if lap.get('device_watts') else ''}" if lap.get('average_watts') else None,
            ]
            lap_summaries.append("\n".join(filter(None, details)))

        summary_text = f"Activity Laps Summary (ID: {activity_id}):\n\n" + "\n\n".join(lap_summaries)
        
        # Add raw data section
        raw_data_text = f"\n\nComplete Lap Data:\n{json.dumps(laps, indent=2)}"
        
        print(f"Successfully fetched {len(laps)} laps for activity {activity_id}", flush=True)
        
        return {
            "content": [
                {"type": "text", "text": summary_text},
                {"type": "text", "text": raw_data_text}
            ]
        }
    except requests.exceptions.RequestException as error:
        error_message = str(error)
        print(f"Error fetching laps for activity {activity_id}: {error_message}", flush=True)
        user_friendly_message = (
            f"Activity with ID {activity_id} not found."
            if "404" in error_message
            else f"An unexpected error occurred while fetching laps for activity {activity_id}. Details: {error_message}"
        )
        return {
            "content": [{"type": "text", "text": f"❌ {user_friendly_message}"}],
            "isError": True
        }
