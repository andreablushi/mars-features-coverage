"""Streaming one file down to disk."""

from __future__ import annotations

from pathlib import Path

import httpx

from utils.disk.files import atomic_path

# How long to wait for the larger half of a product.
TIMEOUT = 300.0


def stream(url: str, path: Path, timeout: float = TIMEOUT) -> None:
    """Stream one file to disk, leaving nothing behind if it fails.

    Args:
        url: Where to read it from.
        path: Where it belongs once it is whole.
        timeout: How long to wait on the transfer.

    Returns:
        None.
    """
    path.parent.mkdir(parents=True, exist_ok=True)
    with atomic_path(path) as tmp, httpx.stream("GET", url, timeout=timeout) as reply:
        reply.raise_for_status()
        with tmp.open("wb") as handle:
            for chunk in reply.iter_bytes():
                handle.write(chunk)
