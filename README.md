Release management and post-release data analysis for product managers.

# release-management-post-launch-analytics

Most teams ship releases and never close the loop. This tool makes the loop
unavoidable: every release declares its **hypothesis and success metrics up
front**, then post-release data is scored against those targets to produce a
structured **post-launch review**.

The core idea is simple and deliberately PM-shaped: a release is a bet. Write
down what you believe and what would prove it *before* you ship. After the
measurement window, the data renders the verdict — hit, marginal, or miss —
and the review template captures what you learned. No more launches that
quietly fade into "we think it went fine."

## Quickstart

Zero third-party dependencies — stdlib only. Python 3.10+.

```bash
python -m release_mgmt load-demo
python -m release_mgmt score
python -m release_mgmt report --release checkout-redesign
```

That loads three fictional releases with synthetic post-launch data, scores
them against their declared targets, and prints/saves a Markdown post-launch
review to `reports/checkout-redesign.md`.

## How scoring works

For each metric, the observed value is the **mean of readings inside the
measurement window** (`ship_date` through `ship_date + window_days`). Readings
outside the window are ignored.

- **% of target achieved:** `observed / target × 100` for `increase` metrics,
  `target / observed × 100` for `decrease` metrics.
- **Verdicts:** `hit` at 100%+, `marginal` at 90–99.9%, `miss` below 90%,
  `no-data` when nothing was recorded in the window.
- **Release score:** mean % of target across metrics with data. A release is
  `hit` only if every metric hit; `marginal` if nothing missed but something
  was marginal; `miss` otherwise.

## Full CLI

```bash
# Register a release (hypothesis + metrics declared BEFORE launch)
python -m release_mgmt add-release --id v2.5 --name "Search revamp" \
  --version 2.5.0 --ship-date 2026-10-01 --owner "Jane Doe" \
  --hypothesis "Faster results will lift engagement." \
  --metric "search-ctr:12.5:increase:14" \
  --metric "p95-latency-ms:400:decrease:14"

# Record observations (manual entry)
python -m release_mgmt record-metric --release v2.5 --metric search-ctr \
  --date 2026-10-05 --value 13.1

# Or bulk-import: columns release_id,metric_name,date,value
python -m release_mgmt import-csv --file metrics.csv

# Score one release or all of them
python -m release_mgmt score --release v2.5

# Generate the post-launch review
python -m release_mgmt report --release v2.5 --out review.md
```

Data lives in `.release_mgmt/data.json` (plain JSON) under your working
directory; override with `--data-dir`.

## Architecture

```
                    +-----------------+
                    |   CLI / scripts |
                    +--------+--------+
                             |
              +--------------+--------------+
              |              |              |
     +--------v------+ +-----v------+ +-----v-------+
     |    models     | |   store    | |   scoring   |
     | Release,      | | JSON file  | | window mean |
     | MetricDef,    | | read/write | | % of target |
     | Reading       | |            | | verdicts    |
     +---------------+ +-----+------+ +-------------+
                             |
                    +--------v--------+
                    |  sources/       |  <-- plugin seam
                    |  MetricSource   |      (ABC)
                    |  +- manual      |
                    |  +- csv        |
                    |  +- your API --+-- subclass + register,
                    +----------------+   no core changes
```

Scoring and reports only ever talk to the `MetricSource` interface. Storage,
scoring, and reporting never import a concrete source.

## Adding a metric source (plugin API)

Subclass `MetricSource` and register it — no core code changes:

```python
from release_mgmt.models import Reading
from release_mgmt.sources import MetricSource, SOURCES

class WarehouseSource(MetricSource):
    name = "warehouse"

    def fetch(self, release_id, metric_name, start, end):
        rows = query_warehouse(release_id, metric_name, start, end)  # your code
        return [Reading(release_id, metric_name, d, v) for d, v in rows]

SOURCES["warehouse"] = WarehouseSource
```

Then pass instances to `score_release(release, readings, extra_sources=(WarehouseSource(),))`.
Built in: `manual` (in-memory, handy for scripts/tests) and `csv`
(`release_id,metric_name,date,value` columns).

## Static dashboard (GitHub Pages)

`docs/index.html` is a self-contained dashboard (inline CSS, vanilla JS, no
CDN, works offline) that renders the demo dataset as post-launch review
cards. To publish it:

1. Push this repo to GitHub.
2. Go to **Settings → Pages**.
3. Under **Build and deployment**, set **Source** to *Deploy from a branch*,
   **Branch** to `main`, folder to `/docs`.
4. Save — the dashboard goes live at
   `https://<your-username>.github.io/release-management-post-launch-analytics/`.

## Project layout

```
release_mgmt/            Python package (stdlib only)
  __main__.py            CLI: add-release, record-metric, import-csv, score, report, load-demo
  models.py              Release, MetricDef, Reading
  store.py               JSON-backed storage
  scoring.py             window means, % of target, verdicts
  report.py              Markdown post-launch review renderer
  sources/               MetricSource ABC + registry; manual + csv built in
demo/                    Synthetic dataset: 3 releases, 51 readings
docs/index.html          Static dashboard for GitHub Pages
tests/                   pytest suite (scoring, sources, store, report, CLI)
```

## Why this exists

Release management is usually process theater: checklists, sign-offs, and a
launch email. Post-release data analysis is usually archaeology: digging
through dashboards weeks later trying to remember what "success" meant. This
project connects them with one habit — declare the bet before you ship, score
it after — in a tool small enough to read in ten minutes.

Built by Alok Band. MIT licensed — see LICENSE.
