"""Field selection for raw ODE product items."""

from __future__ import annotations

from collections.abc import Mapping
from typing import Any

from download import configs


def retain_fields(item: Mapping[str, Any]) -> dict[str, Any]:
    """Keep only the ODE product fields the pipeline stores.

    Args:
        item: One raw product object from an ODE response.

    Returns:
        A new dict holding the retained fields that are present.
    """
    return {field: item[field] for field in configs.RETAINED_FIELDS if field in item}
