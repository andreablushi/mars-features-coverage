#!/usr/bin/env python
"""Run the pipeline on DigitalHub: what the platform calls, and what submits it."""

from __future__ import annotations

import argparse
import os
import shutil
import tomllib
from pathlib import Path

import digitalhub as dh
import features_coverage
from digitalhub_runtime_python import handler

import utils.disk.paths as paths
import utils.disk.settings as settings
from analysis import console

PROJECT_NAME = "mars-features-coverage"
FUNCTION_NAME = "features-coverage"
REPOSITORY = "https://github.com/andreablushi/mars-features-coverage"
HANDLER = "scripts.dh_pipeline:save_artifacts"
PYTHON_VERSION = "PYTHON3_13"
SOURCE_ROOT = "/shared"
COMPLETED = "COMPLETED"
MEMORY = "16Gi"
DISK = "64Gi"

ARTIFACTS_NAME = "coverage-artifacts"
METADATA_NAME = "coverage-metadata"
SUMMARY_NAME = "coverage-summary"
CATALOG_NAME = "coverage-catalog"

# Registering a table samples it with pandas, which the pipeline never needs
IMAGE_EXTRAS = ["digitalhub>=0.15.6,<0.16", "pandas"]


def archive(source: Path, name: str) -> Path:
    """Pack a tree into one file, carrying the directory the pipeline reads it from.

    Args:
        source: The directory to pack, whose name the archive entries carry.
        name: The stem the written archive takes.

    Returns:
        The path of the archive, written beside the packed tree.
    """
    return Path(
        shutil.make_archive(
            str(paths.DATA_ROOT / name),
            "gztar",
            root_dir=paths.DATA_ROOT,
            base_dir=source.name,
        )
    )


@handler(outputs=[ARTIFACTS_NAME, SUMMARY_NAME])
def save_artifacts(project):
    """Run the pipeline on DigitalHub and publish everything it left on disk.

    Args:
        project: The DigitalHub project the artifacts are logged into.

    Returns:
        The uploaded archive of the measurements, then the catalogue index as a table.

    Raises:
        RuntimeError: When either half of the pipeline reported a failure.
    """
    os.environ[console.PLAIN_LOG_ENV] = "1"
    print("measuring coverage", flush=True)
    failed = features_coverage.main()

    # Publish the measurements themselves.
    print("packing the measurements", flush=True)
    packed = archive(paths.ARTIFACTS_ROOT, ARTIFACTS_NAME)
    print(
        f"uploading the measurements, {packed.stat().st_size / 1e6:.0f} MB", flush=True
    )
    artifacts = project.log_artifact(
        name=ARTIFACTS_NAME,
        kind="artifact",
        source=str(packed),
        description="Coverage events and summaries; unpack under data/.",
    )

    # Register the index on its own too, so the console can preview it.
    print("uploading the summary", flush=True)
    summary = project.log_table(
        name=SUMMARY_NAME,
        source=str(paths.ARTIFACTS_ROOT / paths.SUMMARY_NAME),
        description="One row per feature and instrument set.",
    )

    # Publish the ODE catalogues the run fetched, which the notebooks read.
    if paths.CATALOG_ROOT.exists() and any(paths.CATALOG_ROOT.glob("*.jsonl")):
        print("uploading the catalogues", flush=True)
        packed = archive(paths.CATALOG_ROOT, CATALOG_NAME)
        project.log_artifact(
            name=CATALOG_NAME,
            kind="artifact",
            source=str(packed),
            description="The ODE feature and instrument sets; unpack under data/.",
        )

    # Publish the records too, unless the run was told to discard them.
    if paths.METADATA_ROOT.exists() and any(paths.METADATA_ROOT.rglob("*.jsonl")):
        print("packing the records", flush=True)
        packed = archive(paths.METADATA_ROOT, METADATA_NAME)
        print(
            f"uploading the records, {packed.stat().st_size / 1e6:.0f} MB", flush=True
        )
        project.log_artifact(
            name=METADATA_NAME,
            kind="artifact",
            source=str(packed),
            description="The ODE records behind each measurement; unpack under data/.",
        )

    # Report a partly failed run only once everything is safely uploaded.
    if failed:
        raise RuntimeError("the run had failures; the artifacts hold what finished")
    print("done", flush=True)
    return artifacts, summary


def requirements() -> list[str]:
    """Read what the pipeline needs installed, so the image matches the repo.

    Returns:
        Every runtime dependency as a pip requirement, plus what the platform asks for.
    """
    manifest = (paths.REPO_ROOT / "pyproject.toml").read_text(encoding="utf-8")
    return tomllib.loads(manifest)["project"]["dependencies"] + IMAGE_EXTRAS


def parser() -> argparse.ArgumentParser:
    """Describe what a submission can be told to do.

    Returns:
        The argument parser for the submitting half.
    """
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--project", default=PROJECT_NAME, help="the DigitalHub project to run in"
    )
    parser.add_argument("--ref", default="main", help="branch, tag, or commit to run")
    parser.add_argument("--cpu", default=None, help="cores (default: config workers)")
    parser.add_argument("--mem", default=MEMORY, help=f"memory (default: {MEMORY})")
    parser.add_argument("--disk", default=DISK, help=f"disk (default: {DISK})")
    return parser


def main() -> int:
    """Register a version of the function from a pushed commit, and run it.

    Returns:
        A process exit code, non zero when the image did not build.
    """
    arguments = parser().parse_args()

    # Register a version of the function pointing at the pushed ref.
    project = dh.get_or_create_project(arguments.project)
    function = project.new_function(
        name=FUNCTION_NAME,
        kind="python",
        python_version=PYTHON_VERSION,
        code_src=f"git+{REPOSITORY}#{arguments.ref}",
        handler=HANDLER,
        requirements=requirements(),
    )

    # Build the image first, since the job cannot install anything itself.
    built = function.run(action="build", wait=True)
    if built.status.state != COMPLETED:
        print(f"the image did not build: {built.status.state}")
        return 1
    function.refresh()

    # Start the job on the built image, telling it where the clone lands.
    run = function.run(
        action="job",
        resources={
            "cpu": arguments.cpu or str(settings.load().workers),
            "mem": arguments.mem,
            "disk": arguments.disk,
        },
        envs=[
            {
                "name": "PYTHONPATH",
                "value": f"{SOURCE_ROOT}:{SOURCE_ROOT}/src:{SOURCE_ROOT}/scripts",
            }
        ],
        wait=False,
    )
    print(run.key)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
