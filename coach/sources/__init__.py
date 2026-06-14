"""Source package — importing this module registers all source specs.

Each ``coach.sources.<name>`` module defines a ``SOURCE_SPEC`` and calls
``coach.sources.registry.register(SOURCE_SPEC)`` as a side-effect of being
imported. Importing ``coach.sources.registry`` alone does *not* populate
``registry.SOURCES`` — the individual source modules must be imported too.
This module does that, so ``import coach.sources`` (or anything that imports
a submodule of this package) is sufficient to fully populate
``coach.sources.registry.SOURCES``.
"""

from coach.sources import (  # noqa: F401
    garmin,
    google_calendar,
    outlook_calendar,
    strava,
)

__all__ = ["garmin", "strava", "google_calendar", "outlook_calendar"]
