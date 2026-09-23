"""Tests for scoring logic: boundaries, direction, windows, missing data."""
from release_mgmt.models import MetricDef, Reading, Release
from release_mgmt.scoring import (
    HIT, MARGINAL, MISS, NO_DATA,
    pct_of_target, score_metric, score_release, verdict_for, window_for,
)


def _release(**kw):
    base = dict(id="r1", name="R", version="1.0", ship_date="2026-01-01",
                owner="O", hypothesis="H")
    base.update(kw)
    return Release(**base)


def _readings(values, start_day=2, release_id="r1", metric="m"):
    return [
        Reading(release_id=release_id, metric_name=metric,
                date=f"2026-01-{day:02d}", value=v)
        for day, v in zip(range(start_day, start_day + len(values)), values)
    ]


# -- verdict boundaries -------------------------------------------------
def test_hit_at_exactly_100_pct():
    assert verdict_for(100.0) == HIT


def test_hit_above_100():
    assert verdict_for(104.8) == HIT


def test_marginal_just_below_100():
    assert verdict_for(99.9) == MARGINAL


def test_marginal_at_floor():
    assert verdict_for(90.0) == MARGINAL


def test_miss_below_floor():
    assert verdict_for(89.9) == MISS


def test_no_data_verdict():
    assert verdict_for(None) == NO_DATA


# -- direction ----------------------------------------------------------
def test_increase_direction():
    assert pct_of_target("increase", 4.0, 4.0) == 100.0
    assert pct_of_target("increase", 4.0, 5.0) == 125.0
    assert pct_of_target("increase", 4.0, 3.0) == 75.0


def test_decrease_direction():
    # lower is better: target/observed
    assert pct_of_target("decrease", 95.0, 95.0) == 100.0
    assert pct_of_target("decrease", 95.0, 90.0) > 100.0   # beat the target
    assert pct_of_target("decrease", 95.0, 100.0) < 100.0  # missed it


# -- windows ------------------------------------------------------------
def test_window_for():
    release = _release(ship_date="2026-03-10")
    start, end = window_for(release, MetricDef("m", 1.0, "increase", 14))
    assert (start, end) == ("2026-03-10", "2026-03-24")


def test_readings_outside_window_are_ignored():
    release = _release(metrics=[MetricDef("m", 10.0, "increase", 14)])
    readings = [
        Reading("r1", "m", "2025-12-31", 100.0),  # before ship
        Reading("r1", "m", "2026-01-05", 10.0),
        Reading("r1", "m", "2026-01-06", 10.0),
        Reading("r1", "m", "2026-02-01", 100.0),  # after window
    ]
    result = score_release(release, readings)
    assert result.metrics[0].observed == 10.0
    assert result.metrics[0].n_readings == 2
    assert result.metrics[0].verdict == HIT


def test_ship_day_reading_counts():
    release = _release(metrics=[MetricDef("m", 10.0, "increase", 14)])
    readings = [Reading("r1", "m", "2026-01-01", 10.0)]
    result = score_release(release, readings)
    assert result.metrics[0].n_readings == 1


# -- missing data -------------------------------------------------------
def test_metric_with_no_readings_is_no_data():
    release = _release(metrics=[MetricDef("m", 10.0, "increase", 14)])
    result = score_release(release, readings=[])
    m = result.metrics[0]
    assert m.verdict == NO_DATA
    assert m.observed is None
    assert m.pct_of_target is None
    assert result.score is None
    assert result.verdict == NO_DATA


def test_no_data_metric_excluded_from_score():
    release = _release(metrics=[
        MetricDef("a", 10.0, "increase", 14),
        MetricDef("b", 10.0, "increase", 14),
    ])
    readings = _readings([10.0, 10.0], metric="a")
    result = score_release(release, readings)
    assert result.metrics[0].verdict == HIT
    assert result.metrics[1].verdict == NO_DATA
    assert result.score == 100.0  # only the metric with data counts


# -- release-level verdicts ---------------------------------------------
def test_release_verdict_all_hit():
    release = _release(metrics=[
        MetricDef("a", 10.0, "increase", 14),
        MetricDef("b", 10.0, "decrease", 14),
    ])
    readings = _readings([10.0], metric="a") + _readings([9.0], metric="b")
    result = score_release(release, readings)
    assert result.verdict == HIT


def test_release_verdict_marginal_when_no_miss():
    release = _release(metrics=[
        MetricDef("a", 100.0, "increase", 14),  # 95 -> marginal
        MetricDef("b", 100.0, "increase", 14),  # 100 -> hit
    ])
    readings = _readings([95.0], metric="a") + _readings([100.0], metric="b")
    result = score_release(release, readings)
    assert result.verdict == MARGINAL
    assert result.score == 97.5


def test_release_verdict_miss_when_any_miss():
    release = _release(metrics=[
        MetricDef("a", 100.0, "increase", 14),  # 80 -> miss
        MetricDef("b", 100.0, "increase", 14),  # 120 -> hit
    ])
    readings = _readings([80.0], metric="a") + _readings([120.0], metric="b")
    result = score_release(release, readings)
    assert result.verdict == MISS


def test_observed_is_mean_of_in_window_readings():
    release = _release(metrics=[MetricDef("m", 10.0, "increase", 14)])
    readings = _readings([8.0, 12.0])
    result = score_release(release, readings)
    assert result.metrics[0].observed == 10.0
    assert result.metrics[0].verdict == HIT
