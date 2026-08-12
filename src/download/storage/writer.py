"""Atomic JSONL writing and reading."""

from __future__ import annotations

import json
import os
import tempfile
from collections.abc import Iterable, Iterator, Mapping
from pathlib import Path
from typing import Any


def write_jsonl(path: Path, rows: Iterable[Mapping[str, Any]]) -> int:
    """Write rows as JSONL, atomically via a temp file and rename.

    The parent directory is created if needed. On any failure the temp file is
    removed and the destination is left untouched.

    Args:
        path: Destination file path.
        rows: An iterable of JSON serialisable mappings.

    Returns:
        The number of rows written.
    """
    path.parent.mkdir(parents=True, exist_ok=True)
    count = 0
    fd, tmp = tempfile.mkstemp(dir=path.parent, suffix=".tmp")
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as handle:
            for row in rows:
                handle.write(json.dumps(row, ensure_ascii=False))
                handle.write("\n")
                count += 1
    except BaseException:
        os.unlink(tmp)
        raise
    os.replace(tmp, path)
    return count


def read_jsonl(path: Path) -> Iterator[dict[str, Any]]:
    """Yield the JSON object on each non empty line of a JSONL file.

    Args:
        path: The JSONL file to read.

    Yields:
        One decoded object per line.
    """
    with path.open(encoding="utf-8") as handle:
        for line in handle:
            line = line.strip()
            if line:
                yield json.loads(line)
