"""The command line the pipeline is driven by."""

from __future__ import annotations

import argparse

from configs import CONFIG_PATH
from download import configs as download_configs


def build_parser() -> argparse.ArgumentParser:
    """Build the argument parser for the pipeline.

    Returns:
        The configured argument parser.
    """
    parser = argparse.ArgumentParser(
        prog="survey-features",
        description=(
            "Download ODE observation metadata for geological features and "
            "measure how each instrument set covers them, computing a set's "
            "coverage as soon as its metadata lands. Every choice not passed "
            f"here defaults to {CONFIG_PATH.name}, in its own section."
        ),
    )
    parser.add_argument(
        "--feature-name",
        nargs="+",
        metavar="NAME",
        help="One or more feature names (default: every feature in the catalog).",
    )
    parser.add_argument(
        "--instrument-set",
        nargs="+",
        metavar="IHID/IID/PT",
        help="One or more instrument sets, such as MRO/CTX/EDR.",
    )
    parser.add_argument(
        "--loc",
        choices=download_configs.LOC_MODES,
        help=(
            "How a footprint must relate to the feature box: b box intersects "
            "box, f footprint intersects box, o footprint fully inside, "
            "i footprint contains the feature."
        ),
    )
    parser.add_argument(
        "--coverage-only",
        action="store_true",
        default=None,
        help="Measure what is already on disk without downloading anything.",
    )
    parser.add_argument(
        "--keep-metadata",
        action=argparse.BooleanOptionalAction,
        default=None,
        help=(
            "Keep a set's downloaded metadata once its coverage is computed. "
            "Discarding it makes the artifacts final, since nothing can be "
            "recomputed without downloading again."
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
        "--download-workers", type=int, help="Concurrent downloads to run at once."
    )
    parser.add_argument(
        "--coverage-workers", type=int, help="Concurrent coverage worker processes."
    )
    parser.add_argument(
        "--force",
        action="store_true",
        default=None,
        help="Redo work already on disk, in both stages.",
    )
    parser.add_argument(
        "--refresh-catalog",
        action="store_true",
        help="Re-fetch the feature and instrument catalogs.",
    )
    return parser
