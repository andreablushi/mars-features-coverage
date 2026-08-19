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

### What a finished run leaves behind

Three entities, each gaining a new version per run rather than replacing the
last:

```
coverage-artifacts   the measurements, as the data/artifacts tree
coverage-metadata    the ODE records they were computed from
coverage-summary     summary.parquet again, as a table dataitem
```

## Downloading the results

`dhcli` makes each of the three entities available on your local machine, so
you can run the analysis locally. Each downloads the latest version.

```bash
# the measurements, which is what the notebook reads
dhcli download -p mars-features-coverage artifact -n coverage-artifacts -d data/artifacts

# the ODE records they were computed from, gigabytes of them
dhcli download -p mars-features-coverage artifact -n coverage-metadata -d data/metadata

# the summary on its own, one row per feature and instrument set
dhcli download -p mars-features-coverage dataitem -n coverage-summary -d data/artifacts
```

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
scripts/              the local entry point, and the DigitalHub one
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
