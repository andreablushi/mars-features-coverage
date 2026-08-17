#!/usr/bin/env python
"""Download the artifacts a DigitalHub run produced into the local data tree."""

from __future__ import annotations

import argparse

import digitalhub as dh

import configs

PROJECT_NAME = "mars-rs-pipeline"
ARTIFACTS_NAME = "coverage-artifacts"


def main() -> int:
    """Fetch one version of the artifacts, so the notebook can read them here.

    The uploaded directory keeps the layout it had on the platform, so it
    lands as the `data/artifacts` tree a local run would have written.

    Returns:
        A process exit code, always zero, since a missing artifact raises.
    """
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--project", default=PROJECT_NAME, help="the DigitalHub project to read from"
    )
    parser.add_argument(
        "--artifact", default=ARTIFACTS_NAME, help="the name the run logged them under"
    )
    parser.add_argument(
        "--version", default=None, help="artifact id to fetch (default: the latest)"
    )
    arguments = parser.parse_args()

    project = dh.get_or_create_project(arguments.project)
    artifact = project.get_artifact(arguments.artifact, entity_id=arguments.version)
    print(artifact.download(str(configs.ARTIFACTS_ROOT), overwrite=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
