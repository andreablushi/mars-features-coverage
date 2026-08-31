"""Picking one observation to clean, and holding what the cleaning left."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

import ipywidgets as widgets
from IPython.display import display

from preprocessing.crism import cleaning
from preprocessing.crism.models.stage import Stage
from preprocessing.crism.models.strip import Strip
from utils.disk import paths
from visualization.common.areas import Areas
from visualization.preprocessing import fetching

# How wide the observation list is drawn.
DROPDOWN_WIDTH = "340px"

# What the status line says while the work is going on.
FETCHING = "Fetching {product}, about 37 MB the first time."
CLEANING = "Cleaning {product}."
READY = "{product}: {lines} lines, {samples} samples, {bands} bands."


@dataclass(frozen=True, slots=True)
class Cleaned:
    """One observation and every step of its cleaning.

    Attributes:
        strip: The observation as loaded, before anything was done to it.
        stages: What each step left, the cube as read first.
    """

    strip: Strip
    stages: list[Stage]

    @property
    def final(self) -> Stage:
        """Return the stage the cleaning ended on.

        Returns:
            The last stage.
        """
        return self.stages[-1]


class StripPicker(Areas[Cleaned | None]):
    """Picks one observation at a time and cleans it on confirmation."""

    def __init__(self, count: int = 8, seed: int | None = None) -> None:
        """Offer a handful of observations drawn from the selected metadata.

        Args:
            count: How many observations to offer in the list.
            seed: Fixes the draw so a run can be repeated, or None to vary it.

        Returns:
            None.
        """
        super().__init__()
        self._cleaned: Cleaned | None = None
        self._products = widgets.Dropdown(
            options=fetching.sample(count, seed),
            description="Observation",
            layout=widgets.Layout(width=DROPDOWN_WIDTH),
            style={"description_width": "initial"},
        )
        self._confirm = widgets.Button(
            description="Clean", button_style="primary", icon="check"
        )
        self._status = widgets.HTML()
        self._confirm.on_click(self._confirmed)

    @property
    def chosen(self) -> Cleaned | None:
        """Return the observation the panels are drawn for.

        Returns:
            The cleaned observation, or None while none has been confirmed.
        """
        return self._cleaned

    def choose(self) -> None:
        """Show the list and the button that fetches and cleans.

        Returns:
            None.
        """
        controls = widgets.HBox([self._products, self._confirm])
        display(widgets.VBox([controls, self._status]))

    def load(self, path: Path) -> None:
        """Clean an observation already on disk, instead of picking one.

        Args:
            path: Either the `.lbl` or the `.img` of the observation.

        Returns:
            None.
        """
        self._cleaned = _cleaned(path)
        self._status.value = _ready(self._cleaned)
        self.refill()

    def _confirmed(self, _button: widgets.Button | None = None) -> None:
        """Fetch the chosen observation, clean it, and redraw every panel.

        Args:
            _button: Unused, supplied by the widget.

        Returns:
            None.
        """
        product = str(self._products.value)
        self._confirm.disabled = True
        try:
            self._status.value = FETCHING.format(product=product)
            label = fetching.fetch(product, paths.CRISM_ROOT)
            self._status.value = CLEANING.format(product=product)
            self._cleaned = _cleaned(label)
            self._status.value = _ready(self._cleaned)
        except (OSError, ValueError) as exc:
            self._cleaned = None
            self._status.value = f"{product} could not be read: {exc}"
        finally:
            self._confirm.disabled = False
        self.refill()


def _cleaned(path: Path) -> Cleaned:
    """Load one observation and run the cleaning over it.

    Args:
        path: Either the `.lbl` or the `.img` of the observation.

    Returns:
        The observation and every step of its cleaning.
    """
    strip = cleaning.load(path)
    return Cleaned(strip=strip, stages=cleaning.stages(strip))


def _ready(cleaned: Cleaned) -> str:
    """Describe a loaded observation in one line.

    Args:
        cleaned: The observation and its stages.

    Returns:
        The line to show beside the picker.
    """
    lines, samples, bands = cleaned.strip.cube.shape
    return READY.format(
        product=cleaned.strip.product_id, lines=lines, samples=samples, bands=bands
    )
