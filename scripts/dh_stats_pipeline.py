#!/usr/bin/env python
"""The stats on DigitalHub: what the platform calls, and what submits it."""

from __future__ import annotations

import os
import shutil
import tarfile
from pathlib import Path

import dh_pipeline
import digitalhub as dh
from digitalhub_runtime_python import handler

import analysis.utils.settings as settings
import utils.disk.paths as paths
from analysis import console
from analysis.coverage.artifacts import indexing
from analysis.selector import selecting
from analysis.stats.artifacts import storing
from analysis.stats.dataset import aggregating, reading

FUNCTION_NAME = "features-stats"
HANDLER = "scripts.dh_stats_pipeline:save_stats"

STATS_NAME = "coverage-stats"
SELECTION_NAME = "coverage-selection"


@handler(outputs=[SELECTION_NAME, STATS_NAME])
def save_stats(project):
    """Select the dataset under the filter, and publish it with the stats it leaves.

    Args:
        project: The DigitalHub project both archives are logged into.

    Returns:
        The uploaded archives of the selection and of the stats.

    Raises:
        RuntimeError: When the published measurements hold no feature to search.
    """
    os.environ[console.PLAIN_LOG_ENV] = "1"
    print("fetching the measurements", flush=True)
    _unpack(
        project.get_artifact(dh_pipeline.ARTIFACTS_NAME).download(overwrite=True),
        paths.ARTIFACTS_ROOT,
    )

    named = indexing.catalogued_features()
    if not named:
        raise RuntimeError("the published measurements hold no feature to search")

    workers = settings.load().workers
    print(f"selecting from {len(named):,} features on {workers} workers", flush=True)
    picked = selecting.select_dataset(workers, console.logged("selection"))
    kept = sum(1 for one in picked if one.feature.kept)
    print(f"{kept:,} of {len(picked):,} features earned a place", flush=True)
    print("uploading the selection", flush=True)
    selection = project.log_artifact(
        name=SELECTION_NAME,
        kind="artifact",
        source=str(dh_pipeline.archive(paths.SELECTION_ROOT, SELECTION_NAME)),
        description=(
            "The features and observations the filter keeps; "
            "unpack under data/analysis/."
        ),
    )
    # The stats are read off the selection just written, so they never stand
    # for a filter the selection no longer holds
    print(f"reading what the filter left of {len(picked):,} features", flush=True)
    storing.write_stats_file(
        aggregating.dataset_stats(
            reading.measure_every_feature(picked, workers, console.logged("stats")),
            len(picked),
        )
    )
    print("uploading the stats", flush=True)
    stats = project.log_artifact(
        name=STATS_NAME,
        kind="artifact",
        source=str(dh_pipeline.archive(paths.STATS_ROOT, STATS_NAME)),
        description=(
            "What the filter left of the dataset; unpack under data/analysis/."
        ),
    )
    print("done", flush=True)
    return selection, stats


def _unpack(downloaded: str, into: Path) -> None:
    """Put what was published back where the search reads it, and nothing else.

    Args:
        downloaded: The archive the platform left, or the directory holding it.
        into: The directory the archive fills, emptied first so that what it
            holds afterwards is what was published and only that.

    Returns:
        None.

    Raises:
        RuntimeError: When the download left no archive to unpack.
    """
    path = Path(downloaded)
    if path.is_dir():
        found = sorted(path.glob("*.tar.gz"))
        if not found:
            raise RuntimeError(f"no measurements were downloaded into {path}")
        path = found[0]
    shutil.rmtree(into, ignore_errors=True)
    into.parent.mkdir(parents=True, exist_ok=True)
    with tarfile.open(path) as packed:
        packed.extractall(into.parent, filter="data")


def main() -> int:
    """Register a version of the prediction from a pushed commit, and run it.

    Returns:
        A process exit code, non zero when the image did not build.
    """
    arguments = dh_pipeline.parser().parse_args()

    # Register a version of the function pointing at the pushed ref.
    project = dh.get_or_create_project(arguments.project)
    function = project.new_function(
        name=FUNCTION_NAME,
        kind="python",
        python_version=dh_pipeline.PYTHON_VERSION,
        code_src=f"git+{dh_pipeline.REPOSITORY}#{arguments.ref}",
        handler=HANDLER,
        requirements=dh_pipeline.requirements(),
    )

    # Build the image first, since the job cannot install anything itself.
    built = function.run(action="build", wait=True)
    if built.status.state != dh_pipeline.COMPLETED:
        print(f"the image did not build: {built.status.state}")
        return 1
    function.refresh()

    # Start the job on the built image, telling it where the clone lands.
    root = dh_pipeline.SOURCE_ROOT
    run = function.run(
        action="job",
        resources={
            "cpu": arguments.cpu or str(settings.load().workers),
            "mem": arguments.mem,
            "disk": arguments.disk,
        },
        envs=[{"name": "PYTHONPATH", "value": f"{root}:{root}/src:{root}/scripts"}],
        wait=False,
    )
    print(run.key)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
