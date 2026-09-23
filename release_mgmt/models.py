"""Data models. Plain dataclasses, stdlib only."""
from __future__ import annotations

from dataclasses import asdict, dataclass, field
from datetime import date


@dataclass
class MetricDef:
    """A success metric declared BEFORE launch.

    direction: "increase" means observed >= target is good;
               "decrease" means observed <= target is good.
    window_days: how many days after ship_date count toward the score.
    """

    name: str
    target: float
    direction: str = "increase"
    window_days: int = 14

    def __post_init__(self) -> None:
        if self.direction not in ("increase", "decrease"):
            raise ValueError(
                f"direction must be 'increase' or 'decrease', got {self.direction!r}"
            )
        if self.window_days <= 0:
            raise ValueError("window_days must be a positive integer")


@dataclass
class Release:
    """A shipped release with a falsifiable hypothesis."""

    id: str
    name: str
    version: str
    ship_date: str  # ISO YYYY-MM-DD
    owner: str
    hypothesis: str
    metrics: list[MetricDef] = field(default_factory=list)

    def __post_init__(self) -> None:
        date.fromisoformat(self.ship_date)  # validates the format


@dataclass
class Reading:
    """One observed value of a metric on a date."""

    release_id: str
    metric_name: str
    date: str  # ISO YYYY-MM-DD
    value: float

    def __post_init__(self) -> None:
        date.fromisoformat(self.date)  # validates the format


def release_to_dict(release: Release) -> dict:
    return asdict(release)


def release_from_dict(data: dict) -> Release:
    return Release(
        id=data["id"],
        name=data["name"],
        version=data["version"],
        ship_date=data["ship_date"],
        owner=data["owner"],
        hypothesis=data["hypothesis"],
        metrics=[MetricDef(**m) for m in data.get("metrics", [])],
    )


def reading_to_dict(reading: Reading) -> dict:
    return asdict(reading)


def reading_from_dict(data: dict) -> Reading:
    return Reading(**data)
