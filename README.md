# Mars Remote Sensing Pipeline

Collects observation metadata from the PDS Orbital Data Explorer
([ODE](https://ode.rsl.wustl.edu/mars/index.aspx)) and measures how much of each
geological feature every instrument has covered, and when.

## Development Commands

```bash
uv sync                                    # environment
uv run ruff check . && uv run ruff format  # lint
git config core.hooksPath .githooks        # once per clone, blocks unlinted pushes
```

## Running the pipeline

```bash
uv run python scripts/survey_features.py                 # download, measuring as it lands
uv run python scripts/survey_features.py --coverage-only # measure what is already on disk
```

One entry point runs both halves: each instrument set's coverage is computed as
soon as its metadata arrives, so the download waits on the network while the
measurement uses the cores. Download writes one JSONL file per feature and
instrument set, coverage turns those into parquet: a row per observation saying
what it covered and what it newly added, and a row per set saying how much of
the feature it reached and over what span. Neither half redoes finished work, so
an interrupted run resumes where it stopped and `--force` recomputes anyway.

Coverage is measured against the feature's bounding box, in an equal-area
projection centred on it, as an exact union rather than a sampled grid.

Queries are built from that same box rather than from the feature's name, so the
ground asked for is the ground measured. A feature the catalogue writes with
equal west and east longitudes circles a pole and is asked for in two halves; one
it records by centre alone is given a box of `point_radius_deg`, unless it is a
classical albedo name, which has no edge any radius could stand in for and is
reported unqueried instead. ODE answers a query it cannot place with a count of
-1 rather than an error, and that is treated as the failure it is rather than as
an empty result.

## Configuration

`config.yaml` holds the standing choices for the run, one section each, every
parameter documented in place. A flag passed on the command line overrides it
for one run; delete a key for its built-in default, delete the file for all of
them. `--help` lists the flags.

Instrument sets are written `IHID/IID/PT`, optionally followed by a colon and an
ODE product id pattern to narrow one product type to a single observing mode, as
in `MRO/CRISM/TRDR:[mh]sp*`. Coverage needs both a footprint and an acquisition
time, and ODE states per product type whether it publishes either, so a set that
carries neither is refused before the run starts.

## Exploratory Notebook

```bash
uv run --group notebook jupyter lab notebooks/coverage.ipynb
```

`notebooks/coverage.ipynb` reads the artifacts one feature at a time. Pick a
feature, confirm, and the cells below fill themselves in. An instrument that
reached none of the feature is still drawn, at zero, so a missing line always
means something. The notebook explains the rest.

## Structure

```
config.yaml           what to download, and how to measure it
scripts/              the entry point
notebooks/            interactive reads of the artifacts
src/
  configs.py          paths, and what the run as a whole does
  settings.py         config.yaml ranked against the command line
  runner.py           the pooled runner and the two halves it drives
  cli/                the argument parser, the progress bar, and everything printed
  models/             what the stages pass around: features, jobs, results
  storage/            paths, slugs, atomic writes, JSONL, parquet, schemas
  download/           ODE metadata download: api, selection
  analysis/           the coverage computation: geometry, coverage, utils
  visualization/      the feature picker and the plots the notebook draws
data/
  _catalog/           cached ODE catalogs
  metadata/           <class>/<feature>/<IHID_IID_PT>.jsonl
  artifacts/
    coverage/         <class>/<feature>/<set>.{events,summary}.parquet
    geometry/         cached projected footprints, rebuilt when the rule changes
    summary.parquet   every feature's summary rows together
```

Each half is `configs.py` for constants, a planner that turns discovery into
jobs, a runner that executes them and only yields progress events, and a `cli/`
that renders. Runners never print.
