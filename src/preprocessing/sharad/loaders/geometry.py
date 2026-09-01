"""Loading the geometry published beside one SHARAD radargram."""

from __future__ import annotations

import numpy as np

from preprocessing.pds import labels, tables
from preprocessing.sharad.loaders.utils import locations, naming


def load(observation_id: str) -> tuple[np.recarray, dict[str, str]]:
    """Read one track's geometry off disk.

    Args:
        observation_id: The observation, whose files must already be in the
            cache that `download.fetch` puts them in.

    Returns:
        One row per radargram column, its fields named as the label names its
        columns, and the parsed label describing them.

    Raises:
        FileNotFoundError: When the table or its label is missing.
        ValueError: When the table holds fewer rows than the label promises.
    """
    table = locations.files(observation_id, naming.GEOMETRY)[".tab"]
    path = table.with_suffix(".lbl")
    label = labels.load(path)
    return tables.build_table(table, label, tables.columns(path)), label
