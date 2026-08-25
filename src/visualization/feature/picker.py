"""Picking one tile of the feature on show, and what it is drawn from."""

from __future__ import annotations

from dataclasses import dataclass

import ipywidgets as widgets
from IPython.display import display

from survey.models.survey import Survey
from survey.models.track import Track
from visualization.common import panels, surveys, tiles
from visualization.common.picker import Areas, FeaturePicker, View
from visualization.common.surveys import Stretch
from visualization.common.tiles import TileStats

NO_TILE = "Confirm a feature above and pick one of its tiles to fill this in."
NO_TILES = "No tile of this feature holds anything to search."
DROPDOWN_WIDTH = "420px"

# How a tile that earned a window is marked in the list, and one that did not.
PASSED = "PASS"
FAILED = "NOT PASS"


@dataclass(frozen=True, slots=True)
class TileView:
    """One tile of the feature on show, and what the search left on it.

    Attributes:
        view: The feature it belongs to and the strategy it was searched under.
        track: Its admissible observations on one time axis.
        survey: The window it earned, or None when it earned none.
        stats: What it holds, read off the search that ran over it.
        across: How many tiles the feature was cut into along each axis.
    """

    view: View
    track: Track
    survey: Survey | None
    stats: TileStats
    across: int

    @property
    def name(self) -> str:
        """Name the tile by where it sits on the feature.

        Returns:
            The feature and the tile's place on its grid, from the south west.
        """
        return (
            f"{panels.title(self.view.coverage)}  -  "
            f"tile at row {self.stats.row + 1}, column {self.stats.column + 1}"
        )

    @property
    def open_for(self) -> list[Stretch]:
        """Return the stretch of time the tile's window is open over.

        Returns:
            The one stretch it earned, and nothing at all when it earned none.
        """
        if self.survey is None:
            return []
        return [(self.survey.start, self.survey.end)]


class TilePicker(Areas[TileView | None]):
    """A tile picker that follows the feature picker above it."""

    def __init__(self, picker: FeaturePicker) -> None:
        """Follow one feature picker, and offer whatever it confirms.

        Args:
            picker: The feature picker whose choice the tiles come from.

        Returns:
            None.
        """
        super().__init__()
        self._held: list[TileView] = []
        self._loading = False
        self._choice = widgets.Dropdown(
            description="Tile:", layout=widgets.Layout(width=DROPDOWN_WIDTH)
        )
        self._status = widgets.VBox()
        self._choice.observe(self._picked, names="value")
        picker.when_chosen(self._follows)
        if picker.selection is not None:
            self._follows(picker.chosen)

    @property
    def chosen(self) -> TileView | None:
        """Return the tile on show.

        Returns:
            The picked tile, or None while none is picked.
        """
        at = self._choice.value
        return self._held[at] if at is not None and at < len(self._held) else None

    def choose(self) -> None:
        """Display the tile picker.

        Returns:
            None.
        """
        display(widgets.VBox([self._choice, self._status]))

    def _follows(self, view: View) -> None:
        """Rebuild the tile list from the feature the picker just confirmed.

        Args:
            view: The feature on show and the strategy it is judged under.

        Returns:
            None.
        """
        self._held = _tiles(view)
        self._loading = True
        self._choice.options = [
            (_named(held), at) for at, held in enumerate(self._held)
        ]
        self._loading = False
        self._status.children = () if self._held else (panels.unavailable(NO_TILES),)
        self.refill()

    def _picked(self, _change=None) -> None:
        """Redraw every claimed area for the tile just picked.

        Args:
            _change: The widget change event, ignored.

        Returns:
            None.
        """
        if not self._loading:
            self.refill()


def _tiles(view: View) -> list[TileView]:
    """Read every tile of the feature the search ran over.

    Args:
        view: The feature on show and the strategy it is judged under.

    Returns:
        One entry per tile, in the order the patchwork lays them out.
    """
    if not view.coverage:
        return []
    study = surveys.studied(view.coverage, view.strategy)
    return [
        TileView(
            view=view,
            track=track,
            survey=picked,
            stats=stats,
            across=study.patchwork.across,
        )
        for track, picked, stats in zip(
            study.tracks, study.surveys, tiles.measured(study), strict=True
        )
    ]


def _named(held: TileView) -> str:
    """Name one tile as the list shows it.

    Args:
        held: The tile.

    Returns:
        Where it sits, how many observations it holds, and whether it was kept.
    """
    stats = held.stats
    return (
        f"row {stats.row + 1}, column {stats.column + 1}  -  "
        f"{len(held.track.observations):,} observations  -  "
        f"{PASSED if stats.kept else FAILED}"
    )
