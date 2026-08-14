"""Reading the project's config file, and ranking it against the flags.

Both stages answer the same questions from three places, so the ranking is
decided once here: a flag passed on the command line wins, then the config
file, then the built-in default. A flag that was not passed has to be absent
rather than false or zero for the file to speak for it, which is why every flag
either stage reads from here defaults to None in its parser.

The file is optional and a missing one just means defaults, but a file that is
present and holds something unusable raises rather than falling back, because a
typo would otherwise quietly change what a run does.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

import yaml

from common.configs import CONFIG_PATH


def section(name: str, path: Path = CONFIG_PATH) -> dict[str, Any]:
    """Read one stage's section of the config file.

    Args:
        name: The section to read, such as "download".
        path: The config file, which need not exist.

    Returns:
        The section's keys, empty when the file or the section is absent.

    Raises:
        ValueError: When the file or the section is not a mapping.
    """
    if not path.exists():
        return {}
    loaded = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    if not isinstance(loaded, dict):
        raise ValueError(f"{path} should hold a mapping, found {type(loaded).__name__}")
    found = loaded.get(name)
    if found is None:
        return {}
    if not isinstance(found, dict):
        raise ValueError(f"{path}: `{name}` should hold a mapping of settings")
    return found


def first(*candidates: Any) -> Any:
    """Return the first candidate that was actually given.

    Args:
        candidates: The sources in priority order, the flag first and the
            built-in default last.

    Returns:
        The first one that is not None.
    """
    return next(value for value in candidates if value is not None)


def positive_int(value: Any, name: str) -> int:
    """Check that a setting is a count a run can be given.

    Args:
        value: The settled value.
        name: What to call it if it has to be rejected.

    Returns:
        The value unchanged.

    Raises:
        ValueError: When it is not a positive whole number.
    """
    if not isinstance(value, int) or isinstance(value, bool) or value < 1:
        raise ValueError(f"{name} should be a positive whole number, found {value!r}")
    return value


def boolean(value: Any, name: str) -> bool:
    """Check that a setting is a plain yes or no.

    Args:
        value: The settled value.
        name: What to call it if it has to be rejected.

    Returns:
        The value unchanged.

    Raises:
        ValueError: When it is not true or false.
    """
    if not isinstance(value, bool):
        raise ValueError(f"{name} should be true or false, found {value!r}")
    return value
