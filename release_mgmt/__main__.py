"""CLI: python -m release_mgmt <command> [options]

Commands:
  add-release    Register a release with hypothesis + success metrics
  record-metric  Record one observed metric value
  import-csv     Import readings from a CSV file
  score          Score releases against their targets
  report         Print/save a post-launch review (Markdown)
  load-demo      Load the bundled synthetic demo dataset
"""
from __future__ import annotations

import argparse
import json
import os
import sys

from .models import MetricDef, Reading, Release
from .report import render_report, write_report
from .scoring import score_release, window_for
from .sources import SOURCES
from .store import Store

DEMO_FILENAMES = ("releases.json", "metrics.csv")


def find_demo_dir() -> str:
    """Look for demo/ next to cwd, then next to the project root."""
    candidates = [
        os.path.join(os.getcwd(), "demo"),
        os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "demo"),
    ]
    for path in candidates:
        if all(os.path.exists(os.path.join(path, f)) for f in DEMO_FILENAMES):
            return path
    raise FileNotFoundError("demo/ dataset not found (looked next to cwd and the package)")


def parse_metric(spec: str) -> MetricDef:
    """Parse 'name:target:direction[:window_days]', e.g. 'conv-rate:4.5:increase:14'."""
    parts = spec.split(":")
    if len(parts) < 3:
        raise ValueError(
            f"bad --metric {spec!r}; expected name:target:direction[:window_days]"
        )
    name, target, direction = parts[0], float(parts[1]), parts[2]
    window_days = int(parts[3]) if len(parts) > 3 else 14
    return MetricDef(name=name, target=target, direction=direction, window_days=window_days)


def cmd_add_release(args, store: Store) -> None:
    release = Release(
        id=args.id,
        name=args.name,
        version=args.version,
        ship_date=args.ship_date,
        owner=args.owner,
        hypothesis=args.hypothesis,
        metrics=[parse_metric(m) for m in args.metric],
    )
    store.add_release(release)
    print(f"added release {release.id} with {len(release.metrics)} metric(s)")


def cmd_record_metric(args, store: Store) -> None:
    store.add_reading(
        Reading(
            release_id=args.release,
            metric_name=args.metric,
            date=args.date,
            value=float(args.value),
        )
    )
    print(f"recorded {args.metric}={args.value} on {args.date} for {args.release}")


def cmd_import_csv(args, store: Store) -> None:
    source_cls = SOURCES["csv"]
    readings = source_cls(args.file).fetch(None, None, None, None)
    for reading in readings:
        store.add_reading(reading)
    print(f"imported {len(readings)} reading(s) from {args.file}")


def _score_all(store: Store) -> list:
    return [
        (release, score_release(release, store.readings_for(release.id)))
        for release in store.list_releases()
    ]


def cmd_score(args, store: Store) -> None:
    scored = _score_all(store)
    if args.release:
        scored = [(r, s) for r, s in scored if r.id == args.release]
        if not scored:
            raise KeyError(f"unknown release {args.release!r}")
    if not scored:
        print("no releases yet -- run 'load-demo' or 'add-release' first")
        return
    for release, result in scored:
        score = f"{result.score:.1f}%" if result.score is not None else "n/a"
        print(f"\n{release.name} ({release.id}) -- score {score}, verdict {result.verdict.upper()}")
        print(f"  {'metric':28} {'target':>8} {'observed':>9} {'% tgt':>7}  verdict")
        for m in result.metrics:
            observed = f"{m.observed:.2f}" if m.observed is not None else "n/a"
            pct = f"{m.pct_of_target:.1f}" if m.pct_of_target is not None else "n/a"
            print(f"  {m.metric_name:28} {m.target:>8} {observed:>9} {pct:>7}  {m.verdict}")


def cmd_report(args, store: Store) -> None:
    release = store.get_release(args.release)
    result = score_release(release, store.readings_for(release.id))
    text = render_report(release, result)
    out = args.out or os.path.join(os.getcwd(), "reports", f"{release.id}.md")
    os.makedirs(os.path.dirname(out), exist_ok=True)
    write_report(out, text)
    print(text)
    print(f"\nsaved to {out}")


def cmd_load_demo(args, store: Store) -> None:
    demo_dir = find_demo_dir()
    store.reset()
    with open(os.path.join(demo_dir, "releases.json"), encoding="utf-8") as f:
        for raw in json.load(f):
            store.add_release(
                Release(
                    id=raw["id"],
                    name=raw["name"],
                    version=raw["version"],
                    ship_date=raw["ship_date"],
                    owner=raw["owner"],
                    hypothesis=raw["hypothesis"],
                    metrics=[MetricDef(**m) for m in raw["metrics"]],
                )
            )
    readings = SOURCES["csv"](os.path.join(demo_dir, "metrics.csv")).fetch(None, None, None, None)
    for reading in readings:
        store.add_reading(reading)
    releases = store.list_releases()
    print(f"loaded {len(releases)} demo release(s), {len(readings)} reading(s):")
    for release in releases:
        print(f"  - {release.id}: {release.name} ({release.version})")


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="python -m release_mgmt",
        description="Hypothesis-driven release measurement for product managers.",
    )
    parser.add_argument("--data-dir", default=None, help="store directory (default: ./.release_mgmt)")
    sub = parser.add_subparsers(dest="command", required=True)

    p = sub.add_parser("add-release", help="register a release")
    p.add_argument("--id", required=True)
    p.add_argument("--name", required=True)
    p.add_argument("--version", required=True)
    p.add_argument("--ship-date", required=True, help="YYYY-MM-DD")
    p.add_argument("--owner", required=True)
    p.add_argument("--hypothesis", required=True)
    p.add_argument("--metric", action="append", default=[],
                   help="name:target:direction[:window_days], repeatable")
    p.set_defaults(func=cmd_add_release)

    p = sub.add_parser("record-metric", help="record one observed value")
    p.add_argument("--release", required=True)
    p.add_argument("--metric", required=True)
    p.add_argument("--date", required=True, help="YYYY-MM-DD")
    p.add_argument("--value", required=True, type=float)
    p.set_defaults(func=cmd_record_metric)

    p = sub.add_parser("import-csv", help="import readings from CSV")
    p.add_argument("--file", required=True)
    p.set_defaults(func=cmd_import_csv)

    p = sub.add_parser("score", help="score releases against targets")
    p.add_argument("--release", default=None)
    p.set_defaults(func=cmd_score)

    p = sub.add_parser("report", help="post-launch review report (Markdown)")
    p.add_argument("--release", required=True)
    p.add_argument("--out", default=None)
    p.set_defaults(func=cmd_report)

    p = sub.add_parser("load-demo", help="load the bundled synthetic demo dataset")
    p.set_defaults(func=cmd_load_demo)

    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    store = Store(data_dir=args.data_dir)
    try:
        args.func(args, store)
    except (ValueError, KeyError, FileNotFoundError) as e:
        print(f"error: {e}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
