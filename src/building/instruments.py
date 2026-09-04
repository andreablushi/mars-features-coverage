"""What each instrument does at every stage of a build, declared in one place."""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from building.common.layout import Layout
from building.configs import crism as crism_configs
from building.configs import ctx as ctx_configs
from building.configs import mola as mola_configs
from building.configs import sharad as sharad_configs
from building.crop.crism import crop as crism_crop
from building.crop.ctx import crop as ctx_crop
from building.crop.mola import crop as mola_crop
from building.crop.sharad import crop as sharad_crop
from building.download.crism import download as crism_download
from building.download.ctx import download as ctx_download
from building.download.mola import download as mola_download
from building.download.sharad import download as sharad_download
from building.geometry.crism import place as crism_place
from building.geometry.ctx import place as ctx_place
from building.geometry.mola import place as mola_place
from building.geometry.sharad import altitude
from building.geometry.sharad import place as sharad_place
from building.preprocessing.crism import read as crism_read
from building.preprocessing.ctx import read as ctx_read
from building.preprocessing.mola import read as mola_read
from building.preprocessing.sharad import read as sharad_read
from building.writing.crism import crop as crism_write
from building.writing.ctx import crop as ctx_write
from building.writing.mola import crop as mola_write
from building.writing.sharad import crop as sharad_write


@dataclass(frozen=True, slots=True)
class Instrument:
    """How one instrument goes from a product ODE holds to a crop in the dataset.

    Attributes:
        layout: What its arrays hold, and which of them it is stored for.
        fetch: What brings one product of it down into the cache.
        sample: What reads a fetched product off disk into its own sample.
        place: What places that sample against one feature.
        crop: What cuts it to that feature.
        write: What writes the crop into the dataset.
        observation_id: What reads which observation a product the selection
            kept belongs to, or None for a gridded instrument the selection can
            never name.
        altitude: What reads how high the spacecraft flew, for a sounder whose
            delay axis is read through it, and None for every other instrument.
    """

    layout: Layout
    fetch: Callable[..., Any]
    sample: Callable[[str], Any]
    place: Callable[..., Any]
    crop: Callable[..., Any]
    write: Callable[..., Path]
    observation_id: Callable[[str], str | None] | None = None
    altitude: Callable[[Any], tuple[float, float]] | None = None


INSTRUMENTS = {
    crism_configs.LAYOUT.instrument: Instrument(
        crism_configs.LAYOUT,
        crism_download.fetch,
        crism_read.read_sample,
        crism_place.place,
        crism_crop.crop,
        crism_write.write,
        observation_id=crism_download.observation_id,
    ),
    ctx_configs.LAYOUT.instrument: Instrument(
        ctx_configs.LAYOUT,
        ctx_download.fetch,
        ctx_read.read,
        ctx_place.place,
        ctx_crop.crop,
        ctx_write.write,
        observation_id=ctx_download.observation_id,
    ),
    mola_configs.LAYOUT.instrument: Instrument(
        mola_configs.LAYOUT,
        mola_download.fetch,
        mola_read.read,
        mola_place.place,
        mola_crop.crop,
        mola_write.write,
    ),
    sharad_configs.LAYOUT.instrument: Instrument(
        sharad_configs.LAYOUT,
        sharad_download.fetch,
        sharad_read.read,
        sharad_place.place,
        sharad_crop.crop,
        sharad_write.write,
        observation_id=sharad_download.observation_id,
        altitude=altitude.altitude_m,
    ),
}
