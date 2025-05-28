import os
import requests
from dotenv import load_dotenv
from typing import Optional, Dict, Any

load_dotenv()

def explore_segments(bounds: str, activity_type: Optional[str] = None, min_cat: Optional[int] = None, max_cat: Optional[int] = None) -> Dict[str, Any]:
    """
    Searches for popular segments within a given geographical area.

    Args:
        bounds (str): The geographical area to search, specified as a comma-separated string: 
                      south_west_lat,south_west_lng,north_east_lat,north_east_lng.
        activity_type (Optional[str]): Filter segments by activity type ('running' or 'riding').
        min_cat (Optional[int]): Filter by minimum climb category (0-5). Requires riding activity_type.
        max_cat (Optional[int]): Filter by maximum climb category (0-5). Requires riding activity_type.

    Returns:
        Dict[str, Any]: A dictionary containing the results or error messages.
    """
    token = os.getenv("STRAVA_ACCESS_TOKEN")

    if not token or token == "YOUR_STRAVA_ACCESS_TOKEN_HERE":
        return {
            "content": [{"type": "text", "text": "❌ Configuration Error: STRAVA_ACCESS_TOKEN is missing or not set in the .env file."}],
            "isError": True,
        }

    if (min_cat is not None or max_cat is not None) and activity_type != "riding":
        return {
            "content": [{"type": "text", "text": "❌ Input Error: Climb category filters (minCat, maxCat) require activityType to be 'riding'."}],
            "isError": True,
        }

    try:
        print(f"Exploring segments within bounds: {bounds}...")

        # Fetch authenticated athlete details
        athlete_response = requests.get(
            "https://www.strava.com/api/v3/athlete",
            headers={"Authorization": f"Bearer {token}"}
        )
        athlete_response.raise_for_status()
        athlete = athlete_response.json()

        # Fetch segments
        params = {
            "bounds": bounds,
            "activity_type": activity_type,
            "min_cat": min_cat,
            "max_cat": max_cat,
        }
        response = requests.get(
            "https://www.strava.com/api/v3/segments/explore",
            headers={"Authorization": f"Bearer {token}"},
            params={k: v for k, v in params.items() if v is not None}
        )
        response.raise_for_status()
        data = response.json()

        segments = data.get("segments", [])
        if not segments:
            return {"content": [{"type": "text", "text": "No segments found in the specified area with the given filters."}]}

        # Format results based on athlete's measurement preference
        measurement_preference = athlete.get("measurement_preference", "meters")
        distance_factor = 0.000621371 if measurement_preference == "feet" else 0.001
        distance_unit = "mi" if measurement_preference == "feet" else "km"
        elevation_factor = 3.28084 if measurement_preference == "feet" else 1
        elevation_unit = "ft" if measurement_preference == "feet" else "m"

        segment_items = []
        for segment in segments:
            distance = round(segment["distance"] * distance_factor, 2)
            elev_difference = round(segment["elev_difference"] * elevation_factor, 0)
            text = (
                f"🗺️ **{segment['name']}** (ID: {segment['id']})\n"
                f"   - Climb: Cat {segment['climb_category_desc']} ({segment['climb_category']})\n"
                f"   - Distance: {distance} {distance_unit}\n"
                f"   - Avg Grade: {segment['avg_grade']}%\n"
                f"   - Elev Difference: {elev_difference} {elevation_unit}\n"
                f"   - Starred: {'Yes' if segment['starred'] else 'No'}"
            )
            segment_items.append({"type": "text", "text": text})

        response_text = "**Found Segments:**\n\n" + "\n---\n".join(item["text"] for item in segment_items)
        return {"content": [{"type": "text", "text": response_text}]}

    except requests.RequestException as e:
        error_message = str(e)
        print("Error in explore_segments tool:", error_message)
        return {
            "content": [{"type": "text", "text": f"❌ API Error: {error_message}"}],
            "isError": True,
        }
