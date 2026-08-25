"""Sweeping the features with a note of how far it has got."""

from __future__ import annotations

import time
from collections.abc import Sequence

import ipywidgets as widgets
from IPython.display import display

from storage import summary
from visualization.common import panels
from visualization.dataset import loading
from visualization.dataset.loading import Named, Searched


def swept(
    under: Sequence[str], wanted: Sequence[Named] | None = None, workers: int = 8
) -> list[Searched]:
    """Search features under the strategies named, showing how far it has got.

    Args:
        under: The strategies to search under, by name.
        wanted: The features to search, or None for every one computed locally.
        workers: How many processes to search on at once.

    Returns:
        One entry per feature and strategy.
    """
    wanted = list(summary.catalogued_features() if wanted is None else wanted)
    bar = widgets.IntProgress(min=0, max=len(wanted), bar_style="info")
    note = widgets.HTML()
    display(widgets.HBox([bar, note]))
    started = time.monotonic()

    def moved(done: int, total: int) -> None:
        """Move the bar on and say how long the sweep has left.

        Args:
            done: How many features are searched.
            total: How many there are.

        Returns:
            None.
        """
        left = (time.monotonic() - started) / done * (total - done)
        note.value = _note(
            f"{done:,} of {total:,} features, about {left / 60:.0f} min left"
        )
        bar.value = done

    found = loading.sweep(under, wanted, workers, moved)
    bar.bar_style = "success"
    note.value = _note(
        f"{len(wanted):,} features searched in "
        f"{(time.monotonic() - started) / 60:.1f} min"
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
