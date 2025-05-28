import os
from pydantic import BaseModel, ValidationError, Field
from typing import Dict, Any, Union
from strava_client import strava_api, refresh_access_token

# Input schema for route fetching
class GetRouteInput(BaseModel):
    route_id: int = Field(..., gt=0, description="The unique identifier of the route to fetch.")

# Function to format route summary
def format_route_summary(route: Dict[str, Any]) -> str:
    return f"Route Name: {route.get('name', 'N/A')}, Distance: {route.get('distance', 'N/A')} meters"

# Tool function to fetch route details
def get_route_tool(input_data: Dict[str, Any]) -> Dict[str, Union[str, bool]]:
    try:
        # Validate input
        input_obj = GetRouteInput(**input_data)
        route_id = input_obj.route_id

        # Fetch access token
        token = os.getenv("STRAVA_ACCESS_TOKEN")
        if not token:
            return {
                "content": "Configuration error: Missing Strava access token.",
                "is_error": True
            }

        # Fetch route details
        try:
            print(f"Fetching route details for ID: {route_id}...")
            route = strava_api.get(f"routes/{route_id}", headers={"Authorization": f"Bearer {token}"})
            summary = format_route_summary(route)
            print(f"Successfully fetched route {route_id}.")
            return {"content": summary, "is_error": False}
        except Exception as error:
            if "401" in str(error):  # Handle token expiration
                print("🔑 Token expired. Refreshing...")
                token = refresh_access_token()
                return get_route_tool({"route_id": route_id})
            error_message = str(error)
            user_friendly_message = (
                f"Route with ID {route_id} not found."
                if "404" in error_message or "Record Not Found" in error_message
                else f"An unexpected error occurred: {error_message}"
            )
            return {"content": f"❌ {user_friendly_message}", "is_error": True}
    except ValidationError as e:
        return {"content": f"Validation error: {e}", "is_error": True}
