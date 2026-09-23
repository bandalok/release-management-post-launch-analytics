"""Tests for the JSON store and the Markdown report renderer."""
import json

import pytest

from release_mgmt.models import MetricDef, Reading, Release
from release_mgmt.report import render_report
from release_mgmt.scoring import score_release
from release_mgmt.store import Store


def _release():
    return Release(
        id="r1", name="Checkout", version="2.0", ship_date="2026-01-01",
        owner="O", hypothesis="Faster checkout converts better.",
        metrics=[MetricDef("conv", 5.0, "increase", 14)],
    )


def test_store_round_trip(tmp_path):
    store = Store(data_dir=str(tmp_path))
    store.add_release(_release())
    store.add_reading(Reading("r1", "conv", "2026-01-05", 5.5))

    store2 = Store(data_dir=str(tmp_path))
    release = store2.get_release("r1")
    assert release.name == "Checkout"
    assert release.metrics[0].target == 5.0
    assert len(store2.readings_for("r1")) == 1


def test_store_rejects_duplicate_release(tmp_path):
    store = Store(data_dir=str(tmp_path))
    store.add_release(_release())
    with pytest.raises(ValueError, match="already exists"):
        store.add_release(_release())


def test_store_rejects_reading_for_unknown_release(tmp_path):
    store = Store(data_dir=str(tmp_path))
    with pytest.raises(KeyError):
        store.add_reading(Reading("nope", "conv", "2026-01-05", 1.0))


def test_store_rejects_reading_for_unknown_metric(tmp_path):
    store = Store(data_dir=str(tmp_path))
    store.add_release(_release())
    with pytest.raises(KeyError, match="no metric"):
        store.add_reading(Reading("r1", "nope", "2026-01-05", 1.0))


def test_store_file_is_plain_json(tmp_path):
    store = Store(data_dir=str(tmp_path))
    store.add_release(_release())
    with open(tmp_path / "data.json", encoding="utf-8") as f:
        raw = json.load(f)
    assert raw["releases"]["r1"]["name"] == "Checkout"


def test_report_contains_key_sections():
    release = _release()
    result = score_release(release, [Reading("r1", "conv", "2026-01-05", 5.5)])
    text = render_report(release, result)
    assert "Post-launch review" in text
    assert "Hypothesis" in text
    assert "Faster checkout converts better." in text
    assert "Metric results" in text
    assert "HIT" in text
    assert "Learnings" in text


def test_report_handles_no_data():
    release = _release()
    result = score_release(release, [])
    text = render_report(release, result)
    assert "NO DATA" in text
    assert "n/a" in text
