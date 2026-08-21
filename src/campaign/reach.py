"""How much ground every instrument holds inside the window being slid along."""

from __future__ import annotations

from collections.abc import Sequence


class Reach:
    """The cells each instrument set covers inside the window currently held.

    A window covers a cell once however many of its observations fill it, so a
    plain sum would count the overlap several times over. Keeping a tally per
    cell instead makes both ends of a sliding window cheap: a cell is new
    ground the moment its tally rises from zero, and is lost again the moment
    it falls back to zero. Nothing here is recomputed from scratch, which is
    what lets the sweep afford a feature holding tens of thousands of
    observations.
    """

    def __init__(self, totals: Sequence[int], grid: int, wanted: int = 0) -> None:
        """Open an empty window over one feature.

        Args:
            totals: How many cells each instrument set fills across its whole
                record, which its reach inside the window is a share of.
            grid: How many cells the feature's grid holds.
            wanted: How many instrument sets the search is insisting on, which
                is how many the score is taken over. Nought for all of them.

        Returns:
            None.
        """
        self._totals = list(totals)
        self._tally = [[0] * grid for _ in self._totals]
        self._seen = [0] * len(self._totals)
        self._held = [0] * len(self._totals)
        self._wanted = wanted or len(self._totals)
        self._present = 0

    def hold(self, owner: int, cells: Sequence[int]) -> None:
        """Take one more observation into the window.

        Args:
            owner: The instrument set the observation belongs to.
            cells: The feature's cells it fills.

        Returns:
            None.
        """
        tally = self._tally[owner]
        fresh = 0
        for cell in cells:
            if not tally[cell]:
                fresh += 1  # ground the window did not hold a moment ago
            tally[cell] += 1
        self._seen[owner] += fresh
        if not self._held[owner]:
            self._present += 1
        self._held[owner] += 1

    def release(self, owner: int, cells: Sequence[int]) -> None:
        """Drop the oldest observation back out of the window.

        Args:
            owner: The instrument set the observation belongs to.
            cells: The feature's cells it fills.

        Returns:
            None.
        """
        tally = self._tally[owner]
        lost = 0
        for cell in cells:
            tally[cell] -= 1
            if not tally[cell]:
                lost += 1  # ground nothing else left in the window reaches
        self._seen[owner] -= lost
        self._held[owner] -= 1
        if not self._held[owner]:
            self._present -= 1

    @property
    def shares(self) -> list[float]:
        """Return what share of its own ground each set reaches in the window.

        Returns:
            One share per instrument set, where 1.0 means the window holds
            everything that set ever covered of this feature.
        """
        pairs = zip(self._seen, self._totals, strict=True)
        return [seen / total for seen, total in pairs]

    @property
    def mean(self) -> float:
        """Return how much ground the window reaches, counting it evenly out.

        The shares are multiplied and rooted rather than added and divided. An
        average would let one instrument carry a window on its own: a hundred
        percent beside two ones averages a third, which is what a window
        serving every instrument evenly also scores. Multiplying refuses that.
        The same three shares come to five percent, and only a window that
        brings every instrument along scores well.

        A set absent from the window counts as zero rather than being left out.
        Were it left out, taking an instrument in could lower the score, the
        window would stop improving as it grows, and the sweep could no longer
        trust that widening only ever helps. Every step of the way this score
        rises when any instrument gains ground and never falls, which is what
        the sweep rests on.

        When the search has settled for fewer instruments than the feature has,
        the score is taken over that many, best first. Otherwise a set the
        search is not asking for would sit at zero and take every window down
        with it.

        Returns:
            The score, between zero and one.
        """
        shares = self.shares
        if self._wanted < len(shares):
            shares = sorted(shares, reverse=True)[: self._wanted]
        product = 1.0
        for share in shares:
            product *= share
        return product ** (1.0 / len(shares))

    @property
    def instruments(self) -> int:
        """Count the instrument sets with an observation in the window.

        Returns:
            The count.
        """
        return self._present
