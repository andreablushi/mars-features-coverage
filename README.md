# Mars Geological Features Coverage Pipeline

Collects observation metadata from the PDS Orbital Data Explorer
([ODE](https://ode.rsl.wustl.edu/mars/index.aspx)) and measures how much of each
geological feature every instrument has covered, and when. Then reads those
measurements back to say what a training dataset would hold: the time window
each tile of a feature is best studied over, and the observations inside it
worth keeping.

## Development Commands

```bash
uv sync                                    # environment
uv run ruff check . && uv run ruff format  # lint
git config core.hooksPath .githooks        # once per clone, blocks unlinted pushes
```

## Running the pipeline locally

```bash
uv run python scripts/features_coverage.py
```

One entry point runs both halves, and takes no arguments: every choice comes
from `config.yaml`, so the same file describes what was run and what to run
again. Every details about each option is in `config.yaml`'s comments.

## Running the pipeline on DigitalHub

[DigitalHub](https://scc-digitalhub.github.io/docs/0.15/) runs the pipeline on a
cluster instead of your laptop, and keeps what it produced as versioned
entities you can download later.
However, every change to the code or the config requires a push to the repository main branch, and a new run to be started from it.

### 1. Install the client

```bash
uv sync --group digitalhub
```

Then get the [CLI](https://scc-digitalhub.github.io/docs/0.15/cli/installation/)
(`dhcli`), point it at the instance, and log in.

```bash
dhcli register <your-digitalhub-core-endpoint>
dhcli login                                    # opens a browser tab
```

### 2. Measure the coverage

```bash
uv run --group digitalhub python scripts/dh_pipeline.py
```

It creates the project if the platform has none, takes the pip requirements
straight from `pyproject.toml` so the image matches this repository, builds
that image, and then starts the job. It prints the run key and returns.

| Parameter | Default | What it does |
| --- | --- | --- |
| `--project` | `mars-features-coverage` | which project to run in |
| `--ref` | `main` | branch, tag, or commit to run |
| `--cpu` | `workers` from `config.yaml` | cores to request |
| `--mem` | `16Gi` | memory to request |
| `--disk` | `64Gi` | disk to request, sized for a whole catalogue |

### 3. Predict the dataset

```bash
uv run --group digitalhub python scripts/dh_prediction_pipeline.py
```

It measures nothing. It fetches what the run above published, sweeps every
strategy in `src/analysis/selector/strategies/` over every tile of every measured
feature, and publishes what each of them would keep. It takes the same
parameters.

A strategy still written as it was when it was published is read back rather
than swept again, so only a new or edited one costs time.

## Downloading the results

`dhcli` brings each entity down to your machine, latest version, and the script
unpacks the archives into the directories the notebooks read.

```bash
chmod +x scripts/dh_download.sh # Only once, to make it executable
./scripts/dh_download.sh
```

With no argument everything comes down. Name one or more to bring down only
those.

```bash
./scripts/dh_download.sh predictions        # just what the strategies predicted
./scripts/dh_download.sh artifacts summary  # just what the notebooks read
```

| Name | What it holds | Where it lands |
| --- | --- | --- |
| `artifacts` | the coverage measurements | `data/artifacts/` |
| `metadata` | the ODE records behind them | `data/metadata/` |
| `predictions` | what each strategy would keep | `data/predictions/` |
| `summary` | one row per feature and instrument set | `data/artifacts/` |

## Notebooks

`notebooks/qualitative.ipynb` reads one feature at a
time, whole and then tile by tile. Pick a feature, confirm, and the cells below
fill themselves in. An instrument that reached none of the feature is still
drawn, at zero, so a missing line always means something.

`notebooks/quantitative.ipynb` puts every strategy
side by side, over every tile of every measured feature rather than a sample of
them. The sweep costs minutes, so it reads back what the prediction pipeline
published, and sweeps on the spot only a strategy nothing was published for.

## Structure

```
config.yaml           # Configures the run, local and DigitalHub
scripts/              # Entrypoints for the pipeline, local and DigitalHub
notebooks/            # The two notebooks that read the results
src/
  ode/                # The ODE client, its settings, its errors
  utils/disk/         # Project paths, atomic writes, slugs
  analysis/           # What the coverage survey measures and the notebooks read
    console.py        # Progress bar for console prints
    planner.py        # What each half has left to do
    runner.py         # Orchestrates the pipeline stages
    models/           # The data model: features, instruments, settings
    metadata/         # ODE catalogue and record fetching
    coverage/         # Coverage measurement, geometry, and what it leaves on disk
    selector/         # The best time window search
      strategies/     # One YAML per strategy the search can run under
    sampling/         # The sweep over every tile, and the aggregates over it
    visualization/    # What the notebooks draw
    utils/            # config.yaml, parquet, record provenance
      maths/          # Scaling, formatting, and cell packing
  building/           # What a downloaded observation is turned into
    preprocessing/    # One package per instrument, and what they share
data/
  _catalog/           # Cached ODE catalogs
  metadata/           # Raw ODE records
  predictions/        # What each strategy made of the dataset, one file each
  artifacts/
    coverage/         # Coverage measurements
    summary.parquet   # Every feature's summary rows together
```
