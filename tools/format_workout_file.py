import re
from typing import List, Dict, Union

class WorkoutSegment:
    def __init__(self, type: str, duration: Dict[str, Union[int, str]], target: str, cadence: int = None, notes: str = None):
        self.type = type
        self.duration = duration
        self.target = target
        self.cadence = cadence
        self.notes = notes

def target_to_zwift_power(target: str) -> float:
    target_lower = target.lower()
    ftp_match = re.search(r"(\d+)%\s*ftp", target_lower)
    if ftp_match:
        return int(ftp_match.group(1)) / 100

    zone_map = {
        "very easy": 0.5,
        "easy": 0.6,
        "zone 1": 0.6,
        "zone 2": 0.75,
        "moderate": 0.75,
        "tempo": 0.85,
        "zone 3": 0.85,
        "threshold": 1.0,
        "zone 4": 1.0,
        "hard": 1.05,
        "zone 5": 1.1,
        "very hard": 1.15,
        "max": 1.2,
    }

    for desc, power in zone_map.items():
        if desc in target_lower:
            return power

    return 0.75

def parse_duration(duration: str) -> Dict[str, Union[int, str]]:
    match = re.match(r"(\d+)\s*(min|sec)", duration, re.IGNORECASE)
    if not match:
        raise ValueError(f"Invalid duration format: {duration}")
    return {"value": int(match.group(1)), "unit": match.group(2).lower()}

def parse_workout_text(text: str) -> List[WorkoutSegment]:
    segments = []
    lines = text.split("\n")

    for line in lines:
        if not line.strip().startswith("-"):
            continue

        match = re.match(r"^-\s*([^:]+):\s*(\d+\s*(?:min|sec))\s*at\s*([^[\n]+)(?:\s*\[([^\]]+)\])?", line, re.IGNORECASE)
        if not match:
            continue

        type, duration, target, extras = match.groups()
        segment = WorkoutSegment(
            type=type.strip(),
            duration=parse_duration(duration.strip()),
            target=target.strip()
        )

        if extras:
            cadence_match = re.search(r"Cadence:\s*(\d+)", extras, re.IGNORECASE)
            if cadence_match:
                segment.cadence = int(cadence_match.group(1))

            notes_match = re.search(r"Notes:\s*([^\]]+)", extras, re.IGNORECASE)
            if notes_match:
                segment.notes = notes_match.group(1).strip()

        segments.append(segment)

    return segments

def generate_zwo_content(segments: List[WorkoutSegment]) -> str:
    workout_segments = []
    for segment in segments:
        duration_seconds = segment.duration["value"] * 60 if segment.duration["unit"] == "min" else segment.duration["value"]
        power = target_to_zwift_power(segment.target)
        cadence_attr = f' Cadence="{segment.cadence}"' if segment.cadence else ""
        shows_target = ' ShowsPower="1"' if "ftp" in segment.target.lower() else ""
        notes_attr = f' textEvent="{segment.notes}"' if segment.notes else ""

        workout_segments.append(
            f'        <SteadyState Duration="{duration_seconds}" Power="{power}"{cadence_attr}{shows_target}{notes_attr}/>'
        )

    return f"""<workout_file>
    <author>Strava MCP Server</author>
    <name>Generated Workout</name>
    <description>Workout generated based on recent activities</description>
    <sportType>bike</sportType>
    <tags></tags>
    <workout>
{chr(10).join(workout_segments)}
    </workout>
</workout_file>"""

def format_workout_file(workout_text: str, format: str = "zwo") -> Dict[str, Union[str, bool]]:
    try:
        segments = parse_workout_text(workout_text)
        if not segments:
            return {
                "content": "❌ No valid workout segments found in the input text. Please ensure the format matches the expected pattern.",
                "isError": True
            }

        if format == "zwo":
            zwo_content = generate_zwo_content(segments)
            return {
                "content": zwo_content,
                "mimeType": "application/xml"
            }

        raise ValueError(f"Unsupported format: {format}")

    except Exception as e:
        return {
            "content": f"❌ Failed to format workout: {str(e)}",
            "isError": True
        }
