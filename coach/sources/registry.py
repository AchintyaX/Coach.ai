from coach.sources.base import CAPABILITIES, ROLES, SourceSpec

SOURCES: dict[str, SourceSpec] = {}


def register(spec: SourceSpec) -> None:
    """Register a SourceSpec into SOURCES, keyed by spec.name."""
    if not spec.capabilities <= CAPABILITIES:
        raise ValueError(
            f"Invalid capabilities for source {spec.name!r}: "
            f"{spec.capabilities - CAPABILITIES}"
        )
    if not spec.roles <= ROLES:
        raise ValueError(
            f"Invalid roles for source {spec.name!r}: {spec.roles - ROLES}"
        )
    SOURCES[spec.name] = spec


def get(name: str) -> SourceSpec | None:
    return SOURCES.get(name)


def resolve_capabilities(specs: list[SourceSpec]) -> set[str]:
    """Union of .capabilities across all given specs."""
    result: set[str] = set()
    for spec in specs:
        result |= spec.capabilities
    return result


def resolve_roles(specs: list[SourceSpec]) -> set[str]:
    """Union of .roles across all given specs."""
    result: set[str] = set()
    for spec in specs:
        result |= spec.roles
    return result
