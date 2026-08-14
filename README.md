# Mars Remote Sensing Pipeline

A pipeline that collects and analyzes remote sensing observation metadata from
the PDS Geosciences Node Orbital Data Explorer (ODE):
https://ode.rsl.wustl.edu/mars/index.aspx

The first stage, documented here, downloads observation **metadata only** (no
data products) and groups it on disk by geological feature class, then feature
name, then the instrument set that produced each observation.

## Setup

The project uses [uv](https://docs.astral.sh/uv/) for the environment and
dependencies.

```bash
uv sync
```

## Download pipeline

The downloader runs from `scripts/download_metadata.py`, which holds the command
wiring and drives the `download` package under `src/`.

### Quick start

Run the small sample first. It downloads 3 features across 2 instrument sets in
a few seconds and touches nothing else:

```bash
uv run python scripts/download_metadata.py --test
```

Add `--dry-run` to any command to print the plan without querying:

```bash
uv run python scripts/download_metadata.py --test --dry-run
```

A live progress bar shows the percentage, jobs completed, estimated time
remaining, the job currently finishing, and the running row and failure counts:

```
  Ultimum Chasma [MRO/CTX/EDR]  ━━━━━━━━━━━━━━━  100.0% 25/25 00:00 4,332 rows
done in 15.5s: 25 jobs, 4,332 rows, 4 empty, 0 failed
```

Use `--quiet` to suppress the bar and print only the final summary.

### Options

| Flag | Meaning |
|---|---|
| `--feature-class CLASS [CLASS ...]` | Feature classes to download (default: all classes). |
| `--feature-name NAME [NAME ...]` | Specific feature names (overrides `--feature-class`). |
| `--instrument IHID/IID/PT [...]` | Instrument set triples (default: the built-in set). |
| `--loc {b,f,o,i}` | ODE containment mode (default: `o`, see below). |
| `--workers N` | Concurrent workers, clamped to 6 (default: 4). |
| `--min-obs-time UTC` / `--max-obs-time UTC` | Restrict by observation time, e.g. `2012-04-03`. |
| `--out DIR` | Metadata output root (default: `data/metadata`). |
| `--cache DIR` | Catalog cache directory (default: `data/_catalog`). |
| `--test` | Small sample: 3 features by 2 instrument sets. |
| `--dry-run` | Print the plan without querying. |
| `--force` | Re-download instead of skipping existing files. |
| `--refresh-catalog` | Re-fetch the feature and instrument catalogs. |
| `--quiet` | Suppress the progress bar, print only the final summary. |

Feature and instrument names are case insensitive. An instrument set is written
as `IHID/IID/PT`, for example `MRO/CTX/EDR`.

### Worked example

Download CTX observations contained in every chasma:

```bash
uv run python scripts/download_metadata.py \
    --feature-class chasma \
    --instrument MRO/CTX/EDR
```

Re-running the same command downloads nothing new: any output file that already
exists is skipped, so runs are resumable. Use `--force` to overwrite.

### The crop rule (`--loc`)

ODE stores a lat/lon **bounding box** per feature, not a true outline, so
"cropped to the feature" means "inside the feature's bounding box". The `--loc`
mode chooses how a product footprint must relate to that box. The default `o`
keeps only products that fall **entirely inside** the feature. For Gale crater
with MRO CTX EDR:

| `--loc` | Meaning | Products |
|---|---|---|
| `b` | box intersects the product box | 423 |
| `f` | intersects the product footprint (ODE default) | 398 |
| `o` | **product is fully inside the feature** (our default) | 88 |
| `i` | product contains the whole feature | 0 |

### On-disk layout

```
data/
  _catalog/
    features.jsonl          cached feature catalog
    instrument_sets.jsonl   cached instrument catalog
  metadata/
    <feature_class>/
      <feature_name>/
        <IHID_IID_PT>.jsonl
```

For example `data/metadata/crater/gale/MRO_CTX_EDR.jsonl`. Each line is one
product: the ODE metadata fields plus provenance (feature name, class, the
feature bounding box, the `loc` mode, and a retrieval timestamp). An empty file
means the pair was checked and matched no products.

Coordinates are stored **exactly as ODE returns them, in degrees**, together
with the footprint in WKT. Converting latitude and longitude to meters (a degree
of longitude shrinks with `cos(latitude)`) is required for real area or coverage
computations, but that projection belongs to the analysis stage, not download,
so the raw values are preserved.

### Reading the output

The JSONL tree is queryable directly with [DuckDB](https://duckdb.org/), no
conversion step:

```bash
duckdb -c "SELECT feature_class, iid, count(*)
           FROM read_json_auto('data/metadata/**/*.jsonl')
           GROUP BY 1, 2 ORDER BY 3 DESC"
```

## Coverage analysis

Turns the downloaded metadata into how much of each feature every instrument
set reached, and when. It reads the whole metadata tree and needs no selection
arguments:

```bash
uv run python scripts/compute_coverage.py
```

Finished instrument sets are skipped, so an interrupted run resumes where it
stopped. Pass `--force` to recompute regardless, and `--workers N` to change the
process count.

Results land in `data/artifacts/coverage/<class>/<feature>/`, one
`<set>.events.parquet` with a row per observation and one `<set>.summary.parquet`
with the row for the set, plus a per-feature `summary.parquet`. Every feature's
summary rows are gathered into `data/artifacts/summary.parquet`.

## Notebook

`notebooks/coverage.ipynb` reads those artifacts one feature at a time: pick a
feature type and name, confirm, and it plots what each observation covered and
how much each instrument has reached in total. Features with nothing computed
locally are marked in the dropdown and show a grey panel instead of plots.

```bash
uv run --group notebook jupyter lab notebooks/coverage.ipynb
```

## Project layout

Dependencies point inward: models know nothing about services, services know
nothing about orchestration, and only the command layer knows about the
terminal.

```
scripts/download_metadata.py   command wiring and entry point

src/download/
  configs.py          every tunable constant, imports nothing from the package
  models/             shared vocabulary, one file per group
    feature.py        Feature
    instrument.py     InstrumentSet
    product.py        ProductRecord, InstrumentSetInfo
    job.py            Job, JobOutcome, DownloadPlan
    progress.py       ProgressEvent, RunSummary
  ode/                ODE REST access
    client.py         HTTP with retry and backoff
    catalog.py        feature and instrument catalogs, cached
    products.py       count and paged metadata fetch
  storage/
    layout.py         output paths, keyed by the shared slug rule
    cache.py          reads the cached catalogues back without a client
    writer.py         atomic JSONL write
  planner.py          selects features, builds the job plan
  runner.py           parallel execution, yields ProgressEvent
  cli/
    args.py           argument definitions
    progress.py       rich rendering of progress events
```

The runner never prints. It yields `ProgressEvent` objects carrying the
completed count, total, elapsed time, ETA, current job, and running totals, and
the caller decides how to render them. Anything else, a notebook or the coming
analysis stage, can drive the same runner and ignore the rendering entirely.

## Development

Linting and formatting use [ruff](https://docs.astral.sh/ruff/):

```bash
uv run ruff check .
uv run ruff format
```

A pre-push git hook blocks pushes when ruff reports problems. Enable it once per
clone:

```bash
git config core.hooksPath .githooks
```
