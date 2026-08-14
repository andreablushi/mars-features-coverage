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

Start with one feature. It downloads every configured instrument set for that
feature and touches nothing else:

```bash
uv run python scripts/download_metadata.py --feature-name Jezero
```

Leaving `--feature-name` off downloads the whole catalog.

### Configuration

`config.yaml` at the repository root holds the standing choices:

```yaml
download:
  instruments:
    - MRO/CTX/EDR
    - MRO/HIRISE/RDRV11
    - MRO/CRISM/MTRDR
    - MRO/CRISM/TRDR
    - MRO/SHARAD/RDR
  loc: f          # f: any footprint overlapping the box, o: only those inside
  force: false
  workers: 4
```

Every key has a matching flag, and the flag wins for that one run:

```bash
uv run python scripts/download_metadata.py --instrument-set MRO/SHARAD/RDR --workers 2 --force
```

Drop a key to fall back to the default in `src/download/configs.py`, or delete
the file to run on defaults entirely. A file that is present but holds an
unusable value stops the run rather than falling back quietly.

A live progress bar shows how many jobs have finished, with failures printed
above it as they happen:

```
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━ 25/25
done in 15.5s: 25 jobs, 4,332 rows, 4 empty, 0 failed
```

### Options

| Flag | Meaning |
|---|---|
| `--feature-name NAME [NAME ...]` | Specific feature names (default: every feature in the catalog). |
| `--instrument-set IHID/IID/PT [...]` | Instrument set triples. |
| `--loc {b,f,o,i}` | ODE containment mode, see below. |
| `--workers N` | Concurrent downloads to run at once. |
| `--force` | Re-download instead of skipping existing files. |
| `--refresh-catalog` | Re-fetch the feature and instrument catalogs. |

`--instrument-set`, `--loc`, `--workers` and `--force` fall back to
`config.yaml` when they are not passed. An instrument set is written as
`IHID/IID/PT`, for example `MRO/CTX/EDR`.

### Worked example

Download CTX observations of one crater, four at a time:

```bash
uv run python scripts/download_metadata.py \
    --feature-name Jezero \
    --instrument-set MRO/CTX/EDR \
    --workers 4
```

Re-running the same command downloads nothing new: any output file that already
exists is skipped, so runs are resumable. Use `--force` to overwrite.

### The crop rule (`--loc`)

ODE stores a lat/lon **bounding box** per feature, not a true outline, so
"cropped to the feature" means "inside the feature's bounding box". The `--loc`
mode chooses how a product footprint must relate to that box. The default `f`
keeps every product whose footprint **overlaps** the feature at all, because an
observation that only partly reaches into a feature still covers the part it
reaches, and the coverage stage crops it to the box. For Gale crater with MRO
CTX EDR:

| `--loc` | Meaning | Products |
|---|---|---|
| `b` | box intersects the product box | 423 |
| `f` | **intersects the product footprint** (our default) | 398 |
| `o` | product is fully inside the feature | 88 |
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
stopped. Its own section of `config.yaml` holds the standing choices, and each
key has a matching flag that wins for one run:

```yaml
coverage:
  cumulative_union: true
  force: false
  workers: 8
```

The union of covered ground is the expensive half of the work, so it can be left
out with `--no-cumulative-union`. Each observation's own area is still measured
and one row per observation is still written, but every cumulative column is
left empty, which means no coverage fraction and no cumulative plot. Pass
`--force` to recompute finished sets and `--workers N` to change the process
count.

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
completed count and the unit that just finished, and the caller decides how to
render them. Anything else, a notebook or the analysis stage, can drive the same
runner and ignore the rendering entirely.

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
