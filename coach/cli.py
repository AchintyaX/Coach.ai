"""``coach`` CLI — setup, configuration, and harness installation.

Subcommands (techspec section 9):

- ``coach setup --source <name> [--credentials ...] [--tenant-id ...] [--client-id ...]``
  Looks up ``<name>`` in ``coach.sources.registry.SOURCES``, prints its
  ``auth_steps`` as guidance, and records the source as "configured" for
  this project in ``./.coach/config.json``.

- ``coach setup --schedule``
  Interactively prompts for the daily run time, then writes all three
  local-only scheduling artifacts from ``coach.scheduling``.

- ``coach setup --schedule-time "<time>"``
  Same as ``--schedule`` but non-interactive.

- ``coach install --harness claude|codex|all``
  Resolves the active capability set from configured sources and installs
  the coach personality, MCP server registrations, and skills into the
  requested harness(es).

Config file format — ``./.coach/config.json``::

    {
      "sources": {
        "garmin": {},
        "google_calendar": {"credentials": "./gcp-oauth.keys.json"},
        "outlook_calendar": {"tenant_id": "...", "client_id": "..."}
      }
    }

``sources`` maps source name -> a dict of extra per-source params captured
from ``--credentials``/``--tenant-id``/``--client-id``. An empty dict means
"configured with no extra params". Re-running ``coach setup --source <name>``
is idempotent: it merges any newly-provided extra params into the existing
entry rather than duplicating it.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

import coach.sources  # noqa: F401 - populates registry.SOURCES via side-effects
from coach.harness.claude import ClaudeHarness
from coach.harness.codex import CodexHarness
from coach.scheduling import (
    parse_time_of_day,
    write_claude_scheduled_task,
    write_codex_automation,
    write_cron_fallback,
)
from coach.sources import registry

CONFIG_DIR_NAME = ".coach"
CONFIG_FILE_NAME = "config.json"

PERSONALITY_PATH = Path(__file__).parent / "prompts" / "coach_personality.md"
SKILLS_DIR = Path(__file__).parent.parent / "skills"


# ---------------------------------------------------------------------------
# Config file helpers
# ---------------------------------------------------------------------------


def _config_path(project_dir: Path) -> Path:
    return project_dir / CONFIG_DIR_NAME / CONFIG_FILE_NAME


def load_config(project_dir: Path) -> dict:
    """Load ``./.coach/config.json``, returning ``{"sources": {}}`` if absent."""
    path = _config_path(project_dir)
    if not path.exists():
        return {"sources": {}}
    data = json.loads(path.read_text(encoding="utf-8"))
    data.setdefault("sources", {})
    return data


def save_config(project_dir: Path, config: dict) -> Path:
    path = _config_path(project_dir)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(config, indent=2) + "\n", encoding="utf-8")
    return path


# ---------------------------------------------------------------------------
# coach setup --source <name>
# ---------------------------------------------------------------------------


def setup_source(
    name: str,
    project_dir: Path | None = None,
    credentials: str | None = None,
    tenant_id: str | None = None,
    client_id: str | None = None,
) -> Path:
    """Record ``name`` as a configured source for ``project_dir``.

    Prints the source's ``auth_steps`` (prefixed ``"-> "``) as guidance,
    then writes/merges an entry in ``./.coach/config.json``. Raises
    ``ValueError`` if ``name`` is not a known source.
    """
    project_dir = project_dir or Path.cwd()

    spec = registry.get(name)
    if spec is None:
        known = ", ".join(sorted(registry.SOURCES)) or "(none registered)"
        raise ValueError(f"Unknown source {name!r}. Known sources: {known}")

    for step in spec.auth_steps:
        print(f"→ {step}")

    config = load_config(project_dir)
    extra = config["sources"].setdefault(name, {})

    if credentials is not None:
        extra["credentials"] = credentials
    if tenant_id is not None:
        extra["tenant_id"] = tenant_id
    if client_id is not None:
        extra["client_id"] = client_id

    return save_config(project_dir, config)


# ---------------------------------------------------------------------------
# coach setup --schedule / --schedule-time
# ---------------------------------------------------------------------------


def setup_schedule(
    time_str: str,
    project_dir: Path | None = None,
    home: Path | None = None,
) -> dict[str, Path]:
    """Parse ``time_str`` and write all three local-only scheduling artifacts.

    Returns a dict mapping artifact name -> written path.
    """
    project_dir = project_dir or Path.cwd()

    t = parse_time_of_day(time_str)

    return {
        "claude_scheduled_task": write_claude_scheduled_task(t, project_dir, home=home),
        "codex_automation": write_codex_automation(t, project_dir),
        "cron_fallback": write_cron_fallback(t, project_dir, home=home),
    }


def setup_schedule_interactive(
    project_dir: Path | None = None,
    home: Path | None = None,
) -> dict[str, Path]:
    """Prompt the user for a daily run time, then write scheduling artifacts."""
    time_str = input(
        "What time should I run your daily readiness check + workout generation? "
    )
    return setup_schedule(time_str, project_dir=project_dir, home=home)


# ---------------------------------------------------------------------------
# coach install --harness claude|codex|all
# ---------------------------------------------------------------------------


def _configured_specs(project_dir: Path) -> list:
    """Return the list of SourceSpecs for sources configured in ``project_dir``."""
    config = load_config(project_dir)
    names = list(config["sources"].keys())

    if not names:
        raise ValueError(
            "No sources configured. Run `coach setup --source <name>` first "
            f"(known sources: {', '.join(sorted(registry.SOURCES)) or '(none registered)'})."
        )

    specs = []
    for name in names:
        spec = registry.get(name)
        if spec is None:
            raise ValueError(
                f"Configured source {name!r} is not a known source "
                f"(known sources: {', '.join(sorted(registry.SOURCES))})."
            )
        specs.append(spec)

    return specs


def _install_one(harness, specs: list, capabilities: set[str]) -> dict[str, bool]:
    personality_text = PERSONALITY_PATH.read_text(encoding="utf-8")

    harness.install_personality(personality_text)

    for spec in specs:
        harness.setup_source(spec)

    harness.install_skills(SKILLS_DIR, capabilities)

    return harness.verify()


def install(
    harness_name: str,
    project_dir: Path | None = None,
    home: Path | None = None,
) -> dict[str, dict[str, bool]]:
    """Install Coach AI into the requested harness(es).

    ``harness_name`` is one of ``"claude"``, ``"codex"``, or ``"all"``.
    Returns a dict mapping harness name -> ``verify()`` status map.
    """
    project_dir = project_dir or Path.cwd()

    specs = _configured_specs(project_dir)
    capabilities = registry.resolve_capabilities(specs)

    results: dict[str, dict[str, bool]] = {}

    if harness_name in ("claude", "all"):
        claude_harness = ClaudeHarness(project_dir)
        results["claude"] = _install_one(claude_harness, specs, capabilities)

    if harness_name in ("codex", "all"):
        codex_harness = CodexHarness(project_dir, home=home)
        results["codex"] = _install_one(codex_harness, specs, capabilities)

    return results


def _print_install_results(results: dict[str, dict[str, bool]]) -> None:
    for harness_name, status in results.items():
        print(f"{harness_name}:")
        for key, ok in status.items():
            print(f"  {key}: {'ok' if ok else 'FAILED'}")


# ---------------------------------------------------------------------------
# argparse wiring
# ---------------------------------------------------------------------------


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="coach", description="Coach AI setup and installation CLI.")
    subparsers = parser.add_subparsers(dest="command", required=True)

    setup_parser = subparsers.add_parser("setup", help="Configure sources and scheduling.")
    setup_parser.add_argument("--source", help="Name of a source to configure (e.g. garmin, strava).")
    setup_parser.add_argument("--credentials", help="Path to OAuth credentials file (e.g. gcp-oauth.keys.json).")
    setup_parser.add_argument("--tenant-id", help="Azure tenant ID (for outlook_calendar).")
    setup_parser.add_argument("--client-id", help="Azure client ID (for outlook_calendar).")
    setup_parser.add_argument(
        "--schedule",
        action="store_true",
        help="Interactively configure the daily readiness check + workout generation schedule.",
    )
    setup_parser.add_argument(
        "--schedule-time",
        help='Non-interactively configure the daily schedule, e.g. "7:00 AM".',
    )

    install_parser = subparsers.add_parser("install", help="Install Coach AI into an agent harness.")
    install_parser.add_argument(
        "--harness",
        required=True,
        choices=["claude", "codex", "all"],
        help="Which harness(es) to install into.",
    )

    return parser


def _run_setup(args: argparse.Namespace) -> int:
    project_dir = Path.cwd()

    if args.source:
        try:
            path = setup_source(
                args.source,
                project_dir=project_dir,
                credentials=args.credentials,
                tenant_id=args.tenant_id,
                client_id=args.client_id,
            )
        except ValueError as exc:
            print(f"error: {exc}", file=sys.stderr)
            return 1
        print(f"Configured source {args.source!r} -> {path}")
        return 0

    if args.schedule_time:
        try:
            written = setup_schedule(args.schedule_time, project_dir=project_dir)
        except ValueError as exc:
            print(f"error: {exc}", file=sys.stderr)
            return 1
        for key, path in written.items():
            print(f"{key}: {path}")
        return 0

    if args.schedule:
        try:
            written = setup_schedule_interactive(project_dir=project_dir)
        except ValueError as exc:
            print(f"error: {exc}", file=sys.stderr)
            return 1
        for key, path in written.items():
            print(f"{key}: {path}")
        return 0

    print(
        "error: nothing to do. Use --source <name>, --schedule, or --schedule-time \"<time>\".",
        file=sys.stderr,
    )
    return 1


def _run_install(args: argparse.Namespace) -> int:
    project_dir = Path.cwd()

    try:
        results = install(args.harness, project_dir=project_dir)
    except ValueError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 1

    _print_install_results(results)
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)

    if args.command == "setup":
        return _run_setup(args)
    if args.command == "install":
        return _run_install(args)

    parser.print_help()
    return 1


if __name__ == "__main__":
    sys.exit(main())
