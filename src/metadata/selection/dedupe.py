"""Order preserving deduplication by an arbitrary key."""

from __future__ import annotations

from collections.abc import Callable, Hashable, Iterable


def dedupe[T](items: Iterable[T], key: Callable[[T], Hashable]) -> list[T]:
    """Keep the first item seen for each key, preserving input order.

    Args:
        items: The items to deduplicate.
        key: Returns the hashable identity of an item.

    Returns:
        The unique items in their original order.
    """
    seen: set[Hashable] = set()
    unique: list[T] = []
    for item in items:
        identity = key(item)
        if identity in seen:
            continue
        seen.add(identity)
        unique.append(item)
    return unique
