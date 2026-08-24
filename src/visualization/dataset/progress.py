"""Sweeping the features with a note of how far it has got."""

from __future__ import annotations

import time
from collections.abc import Sequence

import ipywidgets as widgets
from IPython.display import display

from visualization.common import panels
from visualization.dataset import loading
from visualization.dataset.loading import Named, Searched


def swept(wanted: Sequence[Named] | None = None, workers: int = 8) -> list[Searched]:
    """Search features under every strategy, showing how far the sweep has got.

    Args:
        wanted: The features to search, or None for every one computed
            locally.
        workers: How many processes to search on at once.

    Returns:
        One entry per feature and strategy.
    """
    wanted = list(loading.catalogued() if wanted is None else wanted)
    bar = widgets.IntProgress(min=0, max=len(wanted), bar_style="info")
    note = widgets.HTML()
    display(widgets.HBox([bar, note]))
    started = time.monotonic()

    def moved(done: int, total: int) -> None:
        """Move the bar on and say how long is left.

        Args:
            done: How many features are searched.
            total: How many there are.

        Returns:
            None.
        """
        bar.value = done
        note.value = _left(done, total, time.monotonic() - started)

    found = loading.sweep(wanted, workers, moved)
    bar.bar_style = "success"
    note.value = _done(len(wanted), time.monotonic() - started)
    return found


def sample(every: int) -> list[Named]:
    """Take an even sample of the features computed locally.

    Args:
        every: Keep one feature in this many, so the sample spreads over the
            whole catalogue rather than stopping at the first class.

    Returns:
        The sample, in catalogue order.
    """
    return loading.catalogued()[::every]


def _left(done: int, total: int, elapsed: float) -> str:
    """Say how far the sweep has got and how long it has to go.

    Args:
        done: How many features are searched.
        total: How many there are.
        elapsed: How long it has run for, in seconds.

    Returns:
        The note beside the bar.
    """
    remaining = elapsed / done * (total - done)
    return (
        f"<span style='font-family: sans-serif; font-size: 12px;"
        f" color: {panels.GREY}; padding-left: 8px;'>"
        f"{done:,} of {total:,} features, about {remaining / 60:.0f} min left</span>"
    )


def _done(total: int, elapsed: float) -> str:
    """Say the sweep is finished and how long it took.

    Args:
        total: How many features it searched.
        elapsed: How long it took, in seconds.

    Returns:
        The note beside the bar.
    """
    return (
        f"<span style='font-family: sans-serif; font-size: 12px;"
        f" color: {panels.GREY}; padding-left: 8px;'>"
        f"{total:,} features searched in {elapsed / 60:.1f} min</span>"
    )
