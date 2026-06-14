import os
from typing import List, Dict, Union
from pydantic import BaseModel, ValidationError
from strava.strava_client import get_recent_activities

class GetRecentActivitiesInput(BaseModel):
    per_page: int = 100  # Default value is 100

def get_recent_activities_tool(per_page: int = 100) -> Dict[str, Union[List[Dict[str, str]], bool]]:
    try:
        # Validate input using Pydantic

        # Fetch the access token from environment variables
        token = os.getenv("STRAVA_ACCESS_TOKEN")
        if not token or token == "YOUR_STRAVA_ACCESS_TOKEN_HERE":
            print("❌ Configuration Error: STRAVA_ACCESS_TOKEN is missing or not set in the environment.")
            return {
                "content": [{"type": "text", "text": "❌ Configuration Error: STRAVA_ACCESS_TOKEN is missing or not set in the environment."}],
                "isError": True,
            }

        print(f"Fetching {per_page} recent activities...")
        activities = get_recent_activities(token, per_page)
        print(f"Successfully fetched {len(activities) if activities else 0} activities.")

        if not activities:
            return {
                "content": [{"type": "text", "text": "No recent activities found."}],
            }

        # Map activities to content items
        content_items = []
        for activity in activities:
            date_str = activity.start_date.strftime("%Y-%m-%d") if activity.start_date else "N/A"
            distance_str = f"{activity.distance}m" if activity.distance else "N/A"
            content_items.append({
                "type": "text",
                "text": f"🏃 {activity.name} (ID: {activity.id or 'N/A'}) — {distance_str} on {date_str}"
            })

        return {"content": content_items}

    except ValidationError as e:
        print("Validation error:", e)
        return {
            "content": [{"type": "text", "text": f"❌ Validation Error: {str(e)}"}],
            "isError": True,
        }
    except Exception as e:
        error_message = str(e)
        print("Error in get_recent_activities_tool:", error_message)
        return {
            "content": [{"type": "text", "text": f"❌ API Error: {error_message}"}],
            "isError": True,
        }
