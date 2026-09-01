"""Reading a PDS or ISIS label into the keys it names."""

from __future__ import annotations

from pathlib import Path


def load(path: Path) -> dict[str, str]:
    """Read a label into its keys and values.

    Args:
        path: The `.lbl` or `.hdr` file to read.

    Returns:
        The label, keyed as written, with quotes and unit suffixes stripped.
        Where a key is written more than once the first wins.
    """
    label: dict[str, str] = {}
    skipping = False
    for line in path.read_text(errors="replace").splitlines():
        if skipping:
            skipping = "}" not in line
            continue
        if "=" not in line:
            continue
        key, _, value = line.partition("=")
        value = value.strip()
        if value.startswith("{") and "}" not in value:
            skipping = True
            continue
        key = key.strip()
        if key and key not in label:
            label[key] = value.strip('"').split("<")[0].strip()
    return label
