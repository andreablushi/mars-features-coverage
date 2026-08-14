"""Picking one feature, and the areas that redraw themselves once it is picked.

Running the notebook top to bottom cannot pause at the picker, because the
kernel runs the queued cells straight through. So the cells below the picker do
not read a chosen feature, they claim an area and register how to fill it.
Confirming loads the feature once and refills every claimed area in place, which
is also what makes a second choice update the plots without rerunning anything.

An area is a container holding exactly one widget, and refilling it replaces
that widget. Capturing cell output into it would be the obvious alternative and
is the wrong one: a redraw runs inside a button callback, where a request to
clear captured output never takes effect, so every confirm would stack another
copy on the ones before it.

The catalogue holds far more features than have ever been downloaded, so a name
carries whether anything was computed for it. Choosing one that has nothing is
allowed and answered with the grey panel, which is what tells a missing plot
apart from an empty one.
"""

from __future__ import annotations

from collections.abc import Callable, Sequence

import ipywidgets as widgets
from IPython.display import display

from analysis.loader import artifacts
from analysis.models.coverage import SetCoverage
from common.files import slugify
from download.storage import cache
from visualization import panels

Render = Callable[[Sequence[SetCoverage]], widgets.Widget]

_DEFAULT_CLASS = "Crater"
_NO_DATA_SUFFIX = "  (no data)"
_DROPDOWN_WIDTH = "340px"


class FeatureSelector:
    """A feature picker that fills the areas claimed below it.

    Attributes:
        selection: The confirmed feature class and name, or None until the
            confirm button has been pressed.
        coverage: The confirmed feature's instrument sets, widest coverage
            first, and empty until a feature with local data is confirmed.
    """

    def __init__(self) -> None:
        """Build the picker from the catalogue and what is computed on disk.

        Returns:
            None.
        """
        self._names = _names_by_class()
        self._computed = artifacts.computed_features()
        self.selection: tuple[str, str] | None = None
        self.coverage: list[SetCoverage] = []
        self._areas: list[tuple[widgets.Box, Render]] = []
        self._class = widgets.Dropdown(
            options=sorted(self._names),
            description="Type:",
            value=_DEFAULT_CLASS if _DEFAULT_CLASS in self._names else None,
            layout=widgets.Layout(width=_DROPDOWN_WIDTH),
        )
        self._name = widgets.Dropdown(
            description="Name:", layout=widgets.Layout(width=_DROPDOWN_WIDTH)
        )
        self._confirm = widgets.Button(
            description="Confirm", button_style="primary", icon="check"
        )
        self._status = widgets.VBox()
        self._class.observe(self._refresh_names, names="value")
        self._confirm.on_click(self._confirmed)
        self._refresh_names()

    def show(self) -> None:
        """Display the picker and report what the catalogue holds.

        Returns:
            None.
        """
        catalogued = sum(len(names) for names in self._names.values())
        print(f"{catalogued} catalogued features in {len(self._names)} classes")
        print(f"{len(self._computed)} with coverage computed locally")
        controls = widgets.HBox([self._class, self._name, self._confirm])
        display(widgets.VBox([controls, self._status]))

    def show_panel(self, render: Render) -> None:
        """Claim an area here and fill it whenever a feature is confirmed.

        Rerunning the cell claims a fresh area and drops the one it replaces,
        which is what stops a second run from drawing the same thing twice.

        Args:
            render: What to draw in it, given the confirmed feature's coverage.
                It is called with an empty sequence while nothing is confirmed,
                which is when it should show the grey panel.

        Returns:
            None.
        """
        area = widgets.VBox()
        self._areas = [claimed for claimed in self._areas if claimed[1] is not render]
        self._areas.append((area, render))
        display(area)
        self._fill(area, render)

    def _fill(self, area: widgets.Box, render: Render) -> None:
        """Redraw one claimed area from the current coverage.

        Args:
            area: The container to refill, which ends up holding one widget.
            render: What to build for it.

        Returns:
            None.
        """
        area.children = (render(self.coverage),)

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
                name if self._has_data(feature_class, name) else name + _NO_DATA_SUFFIX,
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
            self.coverage = artifacts.load_feature(feature_class, name)
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
        for area, render in self._areas:
            self._fill(area, render)


def _names_by_class() -> dict[str, list[str]]:
    """Group the catalogued feature names under their class.

    Returns:
        The sorted names of every catalogued feature, keyed by feature class.
    """
    grouped: dict[str, list[str]] = {}
    for feature in cache.read_features():
        grouped.setdefault(feature.feature_class, []).append(feature.name)
    for names in grouped.values():
        names.sort()
    return grouped
