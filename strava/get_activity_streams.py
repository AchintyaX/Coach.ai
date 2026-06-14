import os
import requests
from typing import List, Dict, Any, Optional

# Define stream types available in Strava API
STREAM_TYPES = [
    "time", "distance", "latlng", "altitude", "velocity_smooth",
    "heartrate", "cadence", "watts", "temp", "moving", "grade_smooth"
]

# Define resolution types
RESOLUTION_TYPES = ["low", "medium", "high"]

get_activity_streams_descriptions = """
    Retrieves detailed time-series data streams from a Strava activity. Perfect for analyzing workout metrics, 
    visualizing routes, or performing detailed activity analysis.

    Key Features:
    1. Multiple Data Types: Access various metrics like heart rate, power, speed, GPS coordinates, etc.
    2. Flexible Resolution: Choose data density from low (~100 points) to high (~10000 points)
    3. Smart Pagination: Get data in manageable chunks or all at once
    4. Rich Statistics: Includes min/max/avg for numeric streams
    5. Formatted Output: Data is processed into human and LLM-friendly formats

    Common Use Cases:
    - Analyzing workout intensity through heart rate zones
    - Calculating power metrics for cycling activities
    - Visualizing route data using GPS coordinates
    - Analyzing pace and elevation changes
    - Detailed segment analysis

    Output Format:
    1. Metadata: Activity overview, available streams, data points
    2. Statistics: Summary stats for each stream type (max/min/avg where applicable)
    3. Stream Data: Actual time-series data, formatted for easy use
    
    INPUT:
    activity_id: int - The unique ID of the Strava activity to fetch streams for
    types: List[str] - List of stream types to retrieve (e.g., ["latlng", "heartrate", "watts"])
    resolution: Optional[str] - Resolution of the data (default: None, which uses Strava's default resolution)

    Notes: 
    - Requires activity:read scope
    - Not all streams are available for all activities
    - Older activities might have limited data
    - Large activities are automatically paginated to handle size limits
"""
# Helper function to calculate normalized power
def calculate_normalized_power(power_data: List[float]) -> float:
    if len(power_data) < 30:
        return 0.0

    # 30-second moving average
    window_size = 30
    moving_avg = [
        sum(power_data[i - window_size + 1:i + 1]) / window_size
        for i in range(window_size - 1, len(power_data))
    ]
    moving_avg_raised = [avg ** 4 for avg in moving_avg]

    # Calculate normalized power
    normalized_power = (sum(moving_avg_raised) / len(moving_avg_raised)) ** 0.25
    return round(normalized_power, 1)

# Tool definition
def get_activity_streams(activity_id: int, types: List[str], resolution: Optional[str] = None,
                         series_type: Optional[str] = "distance", page: int = 1,
                         points_per_page: int = 100) -> Dict[str, Any]:
    token = os.getenv("STRAVA_ACCESS_TOKEN")
    if not token:
        return {
            "content": [{"type": "text", "text": "❌ Missing STRAVA_ACCESS_TOKEN in environment variables."}],
            "isError": True
        }

    try:
        headers = {"Authorization": f"Bearer {token}"}
        params = {}
        if resolution:
            params["resolution"] = resolution
        if series_type:
            params["series_type"] = series_type

        # Build the endpoint URL
        endpoint = f"https://www.strava.com/api/v3/activities/{activity_id}/streams/{','.join(types)}"
        response = requests.get(endpoint, headers=headers, params=params)
        response.raise_for_status()
        streams = response.json()

        if not streams:
            return {
                "content": [{"type": "text", "text": "⚠️ No streams were returned. This could mean:\n"
                                                    "1. The activity was recorded without this data\n"
                                                    "2. The activity is not a GPS-based activity\n"
                                                    "3. The activity is too old (Strava may not keep all stream data indefinitely)"}],
                "isError": True
            }

        # Generate stream statistics
        stream_stats = {}
        for stream in streams:
            data = stream["data"]
            stats = {
                "total_points": len(data),
                "resolution": stream.get("resolution"),
                "series_type": stream.get("series_type")
            }

            # Add type-specific statistics
            if stream["type"] == "heartrate":
                stats.update({
                    "max": max(data),
                    "min": min(data),
                    "avg": round(sum(data) / len(data))
                })
            elif stream["type"] == "watts":
                stats.update({
                    "max": max(data),
                    "avg": round(sum(data) / len(data)),
                    "normalized_power": calculate_normalized_power(data)
                })
            elif stream["type"] == "velocity_smooth":
                stats.update({
                    "max_kph": round(max(data) * 3.6, 1),
                    "avg_kph": round(sum(data) / len(data) * 3.6, 1)
                })

            stream_stats[stream["type"]] = stats

        # Handle paginated response
        total_points = len(streams[0]["data"])
        total_pages = (total_points + points_per_page - 1) // points_per_page

        if page < 1 or page > total_pages:
            return {
                "content": [{"type": "text", "text": f"❌ Invalid page number. Please specify a page between 1 and {total_pages}"}],
                "isError": True
            }

        start_idx = (page - 1) * points_per_page
        end_idx = min(start_idx + points_per_page, total_points)

        # Process paginated stream data
        stream_data = {
            "metadata": {
                "available_types": [stream["type"] for stream in streams],
                "total_points": total_points,
                "current_page": page,
                "total_pages": total_pages,
                "points_per_page": points_per_page,
                "points_in_page": end_idx - start_idx
            },
            "statistics": stream_stats,
            "streams": {}
        }

        for stream in streams:
            paginated_data = stream["data"][start_idx:end_idx]
            if stream["type"] == "latlng":
                processed_data = [{"latitude": round(lat, 6), "longitude": round(lng, 6)} for lat, lng in paginated_data]
            elif stream["type"] == "time":
                processed_data = [{"seconds_from_start": t, "formatted": f"{t // 3600:02}:{(t % 3600) // 60:02}:{t % 60:02}"} for t in paginated_data]
            elif stream["type"] == "distance":
                processed_data = [{"meters": d, "kilometers": round(d / 1000, 2)} for d in paginated_data]
            elif stream["type"] == "velocity_smooth":
                processed_data = [{"meters_per_second": v, "kilometers_per_hour": round(v * 3.6, 1)} for v in paginated_data]
            elif stream["type"] in ["heartrate", "cadence", "watts", "temp", "grade_smooth"]:
                processed_data = [round(v, 1) for v in paginated_data]
            elif stream["type"] == "moving":
                processed_data = paginated_data
            else:
                processed_data = paginated_data

            stream_data["streams"][stream["type"]] = processed_data

        return {
            "content": [{"type": "text", "text": stream_data}]
        }

    except requests.exceptions.RequestException as error:
        error_message = str(error)
        return {
            "content": [{"type": "text", "text": f"❌ Failed to fetch activity streams: {error_message}"}],
            "isError": True
        }
