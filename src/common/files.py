"""Where files live, what they are called, and how they are written.

Four rules that both stages depend on and that nothing else in the project is
allowed to restate: the repository root every data path hangs off, the slug the
two data trees are keyed by, the temp-file-and-rename that keeps an interrupted
run from leaving a half-written file behind, and the JSONL both stages store
their records in.

Both stages keep their data inside the repository, and a script run from the
root used to be the only thing that resolved a relative data path correctly. A
notebook opens with its own directory as the working directory, so the roots
hang off `REPO_ROOT` instead and mean the same place wherever they are resolved
from.
"""

from __future__ import annotations

import json
import os
import re
import tempfile
from collections.abc import Iterable, Iterator, Mapping
from contextlib import contextmanager
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parents[2]

_SLUG_RE = re.compile(r"[^a-z0-9]+")


def slugify(text: str) -> str:
    """Convert a name into a lowercase, underscore separated slug.

    The download stage names its directories with this and the coverage stage
    mirrors those names, so anything starting from a catalogue name rather than
    from a path on disk needs the same rule.

    Args:
        text: The raw name, for example "Rovers and Landers".

    Returns:
        A slug such as "rovers_and_landers", or "unnamed" if empty.
    """
    slug = _SLUG_RE.sub("_", text.strip().lower()).strip("_")
    return slug or "unnamed"


@contextmanager
def atomic_path(path: Path) -> Iterator[Path]:
    """Yield a temporary path that replaces the destination on success.

    Both stages decide what still needs doing by looking at which output files
    exist, so a file that appears complete but was truncated mid-write would
    make a resumed run skip work it never finished. The parent directory is
    created if needed. On any failure the temporary file is removed and the
    destination is left untouched.

    Args:
        path: The destination the temporary file is renamed to.

    Yields:
        The temporary path to write to.
    """
    path.parent.mkdir(parents=True, exist_ok=True)
    handle, raw = tempfile.mkstemp(dir=path.parent, suffix=".tmp")
    os.close(handle)
    tmp = Path(raw)
    try:
        yield tmp
    except BaseException:
        tmp.unlink(missing_ok=True)
        raise
    os.replace(tmp, path)


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
