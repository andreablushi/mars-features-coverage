"""The written dataset, as the one thing another repository has to hold."""

from __future__ import annotations

import random
from dataclasses import dataclass
from pathlib import Path
from typing import TYPE_CHECKING

from building.metadata.models.feature import FeatureFrame
from building.metadata.models.observation import ObservationRecord

if TYPE_CHECKING:
    import xarray

Key = tuple[str, str]


@dataclass(frozen=True, slots=True)
class Dataset:
    """Every crop that was built, and where each of them sits.

    Attributes:
        root: The dataset's own directory, which every path is relative to.
        frames: The local frame of each feature, by class and name.
        records: What each crop is, in the order they were written.
    """

    root: Path
    frames: dict[Key, FeatureFrame]
    records: tuple[ObservationRecord, ...]

    @property
    def features(self) -> list[Key]:
        """Return every feature the dataset holds a crop of.

        Returns:
            The class and name of each, sorted.
        """
        return sorted({(one.feature_class, one.feature_name) for one in self.records})

    def crops(
        self, feature: Key | None = None, instrument: str | None = None
    ) -> list[ObservationRecord]:
        """Return the crops matching a feature, an instrument, or both.

        Args:
            feature: The feature to keep, by class and name, or None for every one.
            instrument: The instrument to keep, or None for every one.

        Returns:
            The records that match, in the order they were written.
        """
        return [
            one
            for one in self.records
            if (feature is None or (one.feature_class, one.feature_name) == feature)
            and (instrument is None or one.instrument == instrument)
        ]

    def open(self, held: ObservationRecord) -> xarray.Dataset:
        """Open one crop, its arrays left on disk until they are asked for.

        Args:
            held: The record naming the crop to open.

        Returns:
            The crop, its measurement placed by the north and east coordinates
            beside it, in metres of latitude and longitude from the feature's
            own centre.

        Raises:
            ModuleNotFoundError: When xarray is not installed, which is the
                reader's own choice and never the pipeline's.
        """
        import xarray

        return xarray.open_zarr(self.root / held.path, consolidated=False)

    def split(self, seed: int = 0, **shares: float) -> dict[str, list[Key]]:
        """Draw a split of the features, each one landing whole in one part.

        A feature is split and never an observation, since one feature is seen
        in many observations and splitting those would put the same ground on
        both sides of the split.

        Args:
            seed: The number to draw with, so the same seed gives the same split.
            shares: What share of the features each part takes, named as the
                parts are, such as train=0.8, test=0.2. They are taken in
                proportion, so they need not add to one.

        Returns:
            The features of each part, keyed by the name it was asked for.

        Raises:
            ValueError: When no share is asked for, or they are not above zero.
        """
        if not shares or min(shares.values()) <= 0:
            raise ValueError("a split needs a share above zero for every part")
        held = self.features
        random.Random(seed).shuffle(held)
        whole = sum(shares.values())
        parts: dict[str, list[Key]] = {}
        at = 0
        for position, (name, share) in enumerate(shares.items(), start=1):
            # The last part takes what is left, so nothing is lost to rounding.
            until = (
                len(held)
                if position == len(shares)
                else at + round(len(held) * share / whole)
            )
            parts[name] = sorted(held[at:until])
            at = until
        return parts

    def __len__(self) -> int:
        """Return how many crops the dataset holds.

        Returns:
            One per crop that was written.
        """
        return len(self.records)

    def __getitem__(self, at: int) -> xarray.Dataset:
        """Return one crop by position, so the dataset reads as a sequence.

        Args:
            at: Which crop to open, counted from zero.

        Returns:
            The crop at that position, opened.
        """
        return self.open(self.records[at])
