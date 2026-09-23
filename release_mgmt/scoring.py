"""Scoring: compare observed in-window metric values against their targets.

Rules (deliberately simple and explainable):
  - observed = mean of readings inside [ship_date, ship_date + window_days]
  - % of target achieved:
      increase -> observed / target * 100
      decrease -> target / observed * 100   (lower is better)
  - verdict:  hit >= 100% | marginal 90-99.9% | miss < 90% | no-data
  - release score = mean % of target across metrics that have data
  - release verdict: hit if every metric hit; marginal if no misses but at
    least one marginal; miss otherwise; no-data if nothing has data.
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import date, timedelta

from .models import MetricDef, Reading, Release
from .sources import MetricSource

HIT = "hit"
MARGINAL = "marginal"
MISS = "miss"
NO_DATA = "no-data"

MARGINAL_FLOOR_PCT = 90.0


@dataclass
class MetricScore:
    metric_name: str
    target: float
    direction: str
    window_days: int
    observed: float | None
    n_readings: int
    pct_of_target: float | None
    verdict: str


@dataclass
class ReleaseScore:
    release_id: str
    metrics: list[MetricScore]
    score: float | None  # mean % of target over metrics with data
    verdict: str


def window_for(release: Release, metric: MetricDef) -> tuple[str, str]:
    """(start, end) ISO dates for a metric's measurement window."""
    start = date.fromisoformat(release.ship_date)
    end = start + timedelta(days=metric.window_days)
    return start.isoformat(), end.isoformat()


def pct_of_target(direction: str, target: float, observed: float) -> float | None:
    if direction == "increase":
        return (observed / target * 100) if target else None
    return (target / observed * 100) if observed else None


def verdict_for(pct: float | None) -> str:
    if pct is None:
        return NO_DATA
    if pct >= 100:
        return HIT
    if pct >= MARGINAL_FLOOR_PCT:
        return MARGINAL
    return MISS


def score_metric(metric: MetricDef, readings: list[Reading]) -> MetricScore:
    """Score one metric from its (already window-filtered) readings."""
    if not readings:
        return MetricScore(metric.name, metric.target, metric.direction,
                           metric.window_days, None, 0, None, NO_DATA)
    observed = sum(r.value for r in readings) / len(readings)
    pct = pct_of_target(metric.direction, metric.target, observed)
    return MetricScore(
        metric_name=metric.name,
        target=metric.target,
        direction=metric.direction,
        window_days=metric.window_days,
        observed=observed,
        n_readings=len(readings),
        pct_of_target=pct,
        verdict=verdict_for(pct),
    )


def score_release(
    release: Release,
    readings: list[Reading],
    extra_sources: tuple[MetricSource, ...] = (),
) -> ReleaseScore:
    """Score a release. `readings` are stored readings; `extra_sources` are
    queried per metric window and merged in (dedup not attempted -- use one
    or the other per metric in practice)."""
    metric_scores: list[MetricScore] = []
    for metric in release.metrics:
        start, end = window_for(release, metric)
        in_window = [
            r
            for r in readings
            if r.release_id == release.id
            and r.metric_name == metric.name
            and start <= r.date <= end
        ]
        for source in extra_sources:
            in_window.extend(source.fetch(release.id, metric.name, start, end))
        metric_scores.append(score_metric(metric, in_window))

    with_data = [m for m in metric_scores if m.pct_of_target is not None]
    score = (
        round(sum(m.pct_of_target for m in with_data) / len(with_data), 1)
        if with_data
        else None
    )
    verdicts = {m.verdict for m in metric_scores}
    if not with_data:
        verdict = NO_DATA
    elif verdicts == {HIT}:
        verdict = HIT
    elif MISS in verdicts:
        verdict = MISS
    else:
        verdict = MARGINAL
    return ReleaseScore(release.id, metric_scores, score, verdict)
