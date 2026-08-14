#!/usr/bin/env python
"""Command line entry point for the coverage computation stage."""

from __future__ import annotations

from collections.abc import Sequence
from contextlib import closing

from rich.console import Console

from analysis import configs, planner
from analysis.cli import console as view
from analysis.cli.args import build_parser
from analysis.cli.settings import resolve
from analysis.loader import catalog, discovery
from analysis.runner import CoverageRunner
from common.cli import progress


def main(argv: Sequence[str] | None = None) -> int:
    """Run the coverage computation command.

    Args:
        argv: Optional argument list, defaulting to sys.argv.

    Returns:
        A process exit code, non zero when any instrument set failed.
    """
    args = build_parser().parse_args(argv)
    settings = resolve(args)
    console = Console()

    sources = discovery.find_sets()
    plan = planner.build_plan(sources, force=settings.force)
    runner = CoverageRunner(
        workers=settings.workers, cumulative_union=settings.cumulative_union
    )
    view.describe_plan(plan, runner.workers, console)

    if plan.jobs:
        with closing(runner.run(plan.jobs)) as events:
            progress.render(events, len(plan.jobs), "coverage", console)

    for feature_dir in sorted({source.parent for source in sources}):
        catalog.finalise_feature(configs.COVERAGE_ROOT, feature_dir)
    indexed = catalog.rebuild(configs.ARTIFACTS_ROOT, configs.COVERAGE_ROOT)

    view.print_summary(runner.summary, indexed, console)
    return 1 if runner.summary.failed else 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except KeyboardInterrupt:
        progress.print_interrupted("instrument sets")
        raise SystemExit(130) from None
