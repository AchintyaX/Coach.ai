import os
from datetime import datetime
from strava_client import get_authenticated_athlete

def get_athlete_profile():
    """
    Fetches the profile information for the authenticated athlete, including their unique numeric ID
    needed for other tools like get-athlete-stats.
    """
    token = os.getenv("STRAVA_ACCESS_TOKEN")

    if not token or token == "YOUR_STRAVA_ACCESS_TOKEN_HERE":
        print("Missing or placeholder STRAVA_ACCESS_TOKEN in .env")
        return {
            "content": [{"type": "text", "text": "❌ Configuration Error: STRAVA_ACCESS_TOKEN is missing or not set in the .env file."}],
            "isError": True,
        }

    try:
        print("Fetching athlete profile...")
        athlete = get_authenticated_athlete(token)
        print(f"Successfully fetched profile for {athlete.firstname} {athlete.lastname} (ID: {athlete.id}).")

        profile_parts = [
            f"👤 **Profile for {athlete.firstname} {athlete.lastname}** (ID: {athlete.id})",
            f"   - Username: {athlete.username or 'N/A'}",
            f"   - Location: {', '.join(filter(None, [athlete.city, athlete.state, athlete.country])) or 'N/A'}",
            f"   - Sex: {athlete.sex or 'N/A'}",
            f"   - Weight: {'{} kg'.format(athlete.weight) if athlete.weight else 'N/A'}",
            f"   - Measurement Units: {athlete.measurement_preference or 'N/A'}",
            f"   - Strava Summit Member: {'Yes' if athlete.summit else 'No'}",
            f"   - Profile Image (Medium): {athlete.profile_medium or 'N/A'}",
            f"   - Joined Strava: {athlete.created_at.strftime('%Y-%m-%d') if athlete.created_at else 'N/A'}",
            f"   - Last Updated: {athlete.updated_at.strftime('%Y-%m-%d') if athlete.updated_at else 'N/A'}",
        ]

        return {
            "content": [{"type": "text", "text": "\n".join(profile_parts)}]
        }

    except Exception as error:
        error_message = str(error) if isinstance(error, Exception) else "An unknown error occurred"
        print("Error in get_athlete_profile tool:", error_message)
        return {
            "content": [{"type": "text", "text": f"❌ API Error: {error_message}"}],
            "isError": True,
        }