# MarsMultiSensorFeatures

A multi-sensor build dataset pipeline of Mars geological features. One sample is a single named
landform seen by three instruments inside one shared time window: CTX visible
imagery, CRISM multispectral cubes, and SHARAD radar sounding, each cropped to
that landform's extent.

## Development commands

```bash
uv sync                                     # environment
uv run ruff check . && uv run ruff format . # lint, over the whole repo
git config core.hooksPath .githooks         # once per clone, blocks unlinted pushes
```

## Running the analysis

One entry point runs every stage, here by default:

```bash
uv run python scripts/analysis_pipeline.py
```

It downloads the ODE metadata still missing, measures the coverage of every
feature, searches each for its best window, and writes what the filter keeps.
Every other choice comes from `configs/`, so the same files describe what was run
and what to run again.

| Flag | What it does |
| --- | --- |
| `--only-stats` | skip the download and the measurement, and select from what is already on disk |
| `--force` | redo finished work rather than skip it: download again and measure again |
| `--dh` | submit to DigitalHub instead of running here |
| `--ref` | with `--dh`, the branch, tag, or commit the platform clones |

## Running it on DigitalHub

[DigitalHub](https://scc-digitalhub.github.io/docs/0.15/) runs the same entry
point on a cluster and keeps what it produced as versioned entities. It clones a
pushed commit, so every change has to be on the branch you name with `--ref`
before it can run.

```bash
uv sync --group digitalhub
dhcli register <your-digitalhub-core-endpoint>
dhcli login                                    # opens a browser tab

uv run --group digitalhub python scripts/analysis_pipeline.py --dh
uv run --group digitalhub python scripts/analysis_pipeline.py --dh --only-stats
```

The first form runs every stage in one job and publishes all of it: the
measurements, the catalogue index, the records behind them, and the selection
and stats the filter left. The second reads a published measurement back and
publishes only the selection and the stats, so re-running an edited filter costs
nothing but the search.

Everything a submission needs, from the project name to the memory a job asks
for, is in `configs/digitalhub.yaml`. The pip requirements are taken straight
from `pyproject.toml`, so the image always matches this repository.

## Downloading what it published

```bash
chmod +x scripts/dh_download.sh   # once, to make it executable
./scripts/dh_download.sh          # everything
./scripts/dh_download.sh selection stats
```

The names, and the project they come from, are read out of
`configs/digitalhub.yaml`, so nothing here can drift from what the pipeline
publishes.

| Name | What it holds | Where it lands |
| --- | --- | --- |
| `coverage` | the coverage measurements | `data/analysis/coverage/` |
| `summary` | one row per feature and instrument set | `data/analysis/coverage/` |
| `catalog` | the ODE feature and instrument set lists | `data/_catalog/` |
| `metadata` | the ODE records behind the measurements | `data/analysis/metadata/` |
| `selection` | the features and observations the filter keeps | `data/analysis/selection/` |
| `stats` | what the filter left of the dataset | `data/analysis/stats/` |

## Notebooks

`notebooks/qualitative.ipynb` reads one feature at a time, whole. Pick a feature,
confirm, and the cells below fill themselves in. An instrument that reached none
of it is still drawn, at zero, so a missing line always means something.

`notebooks/quantitative.ipynb` reads what the filter made of every measured
feature rather than of a sample of them. It reads back what the pipeline
published and builds no artifact of its own.

## Configuration

```
configs/
  analysis_runner.yaml  # What a run downloads and measures, and on how many workers
  window_filter.yaml    # What a window has to hold for a feature to earn a place
  digitalhub.yaml       # What a submitted run is given, and what it publishes
```

Each file is read as written and no setting is checked: the run that reads it is
the check. What changes from one run to the next is a flag instead.

## Structure

```
scripts/
  analysis_pipeline.py  # The one entry point, and the two platform handlers
  dh_download.sh        # Brings published entities back down
  dhub/                 # Only what a submitted run needs
    configs.py          # Reads configs/digitalhub.yaml
    archives.py         # Packs what is published, unpacks what is read back
    submit.py           # Registers a version of a function, and starts the job
notebooks/              # The two notebooks that read the results
src/
  utils/                # What both halves use
    ode/                # The ODE client, its settings, its errors
    disk/               # Project paths, atomic writes, slugs
  analysis/             # What the archives cover, and what the notebooks read
    console.py          # Progress bars and totals
    planner.py          # What each half has left to do
    runner.py           # Holds the survey's plan and its pools
    models/             # Features, instruments, settings, jobs
    metadata/           # Asking ODE for records, and reading them back
    coverage/           # The coverage measurement, its geometry and its artifacts
    selector/           # The best time window search, under one filter
    stats/              # What the filter left, measured over one feature or all
    visualization/      # What the notebooks draw
  building/             # What a chosen observation is turned into
    preprocessing/      # One package per instrument, and what they share
data/                   # Laid out as src is, each half owning what it writes
  _catalog/             # Cached ODE catalogs, read by both halves
  analysis/
    metadata/           # Raw ODE records
    coverage/
      features/         # Per-feature coverage measurements
      summary.parquet   # Every feature's summary rows together
    selection/          # The features and observations the filter keeps
    stats/              # What the filter left of the dataset
  building/
    preprocessing/      # One directory per instrument, holding its products
```
