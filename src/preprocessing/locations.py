"""Where the files of one downloaded product are kept on disk."""

from __future__ import annotations

from collections.abc import Iterable
from pathlib import Path


def product_files(
    root: Path,
    directory: str,
    stem: str,
    suffixes: Iterable[str],
    subdirectory: str | None = None,
) -> dict[str, Path]:
    """Return where each half of one product belongs.

    Every instrument keeps a product in a directory of its own under its cache
    root, named after what it holds, with each half named for the product and
    suffixed for what that half is.

    Args:
        root: The cache root the instrument downloads under.
        directory: The directory under it, which is the observation for a
            product of one, and a name of its own for what every observation
            shares.
        stem: What each half of the product is called, without its suffix.
        suffixes: The suffixes the product is downloaded as.
        subdirectory: A directory under that one to keep the product in, or
            None to keep it beside the rest.

    Returns:
        The path for each suffix, keyed by suffix.
    """
    place = root / directory
    if subdirectory:
        place = place / subdirectory
    return {suffix: place / f"{stem}{suffix}" for suffix in suffixes}
