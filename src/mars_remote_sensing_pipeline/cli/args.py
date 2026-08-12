"""Command line argument definitions for the download pipeline."""

from __future__ import annotations

import argparse
from pathlib import Path


def build_parser() -> argparse.ArgumentParser:
    """Build the argument parser for the metadata downloader.

    Returns:
        The configured argument parser.
    """
    parser = argparse.ArgumentParser(
        prog="download_metadata",
        description=(
            "Download ODE observation metadata grouped by geological feature "
            "class, feature name, and instrument set."
        ),
    )
    parser.add_argument(
        "--feature-class",
        nargs="+",
        metavar="CLASS",
        help="One or more feature classes (default: all classes).",
    )
    parser.add_argument(
        "--feature-name",
        nargs="+",
        metavar="NAME",
        help="One or more feature names (overrides --feature-class).",
    )
    parser.add_argument(
        "--instrument",
        nargs="+",
        metavar="IHID/IID/PT",
        help="One or more instrument set triples (default: the built-in set).",
    )
    parser.add_argument(
        "--loc",
        default="o",
        choices=["b", "f", "o", "i"],
        help="ODE containment mode; 'o' keeps products fully inside the feature.",
    )
    parser.add_argument(
        "--workers",
        type=int,
        default=4,
        help="Concurrent workers, clamped to 6 (default: 4).",
    )
    parser.add_argument(
        "--min-obs-time",
        metavar="UTC",
        help="Only products observed at or after this UTC time.",
    )
    parser.add_argument(
        "--max-obs-time",
        metavar="UTC",
        help="Only products observed at or before this UTC time.",
    )
    parser.add_argument(
        "--out",
        type=Path,
        default=Path("data/metadata"),
        help="Metadata output root (default: data/metadata).",
    )
    parser.add_argument(
        "--cache",
        type=Path,
        default=Path("data/_catalog"),
        help="Catalog cache directory (default: data/_catalog).",
    )
    parser.add_argument(
        "--test",
        action="store_true",
        help="Small sample: 3 features by 2 instrument sets.",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Print the plan and request estimate without querying.",
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
