"""CLI smoke test: load-demo -> score -> report, end to end."""
import subprocess
import sys

PROJECT_ROOT = __import__("os").path.dirname(
    __import__("os").path.dirname(__import__("os").path.abspath(__file__))
)


def run_cli(tmp_path, *argv):
    return subprocess.run(
        [sys.executable, "-m", "release_mgmt", *argv],
        cwd=tmp_path,
        capture_output=True,
        text=True,
        env={**__import__("os").environ, "PYTHONPATH": PROJECT_ROOT},
    )


def test_cli_end_to_end(tmp_path):
    demo = run_cli(tmp_path, "load-demo")
    assert demo.returncode == 0, demo.stderr
    assert "3 demo release(s)" in demo.stdout

    score = run_cli(tmp_path, "score")
    assert score.returncode == 0, score.stderr
    assert "checkout-redesign" in score.stdout
    assert "pricing-experiment" in score.stdout
    assert "onboarding-flow" in score.stdout

    report = run_cli(tmp_path, "report", "--release", "checkout-redesign")
    assert report.returncode == 0, report.stderr
    assert "Post-launch review" in report.stdout
    assert (tmp_path / "reports" / "checkout-redesign.md").exists()


def test_cli_add_release_and_record_metric(tmp_path):
    add = run_cli(
        tmp_path, "add-release",
        "--id", "r1", "--name", "Test", "--version", "0.1",
        "--ship-date", "2026-01-01", "--owner", "QA",
        "--hypothesis", "It works.",
        "--metric", "conv:5.0:increase:14",
    )
    assert add.returncode == 0, add.stderr

    rec = run_cli(
        tmp_path, "record-metric",
        "--release", "r1", "--metric", "conv",
        "--date", "2026-01-05", "--value", "5.0",
    )
    assert rec.returncode == 0, rec.stderr

    score = run_cli(tmp_path, "score", "--release", "r1")
    assert score.returncode == 0, score.stderr
    assert "HIT" in score.stdout
