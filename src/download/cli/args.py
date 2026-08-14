"""Command line argument definitions for the download pipeline.

Anything the config file can also answer defaults to None here rather than to a
value, so that a flag left off is absent instead of quietly overriding the file
with a default. `cli.settings` is what turns those into settled choices.
"""

from __future__ import annotations

import argparse

from common.configs import CONFIG_PATH
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
            "class, feature name, and instrument set. Instruments, loc, force "
            f"and workers default to {CONFIG_PATH.name}; a flag passed here "
            "overrides it for one run."
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
        choices=configs.LOC_MODES,
        help=(
            "How a footprint must relate to the feature box: b box "
            "intersects box, f footprint intersects box, o footprint "
            "fully inside, i footprint contains the feature."
        ),
    )
    parser.add_argument(
        "--workers",
        type=int,
        help="Concurrent downloads to run at once.",
    )
    parser.add_argument(
        "--force",
        action="store_true",
        default=None,
        help="Re-download instead of skipping existing output files.",
    )
    parser.add_argument(
        "--refresh-catalog",
        action="store_true",
        help="Re-fetch the feature and instrument catalogs.",
    )
    return parser
