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
uv run python scripts/download_metadata.py   # 1. download the observation metadata
uv run python scripts/compute_coverage.py    # 2. measure coverage from it
```

Download writes one JSONL file per feature and instrument set, coverage turns
those into parquet: a row per observation saying what it covered and what it
newly added, and a row per set saying how much of the feature it reached and
over what span. Neither stage redoes finished work, so an interrupted run
resumes where it stopped and `--force` recomputes anyway.

Coverage is measured against the feature's bounding box, in an equal-area
projection centred on it, as an exact union rather than a sampled grid.

## Configuration

`config.yaml` holds the standing choices for both stages, one section each,
every parameter documented in place. A flag passed on the command line
overrides it for one run; delete a key for its built-in default, delete the
file for all of them. `--help` lists the flags.

## Exploratory Notebook

```bash
uv run --group notebook jupyter lab notebooks/coverage.ipynb
```

`notebooks/coverage.ipynb` reads the artifacts one feature at a time. Pick a
feature, confirm, and the cells below fill themselves in. The notebook explains
the rest.

## Structure

```
config.yaml           what to download, and how to compute it
scripts/              one entry point per stage
notebooks/            interactive reads of the artifacts
src/
  common/             what both stages share: paths, slugs, atomic writes, JSONL, config
  download/           ODE metadata download: api, selection, storage
  analysis/           the coverage computation: computation, loader, models
  visualization/      the feature picker and the plots the notebook draws
data/
  _catalog/           cached ODE catalogs
  metadata/           <class>/<feature>/<IHID_IID_PT>.jsonl
  artifacts/          <class>/<feature>/<set>.{events,summary}.parquet
```

Each stage is `configs.py` for constants, a planner that turns discovery into
jobs, a runner that executes them and only yields progress events, and a `cli/`
that renders. Runners never print.
