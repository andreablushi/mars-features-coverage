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

### 2. Start the run

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
| `--mem` | `8Gi` | memory to request |
| `--disk` | `16Gi` | disk to request, sized for a whole catalogue |

## Downloading the results

`dhcli` makes each of the three entities available on your local machine, so you can run the analysis locally.
Each download retrieves the latest version.

The downloads are packaged as `.tar.gz` archives and are automatically extracted into the expected directories by the download script.

```bash
chmod +x scripts/dh_download.sh # Only once, to make it executable
./scripts/dh_download.sh
```

This downloads:

* **Measurements**: the coverage artifacts read by the notebook, extracted to `data/artifacts/`.
* **ODE records**: the metadata used to compute the measurements, extracted to `data/metadata/`.
* **Coverage summary**: one row per feature and instrument set, extracted to `data/artifacts/`.


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
config.yaml           # Configures the run, local and DigitalHub
scripts/              # Entrypoints for the pipeline, local and DigitalHub
notebooks/            # Interactive notebook for exploring the results
src/
  configs.py          # Global constants and paths
  settings.py         # The config.yaml parser and validator
  runner.py           # Orchestrates the pipeline stages
  console.py          # Progress bar for console prints
  utils/
    maths/            # Scaling, formatting, and cell packing
    disk/             # Project paths, config.yaml, slugs, record provenance
  models/             # The data model: features, instruments, coverage, geometry
  storage/            # Caches and the parquet read/write helpers
  download/           # ODE metadata fetching
  analysis/           # Coverage measurement and summary generation
  survey/             # The best time window search, and whether a feature is kept
  visualization/      # Notebook and figure generation
data/
  _catalog/           # Cached ODE catalogs
  metadata/           # Raw ODE records
  artifacts/
    coverage/         # Coverage measurements
    geometry/         # Projection cache, dropped when a run ends
    summary.parquet   # Every feature's summary rows together
```
