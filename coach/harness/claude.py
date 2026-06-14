"""``ClaudeHarness`` — installs Coach AI into a Claude Code project.

File-target matrix (techspec section 5.1):

- ``install_personality()``   -> ``./CLAUDE.md`` (merged, marked section)
- ``register_mcp_server()``   -> ``./.mcp.json`` -> ``mcpServers.<name>``
- ``install_skills()``        -> ``./.claude/skills/<skill>/SKILL.md``
- ``setup_source()``          -> runs source auth, then ``register_mcp_server()``
- ``verify()``                -> also writes ``./.claude/settings.json``
"""

from __future__ import annotations

import json
from pathlib import Path

import yaml

from coach.harness.base import BaseHarness, render_skill
from coach.sources.base import SourceSpec

COACH_START = "<!-- coach:start -->"
COACH_END = "<!-- coach:end -->"

DEFAULT_PERMISSIONS_ALLOW = [
    "Read(./data/**)",
    "Write(./data/**)",
    "WebSearch",
    "WebFetch",
    "Bash",
]


class ClaudeHarness(BaseHarness):
    """Installs/merges Coach AI configuration for the Claude Code harness."""

    # ------------------------------------------------------------------
    # Personality
    # ------------------------------------------------------------------

    def install_personality(self, text: str) -> Path:
        path = self.project_dir / "CLAUDE.md"
        block = f"{COACH_START}\n{text}\n{COACH_END}"

        if not path.exists():
            path.write_text(block + "\n", encoding="utf-8")
            return path

        existing = path.read_text(encoding="utf-8")

        if COACH_START in existing and COACH_END in existing:
            start_idx = existing.index(COACH_START)
            end_idx = existing.index(COACH_END) + len(COACH_END)
            new_content = existing[:start_idx] + block + existing[end_idx:]
        else:
            separator = "" if existing.endswith("\n") else "\n"
            if existing and not existing.endswith("\n\n"):
                separator += "\n"
            new_content = existing + separator + block + "\n"

        path.write_text(new_content, encoding="utf-8")
        return path

    # ------------------------------------------------------------------
    # MCP servers
    # ------------------------------------------------------------------

    def register_mcp_server(self, spec: SourceSpec) -> Path:
        path = self.project_dir / ".mcp.json"

        if path.exists():
            config = json.loads(path.read_text(encoding="utf-8"))
        else:
            config = {}

        servers = config.setdefault("mcpServers", {})

        entry: dict = {
            "command": spec.command,
            "args": list(spec.args),
        }
        if spec.env:
            entry["env"] = dict(spec.env)

        servers[spec.mcp_server_name] = entry

        path.write_text(json.dumps(config, indent=2) + "\n", encoding="utf-8")
        return path

    # ------------------------------------------------------------------
    # Skills
    # ------------------------------------------------------------------

    def install_skills(self, skills_dir: Path, capabilities: set[str]) -> list[Path]:
        skills_dir = Path(skills_dir)
        written: list[Path] = []

        if not skills_dir.is_dir():
            return written

        for skill_dir in sorted(skills_dir.iterdir()):
            skill_file = skill_dir / "SKILL.md"
            if not skill_dir.is_dir() or not skill_file.is_file():
                continue

            content = skill_file.read_text(encoding="utf-8")
            frontmatter = _parse_frontmatter(content)
            required = set(frontmatter.get("capabilities") or [])

            if not required <= capabilities:
                continue

            rendered = render_skill(content, capabilities)

            dest = self.project_dir / ".claude" / "skills" / skill_dir.name / "SKILL.md"
            dest.parent.mkdir(parents=True, exist_ok=True)
            dest.write_text(rendered, encoding="utf-8")
            written.append(dest)

        return written

    # ------------------------------------------------------------------
    # Source setup
    # ------------------------------------------------------------------

    def setup_source(self, spec: SourceSpec) -> None:
        for step in spec.auth_steps:
            print(f"→ {step}")

        self.register_mcp_server(spec)

    # ------------------------------------------------------------------
    # Verification
    # ------------------------------------------------------------------

    def verify(self) -> dict[str, bool]:
        status: dict[str, bool] = {}

        # personality
        claude_md = self.project_dir / "CLAUDE.md"
        personality = False
        if claude_md.exists():
            content = claude_md.read_text(encoding="utf-8")
            if COACH_START in content and COACH_END in content:
                start_idx = content.index(COACH_START) + len(COACH_START)
                end_idx = content.index(COACH_END)
                block_body = content[start_idx:end_idx].strip()
                personality = bool(block_body)
        status["personality"] = personality

        # mcp
        mcp_path = self.project_dir / ".mcp.json"
        mcp_ok = False
        if mcp_path.exists():
            try:
                mcp_config = json.loads(mcp_path.read_text(encoding="utf-8"))
                servers = mcp_config.get("mcpServers")
                mcp_ok = bool(servers)
            except (json.JSONDecodeError, OSError):
                mcp_ok = False
        status["mcp"] = mcp_ok

        # skills
        skills_path = self.project_dir / ".claude" / "skills"
        skills_ok = skills_path.is_dir() and any(skills_path.iterdir())
        status["skills"] = skills_ok

        # settings - write/merge ./.claude/settings.json
        settings_path = self.project_dir / ".claude" / "settings.json"
        settings_path.parent.mkdir(parents=True, exist_ok=True)

        if settings_path.exists():
            try:
                settings = json.loads(settings_path.read_text(encoding="utf-8"))
            except (json.JSONDecodeError, OSError):
                settings = {}
        else:
            settings = {}

        settings["enableAllProjectMcpServers"] = True

        permissions = settings.setdefault("permissions", {})
        allow = permissions.setdefault("allow", [])
        for entry in DEFAULT_PERMISSIONS_ALLOW:
            if entry not in allow:
                allow.append(entry)

        settings_path.write_text(json.dumps(settings, indent=2) + "\n", encoding="utf-8")

        status["settings"] = settings.get("enableAllProjectMcpServers") is True

        return status


# ---------------------------------------------------------------------------
# Frontmatter parsing
# ---------------------------------------------------------------------------


def _parse_frontmatter(content: str) -> dict:
    """Extract and parse a SKILL.md's YAML frontmatter.

    Returns an empty dict if no frontmatter block is present.
    """
    if not content.startswith("---"):
        return {}

    parts = content.split("---", 2)
    if len(parts) < 3:
        return {}

    frontmatter_raw = parts[1]
    data = yaml.safe_load(frontmatter_raw)
    return data or {}
