"""Reading the prediction with a note of how far any sweep it runs has got."""

from __future__ import annotations

import time

import ipywidgets as widgets
from IPython.display import display

from prediction import predicting
from prediction.models.dataset import DatasetStats
from visualization.common import panels


def read(workers: int = 8) -> dict[str, DatasetStats]:
    """Read what every strategy makes of the dataset, showing any sweep it runs.

    Args:
        workers: How many processes to search on at once.

    Returns:
        The stats each strategy leaves, by name, in the order they are written.
    """
    shown: dict[str, object] = {}

    def moved(done: int, total: int) -> None:
        """Move the bar on, claiming it the first time a sweep reports anything.

        Args:
            done: How many features are searched.
            total: How many there are.

        Returns:
            None.
        """
        if not shown:
            shown["bar"] = widgets.IntProgress(min=0, max=total, bar_style="info")
            shown["note"] = widgets.HTML()
            shown["started"] = time.monotonic()
            display(widgets.HBox([shown["bar"], shown["note"]]))
        elapsed = time.monotonic() - shown["started"]
        left = elapsed / done * (total - done)
        shown["bar"].value = done
        shown["note"].value = _note(
            f"{done:,} of {total:,} features, about {left / 60:.0f} min left"
        )

    found = predicting.read(workers, moved)
    if shown:
        shown["bar"].bar_style = "success"
        elapsed = time.monotonic() - shown["started"]
        shown["note"].value = _note(
            f"{shown['bar'].max:,} features searched in {elapsed / 60:.1f} min"
        )
    return found


def _note(text: str) -> str:
    """Write the grey line beside the bar.

    Args:
        text: What it reads.

    Returns:
        The line.
    """
    return (
        f"<span style='font-family: sans-serif; font-size: 12px;"
        f" color: {panels.GREY}; padding-left: 8px;'>{text}</span>"
    )
