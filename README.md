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

## Running the pipeline on DigitalHub

[DigitalHub](https://scc-digitalhub.github.io/docs/0.15/) runs the pipeline on a
cluster instead of your laptop, and keeps what it produced as versioned
entities you can download later. It never sees your working tree: it clones
this repository from its remote, so **only pushed commits can run**, and the
`config.yaml` of the commit you pin is the whole configuration of the run.

Three pieces do the work:

```
scripts/dh_pipeline.py   what DigitalHub calls, and what it uploads afterwards
scripts/dh_submit.py     run here, to register the function and start a run
scripts/dh_fetch.py      run here, to pull the results back down
```

### 1. Install the client

```bash
uv sync --group digitalhub
```

Then get the [CLI](https://scc-digitalhub.github.io/docs/0.15/cli/installation/)
(`dhcli`), point it at the instance, and log in. This writes `~/.dhcore.ini`,
which the SDK reads too, so nothing else needs configuring.

```bash
dhcli register <your-digitalhub-core-endpoint>
dhcli login                                    # opens a browser tab
```

### 2. Push what you want to run

```bash
git push origin HEAD                           # the commit is what gets cloned
```

Edit `config.yaml` first if the run should differ from the last one. A run is
reproducible because the commit carries both the code and the choices.

### 3. Start the run

```bash
uv run --group digitalhub python scripts/dh_submit.py
```

It reads the origin remote and the current branch, so the function points at
what you just pushed, and it takes the pip requirements straight from
`pyproject.toml` so the image matches the local environment.

It refuses to submit a ref that origin does not carry, since the clone happens
minutes later inside the build and fails there with far less to read.

It then needs an execution image, which is where the requirements are
installed and which takes a few minutes to build. The job clones the code
itself when it starts, so the image only carries the environment, and a
version already built for the same requirements and the same source is reused
rather than built again. Without an image the job runs on a base image holding
none of the pipeline's dependencies, which is what a `ModuleNotFoundError` in
the logs means.

It prints the run key and returns. `--wait` blocks on the job as well, `--ref`
pins a tag or an older commit, `--project` picks another project, `--cpu`,
`--mem` and `--disk` override the request, and `--rebuild` forces a fresh image
when you would rather not trust the reuse.

### 4. Watch it

The download half is slow, and a full catalogue run takes hours.

```bash
dhcli -p mars-features-coverage list runs -s RUNNING
dhcli -p mars-features-coverage log <run-id> -f
```

The console of your instance shows the same thing, plus the entities the run
produced, under `/console`.

The job is told to treat its output as a terminal, because rich draws nothing
at all when it thinks it is writing to a file and the log would stay empty for
the whole run. The cost is that the progress bar reaches the log as redraw
frames, so it reads as one long line of escape codes and the log grows for as
long as the run does.

### What a finished run leaves behind

Three entities, each gaining a new version per run rather than replacing the
last:

```
coverage-artifacts   the measurements, as the data/artifacts tree
coverage-metadata    the ODE records they were computed from
coverage-summary     summary.parquet again, as a table dataitem
```

`coverage-summary` is what shows up under **Datasets** in the console, with a
preview of its rows.

The projected footprints under `data/artifacts/geometry` are dropped before any
of this is uploaded. They are a cache the run rebuilds from the records
whenever the projection rule changes, and they outweigh the measurements they
produced by more than ten to one, so publishing them would cost far more than
keeping them saves.

Nothing survives between runs: the platform clones a fresh tree every time, so
each run downloads the whole catalogue from ODE again and a restarted pod
begins at zero. A run whose sets did not all succeed still uploads everything
before it reports the failure, so a partly finished run is never lost.

## Downloading the results

```bash
uv run --group digitalhub python scripts/dh_fetch.py
```

This writes the artifact into `data/artifacts`, in the layout it had on the
platform, which is the same layout a local run produces. The notebook below
then reads it with nothing else to set up. `--version` takes an artifact id if
you want an older run rather than the latest, `--metadata` also pulls the ODE
records down into `data/metadata`, which run to gigabytes and which nothing
local reads, and `--artifact` and `--project` match the flags on the submit
script.

`dhcli` can do it too, without Python:

```bash
dhcli download -p mars-features-coverage artifact -n coverage-artifacts -d data/artifacts
```

### If a run fails

- **`Job has reached the specified backoff limit`.** Kubernetes saying the pod
  kept exiting, never why. Read the job container rather than the init one,
  which is the half that clones and almost always succeeds:
  `dhcli -p <project> log <run-id> -c <container-id>`. A `ModuleNotFoundError`
  there means the job ran on an image that was never built with the
  requirements.
- **Clone fails.** The commit is not pushed, or the repository is private, in
  which case the platform needs a `GIT_TOKEN`
  [secret](https://scc-digitalhub.github.io/docs/0.15/tasks/secrets/).
- **Out of disk.** A whole catalogue run holds every downloaded set and every
  projected footprint on the node's disk at once, close to five gigabytes, so
  the submit script asks for sixteen. `MEMORY` and `DISK` in
  `scripts/dh_submit.py` set the request; the cpu follows `workers` in
  `config.yaml`, since fewer cores than workers only makes them queue.
- **Killed, or slow.** The request above may exceed what the cluster allows a
  single job. Lower it, or lower `workers`, rather than letting the pod sit
  unschedulable. Nothing in the pipeline uses a GPU, so asking for one buys
  nothing: the download waits on the network and the coverage work is shapely
  on the CPU.
- **Unknown kind `python`.** `digitalhub-runtime-python` is missing locally;
  `uv sync --group digitalhub` installs it. If the instance is not on 0.15,
  match its version in `pyproject.toml`.

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
scripts/              the entry point, and the DigitalHub adapters
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
