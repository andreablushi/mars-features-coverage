#!/usr/bin/env python
"""Run the pipeline on DigitalHub: what the platform calls, and what submits it."""

from __future__ import annotations

import argparse
import shutil
import tomllib

import digitalhub as dh
import features_coverage
from digitalhub_runtime_python import handler

import configs
import settings

PROJECT_NAME = "mars-features-coverage"
FUNCTION_NAME = "features-coverage"
REPOSITORY = "https://github.com/andreablushi/mars-features-coverage"
HANDLER = "scripts.dh_pipeline:measure"
PYTHON_VERSION = "PYTHON3_13"
SOURCE_ROOT = "/shared"
COMPLETED = "COMPLETED"
MEMORY = "8Gi"
DISK = "16Gi"

ARTIFACTS_NAME = "coverage-artifacts"
METADATA_NAME = "coverage-metadata"
SUMMARY_NAME = "coverage-summary"


@handler(outputs=[ARTIFACTS_NAME, SUMMARY_NAME])
def measure(project):
    """Run the pipeline on DigitalHub and publish everything it left on disk.

    The projected footprints are dropped before anything is uploaded. They are
    a cache the run rebuilds from the records whenever the projection rule
    changes, and they outweigh the measurements they produced by more than ten
    to one. The records themselves are published beside the measurements, as a
    separate artifact rather than a named output, so that a run configured to
    drop them still returns everything the decorator names.

    Args:
        project: The DigitalHub project, injected by the runtime, which the
            artifacts are logged into.

    Returns:
        The uploaded artifacts directory, then the catalogue index as a table,
        in the order the decorator names them.

    Raises:
        RuntimeError: When either half of the pipeline reported a failure.
            Every entity is logged before this is raised, so what a partly
            failed run did finish is still downloadable.
    """
    print("measuring coverage", flush=True)
    failed = features_coverage.main()

    # Drop the projection cache, which dwarfs the results it produced.
    shutil.rmtree(configs.GEOMETRY_ROOT, ignore_errors=True)

    # Publish the measurements themselves.
    print("uploading the measurements", flush=True)
    artifacts = project.log_artifact(
        name=ARTIFACTS_NAME,
        kind="artifact",
        source=str(configs.ARTIFACTS_ROOT),
        description="Coverage events and summaries for every measured feature.",
    )

    # Publish the records too, unless the run was told to discard them.
    if configs.METADATA_ROOT.exists() and any(configs.METADATA_ROOT.rglob("*.jsonl")):
        print("uploading the records", flush=True)
        project.log_artifact(
            name=METADATA_NAME,
            kind="artifact",
            source=str(configs.METADATA_ROOT),
            description="The ODE records each measurement was computed from.",
        )

    # Register the index again on its own, so the console can preview it.
    print("uploading the summary", flush=True)
    summary = project.log_table(
        name=SUMMARY_NAME,
        source=str(configs.ARTIFACTS_ROOT / configs.SUMMARY_NAME),
        description="One row per feature and instrument set.",
    )

    # Report a partly failed run only once everything is safely uploaded.
    if failed:
        raise RuntimeError("the run had failures; the artifacts hold what finished")
    print("done", flush=True)
    return artifacts, summary


def _requirements() -> list[str]:
    """Read what the pipeline needs installed, so the image matches the repo.

    Returns:
        Every runtime dependency, as pip requirement strings.
    """
    manifest = (configs.REPO_ROOT / "pyproject.toml").read_text(encoding="utf-8")
    return tomllib.loads(manifest)["project"]["dependencies"]


def _parser() -> argparse.ArgumentParser:
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
    parser.add_argument(
        "--wait", action="store_true", help="block until the run finishes"
    )
    return parser


def main() -> int:
    """Register a version of the function from a pushed commit, and run it.

    The requirements are installed into an execution image rather than at
    startup, so the image is built before the job can import anything this
    repository depends on. The job is told where the clone puts the code, so
    that the handler imports the pipeline the same way any other module does.

    Returns:
        A process exit code, non zero when the build, or a waited-for run, did
        not succeed.
    """
    arguments = _parser().parse_args()

    # Register a version of the function pointing at the pushed ref.
    project = dh.get_or_create_project(arguments.project)
    function = project.new_function(
        name=FUNCTION_NAME,
        kind="python",
        python_version=PYTHON_VERSION,
        code_src=f"git+{REPOSITORY}#{arguments.ref}",
        handler=HANDLER,
        requirements=_requirements(),
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
                "value": f"{SOURCE_ROOT}/src:{SOURCE_ROOT}/scripts",
            }
        ],
        wait=arguments.wait,
    )
    print(run.key)
    return 1 if arguments.wait and run.status.state != COMPLETED else 0


if __name__ == "__main__":
    raise SystemExit(main())
