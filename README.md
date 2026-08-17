# Mars Geological Features Coverage Pipeline

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
uv run python scripts/features_coverage.py
```

One entry point runs both halves, and takes no arguments: every choice comes
from `config.yaml`, so the same file describes what was run and what to run
again. Every details about each option is in `config.yaml`'s comments.

## Exploratory Notebook

`notebooks/coverage.ipynb` reads the artifacts one feature at a time. Pick a
feature, confirm, and the cells below fill themselves in. An instrument that
reached none of the feature is still drawn, at zero, so a missing line always
means something. The notebook explains the rest.

```bash
uv run --group notebook jupyter lab notebooks/coverage.ipynb
```

## Structure

```
config.yaml           what to download, and how to measure it
scripts/              the entry point
notebooks/            interactive reads of the artifacts
src/
  configs.py          paths, and what the project's files are called
  settings.py         reads config.yaml and checks what it holds
  runner.py           the pooled runner and the two halves it drives
  console.py          the progress bar and everything printed
  utils.py            helpers shared across the pipeline
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
