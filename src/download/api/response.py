"""Reading the containers an ODE response wraps its items in."""

from __future__ import annotations

from typing import Any


def as_items(results: dict[str, Any], container: str, item: str) -> list[Any]:
    """Read a result container's items, tolerating ODE's placeholder strings.

    Args:
        results: The parsed ODEResults object.
        container: The container field name, for example "Products".
        item: The item field name inside the container, for example "Product".

    Returns:
        The items, empty when the container is missing or is a placeholder.
    """
    section = results.get(container)
    if not isinstance(section, dict):
        return []
    found = section.get(item)
    if found is None:
        return []
    return found if isinstance(found, list) else [found]
