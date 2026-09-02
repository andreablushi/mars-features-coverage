"""Areas a notebook claims under a picker, refilled whenever its choice changes."""

from __future__ import annotations

from collections.abc import Callable

import ipywidgets as widgets
from IPython.display import display


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
