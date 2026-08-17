#!/usr/bin/env python
"""What DigitalHub calls: the pipeline, then the upload of what it wrote."""

from __future__ import annotations

import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(REPO_ROOT / "src"), str(REPO_ROOT / "scripts")]

import features_coverage  # noqa: E402
from digitalhub_runtime_python import handler  # noqa: E402

import configs  # noqa: E402

ARTIFACTS_NAME = "coverage-artifacts"
SUMMARY_NAME = "coverage-summary"


@handler(outputs=[ARTIFACTS_NAME, SUMMARY_NAME])
def main(project):
    """Run the pipeline on DigitalHub and publish everything it left on disk.

    The runtime clones this repository and imports this file directly rather
    than installing it, so `src` and `scripts` are not importable until they
    are put on the path above. A run is configured by the `config.yaml` of the
    commit the function is pinned to, exactly as a local run is configured by
    the file in the working tree.

    Args:
        project: The DigitalHub project, injected by the runtime, which the
            artifacts are logged into.

    Returns:
        The uploaded artifacts directory, then the catalogue index as a table,
        in the order the decorator names them.

    Raises:
        RuntimeError: When either half of the pipeline reported a failure.
            Both entities are logged before this is raised, so what a partly
            failed run did finish is still downloadable.
    """
    failed = features_coverage.main()
    artifacts = project.log_artifact(
        name=ARTIFACTS_NAME,
        kind="artifact",
        source=str(configs.ARTIFACTS_ROOT),
        description="Coverage events and summaries for every measured feature.",
    )
    summary = project.log_table(
        name=SUMMARY_NAME,
        source=str(configs.ARTIFACTS_ROOT / configs.SUMMARY_NAME),
        description="One row per feature and instrument set.",
    )
    if failed:
        raise RuntimeError("the run had failures; the artifacts hold what finished")
    return artifacts, summary
