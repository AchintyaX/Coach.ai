"""``CodexHarness`` — installs Coach AI into a Codex CLI project.

File-target matrix (techspec section 5.1):

- ``install_personality()``   -> ``./AGENTS.md`` (merged, marked section)
- ``register_mcp_server()``   -> ``~/.codex/config.toml`` -> ``[mcp_servers.<name>]``
- ``install_skills()``        -> ``./.codex/skills/<skill>/SKILL.md`` +
  ``~/.codex/config.toml`` -> ``[skills.config.<n>]``
- ``setup_source()``          -> runs source auth, then ``register_mcp_server()``
- ``verify()``                -> checks ``config.toml`` sections parse and skill
  paths exist, and merges ``[tools]\nweb_search = true`` into
  ``~/.codex/config.toml``
"""

from __future__ import annotations

from pathlib import Path

import tomlkit
import yaml

from coach.harness.base import BaseHarness, render_skill
from coach.harness.claude import COACH_END, COACH_START
from coach.sources.base import SourceSpec


class CodexHarness(BaseHarness):
    """Installs/merges Coach AI configuration for the Codex CLI harness."""

    def __init__(self, project_dir: Path, home: Path | None = None):
        super().__init__(project_dir)
        self.home = home or Path.home()
        self.codex_config_path = self.home / ".codex" / "config.toml"

    # ------------------------------------------------------------------
    # Personality
    # ------------------------------------------------------------------

    def install_personality(self, text: str) -> Path:
        path = self.project_dir / "AGENTS.md"
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
        config = self._load_codex_config()

        servers = config.setdefault("mcp_servers", tomlkit.table())

        server = tomlkit.table()
        server["command"] = spec.command
        server["args"] = list(spec.args)

        if spec.env:
            env_table = tomlkit.table()
            for key, value in spec.env.items():
                env_table[key] = value
            server["env"] = env_table

        servers[spec.mcp_server_name] = server

        self._write_codex_config(config)
        return self.codex_config_path

    # ------------------------------------------------------------------
    # Skills
    # ------------------------------------------------------------------

    def install_skills(self, skills_dir: Path, capabilities: set[str]) -> list[Path]:
        skills_dir = Path(skills_dir)
        written: list[Path] = []

        if not skills_dir.is_dir():
            return written

        config = self._load_codex_config()
        skills_table = config.setdefault("skills", tomlkit.table(is_super_table=True))
        skills_config = skills_table.setdefault("config", tomlkit.table(is_super_table=True))

        existing_paths = set()
        next_index = 0
        for key, entry in skills_config.items():
            try:
                idx = int(key)
            except ValueError:
                continue
            next_index = max(next_index, idx + 1)
            entry_path = entry.get("path")
            if entry_path is not None:
                existing_paths.add(entry_path)

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

            dest = self.project_dir / ".codex" / "skills" / skill_dir.name / "SKILL.md"
            dest.parent.mkdir(parents=True, exist_ok=True)
            dest.write_text(rendered, encoding="utf-8")
            written.append(dest)

            rel_path = f"./.codex/skills/{skill_dir.name}"
            if rel_path in existing_paths:
                # Already registered - ensure it's enabled, don't duplicate.
                for entry in skills_config.values():
                    if entry.get("path") == rel_path:
                        entry["enabled"] = True
                continue

            entry = tomlkit.table()
            entry["path"] = rel_path
            entry["enabled"] = True
            skills_config[str(next_index)] = entry
            existing_paths.add(rel_path)
            next_index += 1

        self._write_codex_config(config)
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
        agents_md = self.project_dir / "AGENTS.md"
        personality = False
        if agents_md.exists():
            content = agents_md.read_text(encoding="utf-8")
            if COACH_START in content and COACH_END in content:
                start_idx = content.index(COACH_START) + len(COACH_START)
                end_idx = content.index(COACH_END)
                block_body = content[start_idx:end_idx].strip()
                personality = bool(block_body)
        status["personality"] = personality

        # mcp + skills - parse config.toml
        mcp_ok = False
        skills_ok = False

        if self.codex_config_path.exists():
            try:
                config = tomlkit.parse(self.codex_config_path.read_text(encoding="utf-8"))
            except Exception:
                config = None

            if config is not None:
                servers = config.get("mcp_servers")
                mcp_ok = bool(servers)

                skills_config = config.get("skills", {}).get("config", {})
                if skills_config:
                    skills_ok = all(
                        (self.project_dir / entry["path"]).exists()
                        for entry in skills_config.values()
                        if "path" in entry
                    )

        status["mcp"] = mcp_ok
        status["skills"] = skills_ok

        # tools - merge [tools] web_search = true into ~/.codex/config.toml
        # (native web search for research-goal-plan / setup-coach-personality;
        # Bash/exec is native and needs no config)
        config = self._load_codex_config()
        tools = config.setdefault("tools", tomlkit.table())
        tools["web_search"] = True
        self._write_codex_config(config)
        status["tools"] = config["tools"].get("web_search") is True

        return status

    # ------------------------------------------------------------------
    # config.toml helpers
    # ------------------------------------------------------------------

    def _load_codex_config(self) -> tomlkit.TOMLDocument:
        if self.codex_config_path.exists():
            return tomlkit.parse(self.codex_config_path.read_text(encoding="utf-8"))
        return tomlkit.document()

    def _write_codex_config(self, config: tomlkit.TOMLDocument) -> None:
        self.codex_config_path.parent.mkdir(parents=True, exist_ok=True)
        self.codex_config_path.write_text(tomlkit.dumps(config), encoding="utf-8")


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
