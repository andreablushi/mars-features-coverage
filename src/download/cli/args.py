"""Command line argument definitions for the download pipeline."""

from __future__ import annotations

import argparse

from download import configs


def build_parser() -> argparse.ArgumentParser:
    """Build the argument parser for the metadata downloader.

    Returns:
        The configured argument parser.
    """
    parser = argparse.ArgumentParser(
        prog="download-metadata",
        description=(
            "Download ODE observation metadata grouped by geological feature "
            "class, feature name, and instrument set."
        ),
    )
    parser.add_argument(
        "--feature-name",
        nargs="+",
        metavar="NAME",
        help="One or more feature names (default: every feature in the catalog).",
    )
    parser.add_argument(
        "--workers",
        type=int,
        default=configs.DEFAULT_WORKERS,
        help=f"Concurrent workers, clamped to {configs.MAX_WORKERS}.",
    )
    parser.add_argument(
        "--force",
        action="store_true",
        help="Re-download instead of skipping existing output files.",
    )
    parser.add_argument(
        "--refresh-catalog",
        action="store_true",
        help="Re-fetch the feature and instrument catalogs.",
    )
    return parser
