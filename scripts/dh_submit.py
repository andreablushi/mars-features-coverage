#!/usr/bin/env python
"""Register this repository as a DigitalHub function, and start a run of it."""

from __future__ import annotations

import argparse
import subprocess
import tomllib

import digitalhub as dh

import configs

PROJECT_NAME = "mars-rs-pipeline"
FUNCTION_NAME = "features-coverage"
HANDLER = "scripts.dh_pipeline:main"
PYTHON_VERSION = "PYTHON3_13"


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


def _requirements() -> list[str]:
    """Read what the pipeline needs installed, so the image matches the repo.

    Returns:
        Every runtime dependency, as pip requirement strings.
    """
    manifest = (configs.REPO_ROOT / "pyproject.toml").read_text(encoding="utf-8")
    return tomllib.loads(manifest)["project"]["dependencies"]


def main() -> int:
    """Create a version of the function from a pushed commit, and run it.

    Returns:
        A process exit code, non zero when a waited-for run did not succeed.
    """
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--project", default=PROJECT_NAME, help="the DigitalHub project to run in"
    )
    parser.add_argument(
        "--ref", default=None, help="branch, tag, or commit to run (default: current)"
    )
    parser.add_argument(
        "--wait", action="store_true", help="block until the run finishes"
    )
    arguments = parser.parse_args()

    project = dh.get_or_create_project(arguments.project)
    function = project.new_function(
        name=FUNCTION_NAME,
        kind="python",
        python_version=PYTHON_VERSION,
        code_src=_code_source(arguments.ref or _git("branch", "--show-current")),
        handler=HANDLER,
        requirements=_requirements(),
    )
    run = function.run(action="job", wait=arguments.wait)
    print(run.key)
    return 1 if arguments.wait and run.status.state != "COMPLETED" else 0


if __name__ == "__main__":
    raise SystemExit(main())
