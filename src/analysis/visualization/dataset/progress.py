"""Reading the prediction with a note of how far any sweep it runs has got."""

from __future__ import annotations

import time

import ipywidgets as widgets
from IPython.display import display

import analysis.utils.settings as settings
from analysis.stats.dataset import reading
from analysis.stats.models.dataset import DatasetStats
from analysis.visualization.common import panels

_NOTE = (
    "<span style='font-family: sans-serif; font-size: 12px;"
    " color: {colour}; padding-left: 8px;'>{text}</span>"
)


class _Bar:
    """The bar and the grey line beside it, shown while a sweep runs."""

    def __init__(self, total: int) -> None:
        """Show an empty bar, claimed the first time a sweep reports anything.

        Args:
            total: How many features the sweep runs over.

        Returns:
            None.
        """
        self._started = time.monotonic()
        self._bar = widgets.IntProgress(min=0, max=total, bar_style="info")
        self._note = widgets.HTML()
        display(widgets.HBox([self._bar, self._note]))

    def moved(self, done: int, total: int) -> None:
        """Move the bar on and say how long the rest looks like taking.

        Args:
            done: How many features are read.
            total: How many there are.

        Returns:
            None.
        """
        left = self._elapsed / done * (total - done)
        self._bar.value = done
        self._say(f"{done:,} of {total:,} features, about {left / 60:.0f} min left")

    def closed(self) -> None:
        """Fill the bar in and say how long the sweep took.

        Returns:
            None.
        """
        self._bar.bar_style = "success"
        self._say(f"{self._bar.max:,} features read in {self._elapsed / 60:.1f} min")

    def _say(self, text: str) -> None:
        """Write the grey line beside the bar.

        Args:
            text: What it reads.

        Returns:
            None.
        """
        self._note.value = _NOTE.format(colour=panels.GREY, text=text)

    @property
    def _elapsed(self) -> float:
        """Report how long the sweep has been running.

        Returns:
            The seconds since the bar was first shown.
        """
        return time.monotonic() - self._started


def read() -> DatasetStats:
    """Read what the filter makes of the dataset, showing any sweep it runs.

    Any sweep it has to run measures on as many processes as `runner.yaml` asks.

    Returns:
        The stats the filter leaves over every measured feature.
    """
    shown: _Bar | None = None

    def moved(done: int, total: int) -> None:
        """Show the bar on the first report, and move it on after that.

        Args:
            done: How many features are read.
            total: How many there are.

        Returns:
            None.
        """
        nonlocal shown
        if shown is None:
            shown = _Bar(total)
        shown.moved(done, total)

    found = reading.read_dataset_stats(settings.load().workers, moved)
    if shown is not None:
        shown.closed()
    return found
