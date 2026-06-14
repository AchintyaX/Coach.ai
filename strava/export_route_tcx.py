import os
import requests
from pathlib import Path

def export_route_tcx(route_id: int) -> dict:
    """
    Exports a specific Strava route in TCX format and saves it to a pre-configured local directory.

    Args:
        route_id (int): The ID of the Strava route to export.

    Returns:
        dict: A dictionary containing the result message or error details.
    """
    token = os.getenv("STRAVA_ACCESS_TOKEN")
    if not token:
        return {
            "content": [{"type": "text", "text": "❌ Error: Missing STRAVA_ACCESS_TOKEN in .env file."}],
            "isError": True
        }

    export_dir = os.getenv("ROUTE_EXPORT_PATH")
    if not export_dir:
        return {
            "content": [{"type": "text", "text": "❌ Error: Missing ROUTE_EXPORT_PATH in .env file. Please configure the directory for saving exports."}],
            "isError": True
        }

    try:
        # Ensure the directory exists, create if not
        export_path = Path(export_dir)
        export_path.mkdir(parents=True, exist_ok=True)

        # Fetch TCX data from Strava API
        response = requests.get(
            f"https://www.strava.com/api/v3/routes/{route_id}/export_tcx",
            headers={"Authorization": f"Bearer {token}"}
        )
        response.raise_for_status()
        tcx_data = response.text

        # Save TCX data to file
        filename = f"route-{route_id}.tcx"
        full_path = export_path / filename
        with open(full_path, "w") as file:
            file.write(tcx_data)

        return {
            "content": [{"type": "text", "text": f"✅ Route {route_id} exported successfully as TCX to: {full_path}"}],
        }

    except requests.RequestException as e:
        error_message = str(e)
        print(f"Error in export_route_tcx tool for route {route_id}: {error_message}")
        return {
            "content": [{"type": "text", "text": f"❌ Error exporting route {route_id} as TCX: {error_message}"}],
            "isError": True
        }

    except PermissionError:
        return {
            "content": [{"type": "text", "text": f"❌ Error: No write permission for ROUTE_EXPORT_PATH directory ({export_dir})."}],
            "isError": True
        }
