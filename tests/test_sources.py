"""Tests for the pluggable metric sources."""
import pytest

from release_mgmt.models import Reading
from release_mgmt.sources import SOURCES, ManualSource, MetricSource
from release_mgmt.sources.csv_source import CSVSource


def _reading(**kw):
    base = dict(release_id="r1", metric_name="m", date="2026-01-05", value=1.0)
    base.update(kw)
    return Reading(**base)


def test_manual_source_filters():
    src = ManualSource([
        _reading(metric_name="a", date="2026-01-05"),
        _reading(metric_name="b", date="2026-01-05"),
        _reading(metric_name="a", date="2026-02-01"),
    ])
    got = src.fetch("r1", "a", "2026-01-01", "2026-01-31")
    assert len(got) == 1
    assert got[0].metric_name == "a"
    assert got[0].date == "2026-01-05"


def test_manual_source_add():
    src = ManualSource()
    src.add(_reading())
    assert len(src.fetch(None, None, None, None)) == 1


def test_registry_has_builtins():
    assert SOURCES["manual"] is ManualSource
    assert SOURCES["csv"] is CSVSource


def test_third_party_source_plugs_in_without_core_changes():
    class FakeAPISource(MetricSource):
        name = "fake-api"

        def fetch(self, release_id, metric_name, start, end):
            return [_reading(release_id=release_id, metric_name=metric_name)]

    SOURCES["fake-api"] = FakeAPISource
    try:
        readings = SOURCES["fake-api"]().fetch("r9", "conv", "2026-01-01", "2026-01-31")
        assert readings[0].release_id == "r9"
    finally:
        del SOURCES["fake-api"]


def test_csv_source_reads_expected_columns(tmp_path):
    csv_file = tmp_path / "m.csv"
    csv_file.write_text(
        "release_id,metric_name,date,value\n"
        "r1,conv,2026-01-05,4.2\n"
        "r1,conv,2026-01-06,4.4\n"
        "r2,conv,2026-01-05,9.9\n"
    )
    src = CSVSource(str(csv_file))
    got = src.fetch("r1", "conv", None, None)
    assert [r.value for r in got] == [4.2, 4.4]


def test_csv_source_date_filtering(tmp_path):
    csv_file = tmp_path / "m.csv"
    csv_file.write_text(
        "release_id,metric_name,date,value\n"
        "r1,conv,2026-01-05,4.2\n"
        "r1,conv,2026-03-05,4.4\n"
    )
    src = CSVSource(str(csv_file))
    got = src.fetch("r1", "conv", "2026-01-01", "2026-01-31")
    assert len(got) == 1
    assert got[0].value == 4.2


def test_csv_source_rejects_missing_columns(tmp_path):
    csv_file = tmp_path / "bad.csv"
    csv_file.write_text("release_id,metric_name,date\nr1,conv,2026-01-05\n")
    with pytest.raises(ValueError, match="missing required column"):
        CSVSource(str(csv_file)).fetch(None, None, None, None)
