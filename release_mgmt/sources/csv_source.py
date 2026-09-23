"""CSV metric source.

Expected columns: release_id, metric_name, date, value
Dates are ISO YYYY-MM-DD. Extra columns are ignored.
"""
from __future__ import annotations

import csv

from ..models import Reading
from . import MetricSource

REQUIRED_COLUMNS = ("release_id", "metric_name", "date", "value")


class CSVSource(MetricSource):
    name = "csv"

    def __init__(self, path: str) -> None:
        self.path = path

    def fetch(
        self,
        release_id: str | None = None,
        metric_name: str | None = None,
        start: str | None = None,
        end: str | None = None,
    ) -> list[Reading]:
        readings: list[Reading] = []
        with open(self.path, newline="", encoding="utf-8") as f:
            reader = csv.DictReader(f)
            missing = [c for c in REQUIRED_COLUMNS if c not in (reader.fieldnames or [])]
            if missing:
                raise ValueError(
                    f"{self.path}: missing required column(s): {', '.join(missing)}"
                )
            for row in reader:
                reading = Reading(
                    release_id=row["release_id"].strip(),
                    metric_name=row["metric_name"].strip(),
                    date=row["date"].strip(),
                    value=float(row["value"]),
                )
                if release_id is not None and reading.release_id != release_id:
                    continue
                if metric_name is not None and reading.metric_name != metric_name:
                    continue
                if start is not None and reading.date < start:
                    continue
                if end is not None and reading.date > end:
                    continue
                readings.append(reading)
        return readings
