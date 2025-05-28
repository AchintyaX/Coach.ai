import os
from typing import Optional, List, Dict
from pydantic import BaseModel, ValidationError
from strava_client import strava_api, refresh_access_token

class ZoneRange(BaseModel):
    min: int
    max: Optional[int]

class DistributionBucket(BaseModel):
    min: int
    max: int
    time: int

class HeartRateZones(BaseModel):
    custom_zones: bool
    zones: List[ZoneRange]
    distribution_buckets: Optional[List[DistributionBucket]] = None

class PowerZones(BaseModel):
    zones: List[ZoneRange]
    distribution_buckets: Optional[List[DistributionBucket]]

class StravaAthleteZones(BaseModel):
    heart_rate: Optional[HeartRateZones] = None
    power: Optional[PowerZones] = None

def format_zone_range(zone: ZoneRange) -> str:
    return f"{zone.min} - {zone.max}" if zone.max else f"{zone.min}+"

def format_distribution(buckets: Optional[List[DistributionBucket]]) -> str:
    if not buckets:
        return "  Distribution data not available."
    return "\n".join(
        f"  - {bucket.min}-{bucket.max if bucket.max != -1 else '∞'}: {bucket.time}s"
        for bucket in buckets
    )

def format_athlete_zones(zones_data: StravaAthleteZones) -> str:
    response_text = "**Athlete Zones:**\n"

    if zones_data.heart_rate:
        response_text += "\n❤️ **Heart Rate Zones**\n"
        response_text += f"   Custom Zones: {'Yes' if zones_data.heart_rate.custom_zones else 'No'}\n"
        for i, zone in enumerate(zones_data.heart_rate.zones, start=1):
            response_text += f"   Zone {i}: {format_zone_range(zone)} bpm\n"
        if zones_data.heart_rate.distribution_buckets:
            response_text += "   Time Distribution:\n" + format_distribution(zones_data.heart_rate.distribution_buckets) + "\n"
    else:
        response_text += "\n❤️ Heart Rate Zones: Not configured\n"

    if zones_data.power:
        response_text += "\n⚡ **Power Zones**\n"
        for i, zone in enumerate(zones_data.power.zones, start=1):
            response_text += f"   Zone {i}: {format_zone_range(zone)} W\n"
        if zones_data.power.distribution_buckets:
            response_text += "   Time Distribution:\n" + format_distribution(zones_data.power.distribution_buckets) + "\n"
    else:
        response_text += "\n⚡ Power Zones: Not configured\n"

    return response_text

def get_athlete_zones() -> Dict[str, str]:
    token = os.getenv("STRAVA_ACCESS_TOKEN")
    if not token:
        return {"error": "Configuration error: Missing Strava access token."}

    try:
        print("Fetching athlete zones...")
        data = strava_api.get("athlete/zones", headers={"Authorization": f"Bearer {token}"})
        print(data)
        zones_data = StravaAthleteZones(**data)

        formatted_text = format_athlete_zones(zones_data)
        raw_data_text = f"\n\nRaw Athlete Zone Data:\n{data}"

        print("Successfully fetched athlete zones.")
        return {"formatted": formatted_text, "raw": raw_data_text}

    except ValidationError as e:
        print("Validation error:", e)
        return {"error": "Validation error occurred while processing athlete zones."}
    except Exception as e:
        if "401" in str(e):
            print("🔑 Token expired. Refreshing...")
            refresh_access_token()
            return get_athlete_zones()
        elif "403" in str(e):
            return {"error": "🔒 Access denied. This tool requires 'profile:read_all' permission. Please re-authorize with the correct scope."}
        elif "SUBSCRIPTION_REQUIRED" in str(e):
            return {"error": f"🔒 Accessing zones might require a Strava subscription. Details: {e}"}
        else:
            return {"error": f"An unexpected error occurred: {e}"}
