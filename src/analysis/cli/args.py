"""Command line argument definitions for the coverage pipeline."""

from __future__ import annotations

import argparse

from analysis import configs


def build_parser() -> argparse.ArgumentParser:
    """Build the argument parser for the coverage computation.

    The stage always runs over every downloaded feature, so it takes no
    selection arguments.

    Returns:
        The configured argument parser.
    """
    parser = argparse.ArgumentParser(
        prog="compute-coverage",
        description=(
            "Compute the spatial and temporal coverage of every instrument set "
            "over every downloaded geological feature."
        ),
    )
    parser.add_argument(
        "--workers",
        type=int,
        default=configs.DEFAULT_WORKERS,
        help="Concurrent worker processes.",
    )
    parser.add_argument(
        "--force",
        action="store_true",
        help="Recompute instead of skipping features that are already done.",
    )
    return parser
