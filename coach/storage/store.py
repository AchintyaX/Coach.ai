import json
from pathlib import Path

from coach.storage.schema import Goal, PlanNote, ReadinessCheckin


def _write_json(path: Path, data: dict) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, indent=2))
    return path


def load_goals(data_dir: Path = Path("data")) -> list[Goal]:
    path = data_dir / "goals" / "goals.json"
    if not path.exists():
        return []
    raw = json.loads(path.read_text())
    return [Goal.model_validate(item) for item in raw]


def save_goals(goals: list[Goal], data_dir: Path = Path("data")) -> None:
    path = data_dir / "goals" / "goals.json"
    _write_json(path, [goal.model_dump() for goal in goals])


def save_research(goal_id: str, markdown: str, data_dir: Path = Path("data")) -> Path:
    path = data_dir / "goals" / "research" / f"{goal_id}.md"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(markdown)
    return path


def save_plan_note(date: str, note: PlanNote, data_dir: Path = Path("data")) -> Path:
    path = data_dir / "plan" / f"{date}.json"
    return _write_json(path, note.model_dump())


def load_plan_note(date: str, data_dir: Path = Path("data")) -> PlanNote | None:
    path = data_dir / "plan" / f"{date}.json"
    if not path.exists():
        return None
    return PlanNote.model_validate(json.loads(path.read_text()))


def append_readiness(date: str, checkin: ReadinessCheckin, data_dir: Path = Path("data")) -> Path:
    path = data_dir / "logs" / "readiness" / f"{date}.json"
    return _write_json(path, checkin.model_dump())


def load_profile(data_dir: Path = Path("data")) -> dict:
    path = data_dir / "athlete" / "profile.json"
    if not path.exists():
        return {}
    return json.loads(path.read_text())


def load_personality(data_dir: Path = Path("data")) -> dict | None:
    path = data_dir / "coach" / "personality.json"
    if not path.exists():
        return None
    return json.loads(path.read_text())


def save_personality(personality: dict, data_dir: Path = Path("data")) -> Path:
    path = data_dir / "coach" / "personality.json"
    return _write_json(path, personality)
