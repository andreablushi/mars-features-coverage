"""Picking what is drawn: which feature, and the strategy it is judged under."""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass

import ipywidgets as widgets
from IPython.display import display

from coverage import summary
from coverage.results import SetCoverage
from metadata import catalog
from selector import strategies
from selector.models.strategy import Strategy
from utils.disk.slugify import slugify
from visualization.common import panels, sets, surveys

# The feature class the picker opens on.
DEFAULT_CLASS = "Crater"
NO_DATA_SUFFIX = "  (no data)"
DROPDOWN_WIDTH = "300px"


@dataclass(frozen=True, slots=True)
class View:
    """The feature on show and what it is judged against.

    Attributes:
        coverage: The feature's instrument sets, widest coverage first.
        strategy: Which instruments a window over it has to hold.
    """

    coverage: list[SetCoverage]
    strategy: Strategy


class Areas[Chosen]:
    """Areas claimed under a picker, refilled whenever its choice changes."""

    def __init__(self) -> None:
        """Open with nothing claimed yet.

        Returns:
            None.
        """
        self._areas: list[tuple[widgets.Box, Callable[[Chosen], widgets.Widget]]] = []

    @property
    def chosen(self) -> Chosen:
        """Return what the areas are drawn for.

        Returns:
            The current choice, which every claimed area is handed.

        Raises:
            NotImplementedError: When a picker has not said what it picks.
        """
        raise NotImplementedError

    def show_panel(self, render: Callable[[Chosen], widgets.Widget]) -> None:
        """Claim an area here and fill it whenever the choice changes.

        Args:
            render: What to draw in it, given the current choice.

        Returns:
            None.
        """
        area = widgets.VBox()
        self._areas = [claimed for claimed in self._areas if claimed[1] is not render]
        self._areas.append((area, render))
        display(area)
        area.children = (render(self.chosen),)

    def refill(self) -> None:
        """Redraw every claimed area from the current choice.

        Returns:
            None.
        """
        chosen = self.chosen
        for area, _ in self._areas:
            area.children = ()
        for area, render in self._areas:
            area.children = (render(chosen),)


class FeaturePicker(Areas[View]):
    """A feature and strategy picker that fills the areas claimed below it.

    Attributes:
        selection: The confirmed feature class and name, or None until confirmed.
        coverage: The confirmed feature's instrument sets, widest coverage first.
    """

    def __init__(self) -> None:
        """Build the picker from the catalogue and what is computed on disk.

        Returns:
            None.
        """
        super().__init__()
        self._names: dict[str, list[str]] = {}
        for feature in catalog.read_features():
            self._names.setdefault(feature.feature_class, []).append(feature.name)
        for names in self._names.values():
            names.sort()
        self._computed = summary.computed_features()
        self.selection: tuple[str, str] | None = None
        self.coverage: list[SetCoverage] = []
        self._following: list[Callable[[View], None]] = []
        self._class = widgets.Dropdown(
            options=sorted(self._names),
            description="Type:",
            value=DEFAULT_CLASS if DEFAULT_CLASS in self._names else None,
            layout=widgets.Layout(width=DROPDOWN_WIDTH),
        )
        self._name = widgets.Dropdown(
            description="Name:", layout=widgets.Layout(width=DROPDOWN_WIDTH)
        )
        self._strategy = widgets.Dropdown(
            options=sorted(strategies.STRATEGIES),
            description="Strategy:",
            value=surveys.opening().name,
            layout=widgets.Layout(width=DROPDOWN_WIDTH),
        )
        self._confirm = widgets.Button(
            description="Confirm", button_style="primary", icon="check"
        )
        self._status = widgets.VBox()
        self._class.observe(self._refresh_names, names="value")
        self._strategy.observe(self._restrategised, names="value")
        self._confirm.on_click(self._confirmed)
        self._refresh_names()

    @property
    def chosen(self) -> View:
        """Return the feature on show and the strategy it is judged under.

        Returns:
            The view every claimed area is drawn for.
        """
        return View(self.coverage, strategies.named(self._strategy.value))

    def choose(self) -> None:
        """Display the picker.

        Returns:
            None.
        """
        controls = widgets.HBox([self._class, self._name, self._confirm])
        display(widgets.VBox([controls, self._strategy, self._status]))

    def when_chosen(self, follow: Callable[[View], None]) -> None:
        """Call something whenever the feature or the strategy changes.

        Args:
            follow: What to call with the new view, so a picker can rebuild its areas.

        Returns:
            None.
        """
        self._following.append(follow)

    def _has_data(self, feature_class: str, name: str) -> bool:
        """Report whether a feature has computed coverage on disk.

        Args:
            feature_class: The feature class, such as Crater.
            name: The feature name as ODE spells it.

        Returns:
            True when at least one instrument set has been computed for it.
        """
        return (slugify(feature_class), slugify(name)) in self._computed

    def _refresh_names(self, _change=None) -> None:
        """Repopulate the name dropdown for the selected feature class.

        Args:
            _change: The widget change event, ignored.

        Returns:
            None.
        """
        feature_class = self._class.value
        self._name.options = [
            (
                name if self._has_data(feature_class, name) else name + NO_DATA_SUFFIX,
                name,
            )
            for name in self._names[feature_class]
        ]

    def _restrategised(self, _change=None) -> None:
        """Redraw the confirmed feature under the strategy just picked.

        Args:
            _change: The widget change event, ignored.

        Returns:
            None.
        """
        if self.selection is not None:
            self._filled()

    def _confirmed(self, _button=None) -> None:
        """Load the confirmed feature and refill every claimed area.

        Args:
            _button: The button that was clicked, ignored.

        Returns:
            None.
        """
        feature_class, name = self._class.value, self._name.value
        self.selection = (feature_class, name)
        if self._has_data(feature_class, name):
            self.coverage = sets.plotted(summary.load_feature(feature_class, name))
            note = widgets.HTML(
                f"Loaded <b>{feature_class} / {name}</b>. "
                f"The cells below have filled in."
            )
        else:
            self.coverage = []
            note = panels.unavailable(
                f"Nothing has been downloaded or computed for {feature_class} / {name}."
            )
        self._status.children = (note,)
        self._filled()

    def _filled(self) -> None:
        """Refill everything drawn for the current feature and strategy.

        Returns:
            None.
        """
        view = self.chosen
        self.refill()
        for follow in self._following:
            follow(view)
