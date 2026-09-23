"""Pluggable metric sources.

Core logic (scoring, reports) never imports a concrete source -- it only
talks to MetricSource. To add a real API connector later (Mixpanel,
Amplitude, your warehouse), subclass MetricSource and register it:

    from release_mgmt.sources import MetricSource, SOURCES

    class MixpanelSource(MetricSource):
        name = "mixpanel"
        def fetch(self, release_id, metric_name, start, end):
            ...  # return [Reading, ...]
            return readings

    SOURCES["mixpanel"] = MixpanelSource

No core code changes needed.
"""
from __future__ import annotations

import abc

from ..models import Reading

#: Registry of built-in and third-party sources, keyed by name.
SOURCES: dict[str, type["MetricSource"]] = {}


class MetricSource(abc.ABC):
    """Produces metric readings for a release inside a date window."""

    name = "base"

    @abc.abstractmethod
    def fetch(
        self,
        release_id: str | None,
        metric_name: str | None,
        start: str | None,
        end: str | None,
    ) -> list[Reading]:
        """Return readings whose dates fall between start and end (ISO strings,
        inclusive). Any filter may be None to mean "no filter"."""


class ManualSource(MetricSource):
    """In-memory source: useful for scripts, notebooks, and tests."""

    name = "manual"

    def __init__(self, readings: tuple[Reading, ...] | list[Reading] = ()) -> None:
        self._readings = list(readings)

    def add(self, reading: Reading) -> None:
        self._readings.append(reading)

    def fetch(
        self,
        release_id: str | None,
        metric_name: str | None,
        start: str | None,
        end: str | None,
    ) -> list[Reading]:
        return [
            r
            for r in self._readings
            if (release_id is None or r.release_id == release_id)
            and (metric_name is None or r.metric_name == metric_name)
            and (start is None or r.date >= start)
            and (end is None or r.date <= end)
        ]


SOURCES["manual"] = ManualSource

from .csv_source import CSVSource  # noqa: E402

SOURCES["csv"] = CSVSource
