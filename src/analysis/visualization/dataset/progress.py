"""Reading the prediction with a note of how far any sweep it runs has got."""

from __future__ import annotations

import time
from dataclasses import dataclass

import ipywidgets as widgets
from IPython.display import display

from analysis.sampling import sweeping
from analysis.sampling.models.dataset import DatasetStats
from analysis.visualization.common import panels


@dataclass(frozen=True, slots=True)
class _Bar:
    """The bar and the grey line beside it, shown while a sweep runs.

    Attributes:
        bar: The bar itself, filling as the features are searched.
        note: The line beside it, saying how far the sweep has got.
        started: When it was first shown, which is what the estimate runs from.
    """

    bar: widgets.IntProgress
    note: widgets.HTML
    started: float

    @classmethod
    def opened(cls, total: int) -> _Bar:
        """Show an empty bar, claimed the first time a sweep reports anything.

        Args:
            total: How many features the sweep runs over.

        Returns:
            The bar.
        """
        shown = cls(
            bar=widgets.IntProgress(min=0, max=total, bar_style="info"),
            note=widgets.HTML(),
            started=time.monotonic(),
        )
        display(widgets.HBox([shown.bar, shown.note]))
        return shown

    def moved(self, done: int, total: int) -> None:
        """Move the bar on and say how long the rest looks like taking.

        Args:
            done: How many features are searched.
            total: How many there are.

        Returns:
            None.
        """
        left = self.elapsed / done * (total - done)
        self.bar.value = done
        self.note.value = _note(
            f"{done:,} of {total:,} features, about {left / 60:.0f} min left"
        )

    def closed(self) -> None:
        """Fill the bar in and say how long the sweep took.

        Returns:
            None.
        """
        self.bar.bar_style = "success"
        self.note.value = _note(
            f"{self.bar.max:,} features searched in {self.elapsed / 60:.1f} min"
        )

    @property
    def elapsed(self) -> float:
        """Report how long the sweep has been running.

        Returns:
            The seconds since the bar was first shown.
        """
        return time.monotonic() - self.started


def read(workers: int = 8) -> DatasetStats:
    """Read what the filter makes of the dataset, showing any sweep it runs.

    Args:
        workers: How many processes to search on at once.

    Returns:
        The stats the filter leaves over every measured feature.
    """
    shown: _Bar | None = None

    def moved(done: int, total: int) -> None:
        """Show the bar on the first report, and move it on after that.

        Args:
            done: How many features are searched.
            total: How many there are.

        Returns:
            None.
        """
        nonlocal shown
        if shown is None:
            shown = _Bar.opened(total)
        shown.moved(done, total)

    found = sweeping.read_prediction(workers, moved)
    if shown is not None:
        shown.closed()
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
