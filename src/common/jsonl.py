"""JSONL reading and writing shared by both pipelines."""

from __future__ import annotations

import json
from collections.abc import Iterable, Iterator, Mapping
from pathlib import Path
from typing import Any

from common.atomic import atomic_path


def write_jsonl(path: Path, rows: Iterable[Mapping[str, Any]]) -> int:
    """Write rows as JSONL, atomically via a temp file and rename.

    Args:
        path: Destination file path.
        rows: An iterable of JSON serialisable mappings.

    Returns:
        The number of rows written.
    """
    count = 0
    with atomic_path(path) as tmp, tmp.open("w", encoding="utf-8") as handle:
        for row in rows:
            handle.write(json.dumps(row, ensure_ascii=False))
            handle.write("\n")
            count += 1
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
