"""Orchestration for the metadata download command."""

from __future__ import annotations

import argparse
from collections.abc import Sequence

from mars_remote_sensing_pipeline.cli.args import build_parser
from mars_remote_sensing_pipeline.defaults import (
    DEFAULT_INSTRUMENT_SETS,
    TEST_FEATURE_NAMES,
    TEST_INSTRUMENT_SETS,
)
from mars_remote_sensing_pipeline.download import planner, runner
from mars_remote_sensing_pipeline.ode import catalog
from mars_remote_sensing_pipeline.ode.client import ODEClient
from mars_remote_sensing_pipeline.ode.models import InstrumentSet


def _resolve_instrument_sets(args: argparse.Namespace) -> list[InstrumentSet]:
    """Choose the instrument sets to download from the parsed arguments.

    Args:
        args: The parsed command line arguments.

    Returns:
        The instrument sets to use.

    Raises:
        SystemExit: If an --instrument value is not a valid triple.
    """
    if args.instrument:
        try:
            return [InstrumentSet.parse(text) for text in args.instrument]
        except ValueError as exc:
            raise SystemExit(f"error: {exc}") from exc
    if args.test:
        return list(TEST_INSTRUMENT_SETS)
    return list(DEFAULT_INSTRUMENT_SETS)


def _resolve_feature_selection(
    args: argparse.Namespace,
) -> tuple[list[str] | None, list[str] | None]:
    """Choose the feature names or classes to download.

    Args:
        args: The parsed command line arguments.

    Returns:
        A pair (names, classes) where at most one is set; both None means all
        features.
    """
    if args.feature_name:
        return list(args.feature_name), None
    if args.feature_class:
        return None, list(args.feature_class)
    if args.test:
        return list(TEST_FEATURE_NAMES), None
    return None, None


def main(argv: Sequence[str] | None = None) -> int:
    """Run the metadata download command.

    Args:
        argv: Optional argument list, defaulting to sys.argv.

    Returns:
        A process exit code.
    """
    args = build_parser().parse_args(argv)
    instrument_sets = _resolve_instrument_sets(args)
    names, classes = _resolve_feature_selection(args)

    with ODEClient() as client:
        features = catalog.load_features(
            client, args.cache, refresh=args.refresh_catalog
        )
        usable, degenerate = planner.select_features(
            features, names=names, classes=classes
        )
        jobs, skipped = planner.build_jobs(
            usable, instrument_sets, args.out, force=args.force
        )

        if degenerate:
            print(f"skipping {len(degenerate)} degenerate features (zero-area bbox)")
        print(
            f"plan: {len(usable)} features x {len(instrument_sets)} sets, "
            f"{len(jobs)} jobs to run, {skipped} already downloaded"
        )
        if args.dry_run:
            print("dry run: no queries issued")
            return 0

        runner.run_jobs(
            client,
            jobs,
            loc=args.loc,
            workers=args.workers,
            min_obs_time=args.min_obs_time,
            max_obs_time=args.max_obs_time,
        )
    return 0
