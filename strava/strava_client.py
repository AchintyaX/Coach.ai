import os
import requests
from pydantic import BaseModel, ValidationError, HttpUrl, Field
from typing import List, Optional, Union
from datetime import datetime

# --- Axios Equivalent ---
class StravaApiClient:
    BASE_URL = "https://www.strava.com/api/v3"

    def __init__(self):
        self.session = requests.Session()

    def get(self, endpoint: str, headers: dict = None, params: dict = None):
        url = f"{self.BASE_URL}/{endpoint}"
        response = self.session.get(url, headers=headers, params=params)
        response.raise_for_status()
        return response.json()

    def post(self, endpoint: str, headers: dict = None, data: dict = None):
        url = f"{self.BASE_URL}/{endpoint}"
        response = self.session.post(url, headers=headers, json=data)
        response.raise_for_status()
        return response.json()

    def put(self, endpoint: str, headers: dict = None, data: dict = None):
        url = f"{self.BASE_URL}/{endpoint}"
        response = self.session.put(url, headers=headers, json=data)
        response.raise_for_status()
        return response.json()


strava_api = StravaApiClient()

# --- Pydantic Schemas ---
class StravaActivity(BaseModel):
    id: Optional[int] = None
    name: str
    distance: float
    start_date: datetime

class StravaAthlete(BaseModel):
    id: int
    username: Optional[str] = None
    firstname: str
    lastname: str
    city: Optional[str] = None
    state: Optional[str] = None
    country: Optional[str] = None
    sex: Optional[str] = None
    premium: bool
    summit: bool
    created_at: datetime
    updated_at: datetime
    profile_medium: HttpUrl
    profile: HttpUrl
    weight: Optional[float] = None
    measurement_preference: Optional[str] = Field(None, alias="measurement_preference")
class StravaStats(BaseModel):
    biggest_ride_distance: Optional[float] = None
    biggest_climb_elevation_gain: Optional[float] = None
    recent_ride_totals: dict
    recent_run_totals: dict
    recent_swim_totals: dict
    ytd_ride_totals: dict
    ytd_run_totals: dict
    ytd_swim_totals: dict
    all_ride_totals: dict
    all_run_totals: dict
    all_swim_totals: dict

# --- Token Refresh ---
def refresh_access_token():
    refresh_token = os.getenv("STRAVA_REFRESH_TOKEN")
    client_id = os.getenv("STRAVA_CLIENT_ID")
    client_secret = os.getenv("STRAVA_CLIENT_SECRET")

    if not refresh_token or not client_id or not client_secret:
        raise ValueError("Missing refresh credentials in environment variables.")

    response = requests.post(
        "https://www.strava.com/oauth/token",
        json={
            "client_id": client_id,
            "client_secret": client_secret,
            "refresh_token": refresh_token,
            "grant_type": "refresh_token",
        },
    )
    response.raise_for_status()
    data = response.json()

    os.environ["STRAVA_ACCESS_TOKEN"] = data["access_token"]
    os.environ["STRAVA_REFRESH_TOKEN"] = data["refresh_token"]

    print(f"✅ Token refreshed. New token expires: {datetime.fromtimestamp(data['expires_at'])}")
    return data["access_token"]

# --- API Functions ---
def get_recent_activities(access_token: str, per_page: int = 30) -> List[StravaActivity]:
    headers = {"Authorization": f"Bearer {access_token}"}
    try:
        data = strava_api.get("athlete/activities", headers=headers, params={"per_page": per_page})
        return [StravaActivity(**activity) for activity in data]
    except ValidationError as e:
        print("Validation error:", e)
        raise
    except requests.HTTPError as e:
        if e.response.status_code == 401:
            print("🔑 Token expired. Refreshing...")
            new_token = refresh_access_token()
            return get_recent_activities(new_token, per_page)
        raise

def get_authenticated_athlete(access_token: str) -> StravaAthlete:
    headers = {"Authorization": f"Bearer {access_token}"}
    try:
        data = strava_api.get("athlete", headers=headers)
        return StravaAthlete(**data)
    except ValidationError as e:
        print("Validation error:", e)
        raise
    except requests.HTTPError as e:
        if e.response.status_code == 401:
            print("🔑 Token expired. Refreshing...")
            new_token = refresh_access_token()
            return get_authenticated_athlete(new_token)
        raise

def get_athlete_stats(access_token: str, athlete_id: int) -> StravaStats:
    headers = {"Authorization": f"Bearer {access_token}"}
    try:
        data = strava_api.get(f"athletes/{athlete_id}/stats", headers=headers)
        return StravaStats(**data)
    except ValidationError as e:
        print("Validation error:", e)
        raise
    except requests.HTTPError as e:
        if e.response.status_code == 401:
            print("🔑 Token expired. Refreshing...")
            new_token = refresh_access_token()
            return get_athlete_stats(new_token, athlete_id)
        raise
