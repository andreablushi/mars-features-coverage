# Mars Geological Features Coverage Pipeline

Collects observation metadata from the PDS Orbital Data Explorer
([ODE](https://ode.rsl.wustl.edu/mars/index.aspx)) and measures how much of each
geological feature every instrument has covered, and when. Then reads those
measurements back to say what a training dataset would hold: the time window
each feature is best studied over, and the observations inside it worth
keeping.

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
from `configs/runner.yaml`, so the same file describes what was run and what to
run again. Every details about each option is in `configs/runner.yaml`'s comments.

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
| `--cpu` | `workers` from `configs/runner.yaml` | cores to request |
| `--mem` | `16Gi` | memory to request |
| `--disk` | `64Gi` | disk to request, sized for a whole catalogue |

### 3. Predict the dataset

```bash
uv run --group digitalhub python scripts/dh_prediction_pipeline.py
```

It measures nothing. It fetches what the run above published, sweeps the
filter in `configs/filter.yaml` over every measured feature, and publishes what
it would keep. It takes the same parameters.

A sweep published under the filter as it is still written is read back rather
than run again, so only an edited filter costs time.

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
./scripts/dh_download.sh predictions        # just what the filter predicted
./scripts/dh_download.sh artifacts summary  # just what the notebooks read
```

| Name | What it holds | Where it lands |
| --- | --- | --- |
| `artifacts` | the coverage measurements | `data/analysis/artifacts/` |
| `metadata` | the ODE records behind them | `data/analysis/metadata/` |
| `predictions` | what the filter would keep | `data/analysis/predictions/` |
| `summary` | one row per feature and instrument set | `data/analysis/artifacts/` |

## Notebooks

`notebooks/qualitative.ipynb` reads one feature at a time, whole. Pick a
feature, confirm, and the cells below fill themselves in. An instrument that
reached none of the feature is still drawn, at zero, so a missing line always
means something.

`notebooks/quantitative.ipynb` reads what the filter would make of every
measured feature rather than of a sample of them. The sweep costs minutes, so it
reads back what the prediction pipeline published, and sweeps on the spot only
when the filter has been edited since.

## Structure

```
configs/
  runner.yaml         # Configures the run, local and DigitalHub
  filter.yaml         # What a window has to hold for a feature to be kept
scripts/              # Entrypoints for the pipeline, local and DigitalHub
notebooks/            # The two notebooks that read the results
src/
  utils/              # What both halves use
    ode/              # The ODE client, its settings, its errors
    disk/             # Project paths, atomic writes, slugs
  analysis/           # What the coverage survey measures and the notebooks read
    console.py        # Progress bar for console prints
    planner.py        # What each half has left to do
    runner.py         # Orchestrates the stages, and downloads one set's metadata
    models/           # The data model: features, instruments, settings
    metadata/         # fetchers/, loaders/, and what is already downloaded
    coverage/         # Coverage measurement, geometry, and what it leaves on disk
    selector/         # The best time window search
    sampling/         # The sweep over every feature, and the aggregates over it
    visualization/    # What the notebooks draw
    utils/            # Reading the run config, parquet, record provenance
      maths/          # Scaling, formatting, and cell packing
  building/           # What a downloaded observation is turned into
    preprocessing/    # One package per instrument, and what they share
data/                 # Laid out as src is, each half owning what it writes
  _catalog/           # Cached ODE catalogs, read by both halves
  analysis/
    metadata/         # Raw ODE records
    artifacts/
      coverage/       # Coverage measurements
      summary.parquet # Every feature's summary rows together
    predictions/      # What the filter made of the dataset
  building/
    preprocessing/    # One directory per instrument, holding its products
```
