#!/usr/bin/env python
"""Register this repository as a DigitalHub function, and start a run of it."""

from __future__ import annotations

import argparse
import subprocess
import tomllib

import digitalhub as dh

import configs
import settings

PROJECT_NAME = "mars-features-coverage"
FUNCTION_NAME = "features-coverage"
HANDLER = "scripts.dh_pipeline:main"
PYTHON_VERSION = "PYTHON3_13"
COMPLETED = "COMPLETED"
MEMORY = "8Gi"
DISK = "16Gi"


def _git(*arguments: str) -> str:
    """Ask git something about this repository.

    Args:
        *arguments: The command to run, without the leading `git`.

    Returns:
        What the command printed, stripped.
    """
    finished = subprocess.run(
        ["git", *arguments],
        cwd=configs.REPO_ROOT,
        capture_output=True,
        text=True,
        check=True,
    )
    return finished.stdout.strip()


def _code_source(ref: str) -> str:
    """Spell where DigitalHub clones the pipeline from, and at which commit.

    Args:
        ref: The branch, tag, or commit the run is pinned to. It has to be
            pushed, since the platform clones from the remote and never sees
            the working tree.

    Returns:
        The origin remote's URL, prefixed and pinned the way the runtime reads.
    """
    return f"git+{_git('remote', 'get-url', 'origin')}#{ref}"


def _pushed(ref: str) -> bool:
    """Whether origin already carries the ref, so the platform can clone it.

    Checked before anything is registered, since the clone happens minutes
    later inside the build and fails there with far less to read.

    Args:
        ref: The branch, tag, or commit the run is pinned to.

    Returns:
        Whether the remote has it, by name first and then by whether a remote
        branch contains the commit.
    """
    try:
        if _git("ls-remote", "origin", ref):
            return True
        return bool(_git("branch", "--remotes", "--contains", ref))
    except subprocess.CalledProcessError:
        return False


def _built(project, requirements: list[str], source: str):
    """Find a version of the function whose image already fits this run.

    The job clones the repository itself when it starts, so an image only has
    to supply the interpreter and the installed packages. A version built for
    the same requirements, from the same source, can be run again rather than
    waited on through another build.

    Args:
        project: The DigitalHub project holding the function's versions.
        requirements: The pip requirements this run needs installed.
        source: The git source the run clones from.

    Returns:
        The first version carrying a matching image, or None when the function
        is new or nothing matches.
    """
    try:
        versions = project.get_function_versions(FUNCTION_NAME)
    except Exception:
        return None
    for function in versions:
        spec = function.to_dict().get("spec", {})
        if (
            spec.get("image")
            and spec.get("requirements") == requirements
            and spec.get("python_version") == PYTHON_VERSION
            and spec.get("source", {}).get("source") == source
        ):
            return function
    return None


def _resources(cpu: str | None, mem: str, disk: str) -> dict[str, str]:
    """Ask for enough of the cluster to hold a whole catalogue run.

    A run keeps every downloaded set and every projected footprint on the
    node's own disk until it ends, which a near complete local run measured at
    close to five gigabytes, so the default of a gigabyte cannot hold one. The
    processes are asked for one core each, since fewer cores than workers only
    makes them queue.

    Args:
        cpu: Cores to request, or None to follow `workers` in the config.
        mem: Memory to request.
        disk: Disk to request.

    Returns:
        The cpu, memory, and disk to request for the job.
    """
    return {"cpu": cpu or str(settings.load().workers), "mem": mem, "disk": disk}


def _requirements() -> list[str]:
    """Read what the pipeline needs installed, so the image matches the repo.

    Returns:
        Every runtime dependency, as pip requirement strings.
    """
    manifest = (configs.REPO_ROOT / "pyproject.toml").read_text(encoding="utf-8")
    return tomllib.loads(manifest)["project"]["dependencies"]


def main() -> int:
    """Create a version of the function from a pushed commit, and run it.

    The requirements are installed into an execution image rather than at
    startup, so an image has to exist before the job can import anything this
    repository depends on. A version already built for the same requirements
    is reused, since the job clones the code itself and the image only carries
    the environment; otherwise a version is registered and built here.

    The job is told to treat its output as a terminal, because otherwise rich
    draws nothing at all until the run ends and the log stays empty for hours.

    Returns:
        A process exit code, non zero when the ref is unpushed, the build
        failed, or a waited-for run did not succeed.
    """
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--project", default=PROJECT_NAME, help="the DigitalHub project to run in"
    )
    parser.add_argument(
        "--ref", default=None, help="branch, tag, or commit to run (default: current)"
    )
    parser.add_argument("--cpu", default=None, help="cores (default: config workers)")
    parser.add_argument("--mem", default=MEMORY, help=f"memory (default: {MEMORY})")
    parser.add_argument("--disk", default=DISK, help=f"disk (default: {DISK})")
    parser.add_argument(
        "--rebuild", action="store_true", help="build a new image even if one fits"
    )
    parser.add_argument(
        "--wait", action="store_true", help="block until the run finishes"
    )
    arguments = parser.parse_args()

    ref = arguments.ref or _git("branch", "--show-current")
    if not _pushed(ref):
        print(f"origin has no {ref}; push it before submitting")
        return 1
    source = _code_source(ref)
    requirements = _requirements()

    project = dh.get_or_create_project(arguments.project)
    function = None if arguments.rebuild else _built(project, requirements, source)
    if function is None:
        function = project.new_function(
            name=FUNCTION_NAME,
            kind="python",
            python_version=PYTHON_VERSION,
            code_src=source,
            handler=HANDLER,
            requirements=requirements,
        )
        built = function.run(action="build", wait=True)
        if built.status.state != COMPLETED:
            print(f"the image did not build: {built.status.state}")
            return 1
        function.refresh()

    run = function.run(
        action="job",
        resources=_resources(arguments.cpu, arguments.mem, arguments.disk),
        envs=[{"name": "FORCE_COLOR", "value": "1"}],
        wait=arguments.wait,
    )
    print(run.key)
    return 1 if arguments.wait and run.status.state != COMPLETED else 0


if __name__ == "__main__":
    raise SystemExit(main())
