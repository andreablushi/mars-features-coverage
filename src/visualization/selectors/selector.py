"""Picking one feature, and the areas that redraw themselves once it is picked."""

from __future__ import annotations

from collections.abc import Callable, Sequence

import ipywidgets as widgets
from IPython.display import display

from models.results import SetCoverage
from storage import catalog, summary
from utils import slugify
from visualization import configs, panels
from visualization.selectors.window import Window

Render = Callable[[Sequence[SetCoverage], Window], widgets.Widget]


class FeatureSelector:
    """A feature picker that fills the areas claimed below it.

    Attributes:
        selection: The confirmed feature class and name, or None until the
            confirm button has been pressed.
        coverage: The confirmed feature's instrument sets, widest coverage
            first, and empty until a feature with local data is confirmed.
        window: The date range the figures are limited to, open at both ends
            until a day is picked.
    """

    def __init__(self) -> None:
        """Build the picker from the catalogue and what is computed on disk.

        Returns:
            None.
        """
        self._names: dict[str, list[str]] = {}
        for feature in catalog.read_features():
            self._names.setdefault(feature.feature_class, []).append(feature.name)
        for names in self._names.values():
            names.sort()
        self._computed = summary.computed_features()
        self.selection: tuple[str, str] | None = None
        self.coverage: list[SetCoverage] = []
        self.window = Window()
        self._areas: list[tuple[widgets.Box, Render]] = []
        self._class = widgets.Dropdown(
            options=sorted(self._names),
            description="Type:",
            value=configs.DEFAULT_CLASS
            if configs.DEFAULT_CLASS in self._names
            else None,
            layout=widgets.Layout(width=configs.DROPDOWN_WIDTH),
        )
        self._name = widgets.Dropdown(
            description="Name:", layout=widgets.Layout(width=configs.DROPDOWN_WIDTH)
        )
        self._confirm = widgets.Button(
            description="Confirm", button_style="primary", icon="check"
        )
        self._from = widgets.DatePicker(
            description="From:", layout=widgets.Layout(width=configs.DATE_PICKER_WIDTH)
        )
        self._to = widgets.DatePicker(
            description="To:", layout=widgets.Layout(width=configs.DATE_PICKER_WIDTH)
        )
        self._status = widgets.VBox()
        self._class.observe(self._refresh_names, names="value")
        self._confirm.on_click(self._confirmed)
        self._from.observe(self._retimed, names="value")
        self._to.observe(self._retimed, names="value")
        self._refresh_names()

    def choose(self) -> None:
        """Display the picker and report what the catalogue holds.

        Returns:
            None.
        """
        catalogued = sum(len(names) for names in self._names.values())
        print(f"{catalogued} catalogued features in {len(self._names)} classes")
        print(f"{len(self._computed)} with coverage computed locally")
        controls = widgets.HBox([self._class, self._name, self._confirm])
        dates = widgets.HBox(
            [
                widgets.HTML(
                    f"<div style='color: {configs.GREY}; padding: 4px 8px 0 0'>"
                    f"Date range (optional):</div>"
                ),
                self._from,
                self._to,
            ]
        )
        display(widgets.VBox([controls, dates, self._status]))

    def show_panel(self, render: Render) -> None:
        """Claim an area here and fill it whenever a feature is confirmed.

        Args:
            render: What to draw in it, given the confirmed feature's coverage
                and the date range to limit it to. It is called with an empty
                sequence while nothing is confirmed, which is when it should
                show the grey panel.

        Returns:
            None.
        """
        area = widgets.VBox()
        self._areas = [claimed for claimed in self._areas if claimed[1] is not render]
        self._areas.append((area, render))
        display(area)
        area.children = (render(self.coverage, self.window),)

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
                name
                if self._has_data(feature_class, name)
                else name + configs.NO_DATA_SUFFIX,
                name,
            )
            for name in self._names[feature_class]
        ]

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
            self.coverage = summary.load_feature(feature_class, name)
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
        self._refill()

    def _retimed(self, _change=None) -> None:
        """Limit every claimed area to the picked date range.

        Args:
            _change: The widget change event, ignored.

        Returns:
            None.
        """
        self.window = Window.between(self._from.value, self._to.value)
        self._refill()

    def _refill(self) -> None:
        """Redraw every claimed area from the current feature and window.

        Returns:
            None.
        """
        for area, render in self._areas:
            area.children = (render(self.coverage, self.window),)
