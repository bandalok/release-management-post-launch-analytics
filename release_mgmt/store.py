"""JSON-backed store. Releases and readings live in a single JSON file,
defaulting to .release_mgmt/data.json under the current working directory.
Override with --data-dir on the CLI or the data_dir argument here.
"""
from __future__ import annotations

import json
import os

from .models import (
    Reading,
    Release,
    reading_from_dict,
    reading_to_dict,
    release_from_dict,
    release_to_dict,
)

DEFAULT_DIRNAME = ".release_mgmt"
DATA_FILENAME = "data.json"


class Store:
    def __init__(self, data_dir: str | None = None) -> None:
        self.data_dir = data_dir or os.path.join(os.getcwd(), DEFAULT_DIRNAME)
        self.path = os.path.join(self.data_dir, DATA_FILENAME)
        self._data: dict = {"releases": {}, "readings": []}
        self._load()

    # -- persistence ----------------------------------------------------
    def _load(self) -> None:
        if os.path.exists(self.path):
            with open(self.path, encoding="utf-8") as f:
                self._data = json.load(f)

    def save(self) -> None:
        os.makedirs(self.data_dir, exist_ok=True)
        with open(self.path, "w", encoding="utf-8") as f:
            json.dump(self._data, f, indent=2)

    def reset(self) -> None:
        self._data = {"releases": {}, "readings": []}
        self.save()

    # -- releases -------------------------------------------------------
    def add_release(self, release: Release) -> None:
        if release.id in self._data["releases"]:
            raise ValueError(f"release {release.id!r} already exists")
        self._data["releases"][release.id] = release_to_dict(release)
        self.save()

    def get_release(self, release_id: str) -> Release:
        try:
            return release_from_dict(self._data["releases"][release_id])
        except KeyError:
            raise KeyError(f"unknown release {release_id!r}") from None

    def list_releases(self) -> list[Release]:
        return [release_from_dict(r) for r in self._data["releases"].values()]

    # -- readings -------------------------------------------------------
    def add_reading(self, reading: Reading) -> None:
        if reading.release_id not in self._data["releases"]:
            raise KeyError(f"unknown release {reading.release_id!r}")
        known = {m["name"] for m in self._data["releases"][reading.release_id]["metrics"]}
        if reading.metric_name not in known:
            raise KeyError(
                f"release {reading.release_id!r} has no metric {reading.metric_name!r}"
            )
        self._data["readings"].append(reading_to_dict(reading))
        self.save()

    def readings_for(self, release_id: str, metric_name: str | None = None) -> list[Reading]:
        out = []
        for raw in self._data["readings"]:
            if raw["release_id"] != release_id:
                continue
            if metric_name is not None and raw["metric_name"] != metric_name:
                continue
            out.append(reading_from_dict(raw))
        return out
