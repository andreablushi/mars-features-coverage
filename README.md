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
dhcli register https://core.rsde.atlas.fbk.eu
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
`pyproject.toml` so the image matches the local environment. It prints the run
key and returns; pass `--wait` to block instead, `--ref` to pin a tag or an
older commit, and `--project` to use a project other than `mars-rs-pipeline`.

### 4. Watch it

The download half is slow, and a full catalogue run takes hours.

```bash
dhcli -p mars-rs-pipeline list runs -s RUNNING
dhcli -p mars-rs-pipeline log <run-id> -f
```

The console shows the same thing, plus the entities the run produced, at
[core.rsde.atlas.fbk.eu/console](https://core.rsde.atlas.fbk.eu/console).

### What a finished run leaves behind

The whole `data/artifacts` tree is uploaded as one artifact, `coverage-artifacts`,
and `summary.parquet` is registered again on its own as a table dataitem,
`coverage-summary`, which is what shows up under **Datasets** in the console with
a preview of its rows. Each run adds a new version of both rather than replacing
the last. The downloaded ODE metadata under `data/metadata` is not uploaded: it
is the intermediate the artifacts were computed from, and it is large.

A run whose sets did not all succeed still uploads both entities before it
reports the failure, so a partly finished run is never lost.

## Downloading the results

```bash
uv run --group digitalhub python scripts/dh_fetch.py
```

This writes the artifact into `data/artifacts`, in the layout it had on the
platform, which is the same layout a local run produces. The notebook below
then reads it with nothing else to set up. `--version` takes an artifact id if
you want an older run rather than the latest, and `--artifact` and `--project`
match the flags on the submit script.

`dhcli` can do it too, without Python:

```bash
dhcli download -p mars-rs-pipeline artifact -n coverage-artifacts -d data/artifacts
```

### If a run fails

- **Clone fails.** The commit is not pushed, or the repository is private, in
  which case the platform needs a `GIT_TOKEN`
  [secret](https://scc-digitalhub.github.io/docs/0.15/tasks/secrets/).
- **Killed, or slow.** The job takes the cluster's default CPU and memory, and
  `workers` in `config.yaml` asks for that many processes. Pass `resources` to
  `function.run()` in `scripts/dh_submit.py` to ask for more.
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
