"""Command line argument definitions for the coverage pipeline.

Anything the config file can also answer defaults to None here rather than to a
value, so that a flag left off is absent instead of quietly overriding the file
with a default. `cli.settings` is what turns those into settled choices.
"""

from __future__ import annotations

import argparse

from common.configs import CONFIG_PATH


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
            "over every downloaded geological feature. The cumulative union, "
            f"force and workers default to {CONFIG_PATH.name}; a flag passed "
            "here overrides it for one run."
        ),
    )
    parser.add_argument(
        "--cumulative-union",
        action=argparse.BooleanOptionalAction,
        default=None,
        help=(
            "Accumulate the running union of covered ground. Turning it off "
            "leaves every cumulative column empty and only measures what each "
            "observation covered on its own."
        ),
    )
    parser.add_argument(
        "--workers",
        type=int,
        help="Concurrent worker processes.",
    )
    parser.add_argument(
        "--force",
        action="store_true",
        default=None,
        help="Recompute instead of skipping features that are already done.",
    )
    return parser
