"""Writing a file so an interrupted run never leaves a half-written one.

Both stages are long enough to be stopped part way through, and both decide
what still needs doing by looking at which output files exist. A file that
appears complete but was truncated mid-write would make a resumed run skip work
it never finished, so every output is built beside its destination and moved
into place only once it is whole.
"""

from __future__ import annotations

import os
import tempfile
from collections.abc import Iterator
from contextlib import contextmanager
from pathlib import Path


@contextmanager
def atomic_path(path: Path) -> Iterator[Path]:
    """Yield a temporary path that replaces the destination on success.

    The parent directory is created if needed. On any failure the temporary
    file is removed and the destination is left untouched.

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
