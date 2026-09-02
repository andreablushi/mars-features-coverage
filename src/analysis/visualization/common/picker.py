"""Picking what is drawn: which feature, and the strategy it is judged under."""

from __future__ import annotations

from collections.abc import Callable, Sequence
from dataclasses import dataclass

import ipywidgets as widgets
from IPython.display import display

import analysis.utils.settings as settings
from analysis.coverage import summary
from analysis.coverage.results import SetCoverage
from analysis.metadata import catalog
from analysis.selector import strategies
from analysis.selector.models.strategy import Strategy
from analysis.visualization.common import panels, surveys
from analysis.visualization.common.areas import Areas
from utils.disk.slugify import slugify

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


def drawn_sets(coverage: Sequence[SetCoverage]) -> list[SetCoverage]:
    """Keep the instrument sets the config draws, in the order it names them.

    Args:
        coverage: Every instrument set loaded for one feature.

    Returns:
        The sets the config names, in the order it names them.
    """
    config = settings.load()
    wanted = config.plot_instrument_sets
    # A config naming no set draws every one, in the order the config ranks them
    keys = {chosen.key for chosen in wanted or ()}
    kept = (
        list(coverage)
        if wanted is None
        else [one for one in coverage if one.summary.set_key in keys]
    )
    ranks = {
        chosen.key: rank for rank, chosen in enumerate(wanted or config.instrument_sets)
    }
    return sorted(
        kept, key=lambda instrument: ranks.get(instrument.summary.set_key, len(ranks))
    )


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
        self._class = _dropdown(
            "Type:", options=sorted(self._names), value=DEFAULT_CLASS
        )
        self._name = _dropdown("Name:")
        self._strategy = _dropdown(
            "Strategy:",
            options=sorted(strategies.STRATEGIES),
            value=surveys.opening().name,
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
            self.coverage = drawn_sets(summary.load_feature(feature_class, name))
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


def _dropdown(
    description: str, options: Sequence[str] = (), value: str | None = None
) -> widgets.Dropdown:
    """Build one of the picker's dropdowns, all set to the same width.

    Args:
        description: The label beside it.
        options: What it offers, and nothing until a choice above fills it.
        value: What it opens on, ignored where it is not on offer.

    Returns:
        The dropdown.
    """
    return widgets.Dropdown(
        description=description,
        options=options,
        value=value if value in options else None,
        layout=widgets.Layout(width=DROPDOWN_WIDTH),
    )
