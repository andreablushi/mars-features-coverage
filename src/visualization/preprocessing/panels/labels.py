"""What the label says about the observation, before anything is drawn."""

from __future__ import annotations

import ipywidgets as widgets

from metadata.api.client import ODEClient
from preprocessing.crism import reading
from visualization.common import panels, tables
from visualization.preprocessing import fetching
from visualization.preprocessing.picker import Cleaned

NO_STRIP = "Pick an observation above and press Clean to fill this in."

_HEADINGS = ("What", "Value", "Why it matters")

# What every multispectral survey observation has to agree on, since the band
# table and the dead column list are hardcoded against them, and what a
# disagreement in each would mean.
_MUST_AGREE = (
    ("SAMPLING_MODE_ID", "A mode other than MULTISPEC is not what this cleans"),
    ("LINE_SAMPLES", "A different width would move the dead columns"),
    ("BANDS", "A different count would break the band table outright"),
    (
        "MRO:WAVELENGTH_FILE_NAME",
        "Versions differ harmlessly: the two in circulation hold identical "
        "centres and identical live columns, compared band by band",
    ),
    ("MRO:HDF_SOFTWARE_NAME", "N/A throughout is why the despiking is needed"),
)

_ACROSS_HEADINGS = ("Field", "Values seen", "Same", "What a difference would mean")

# The label keys worth reading, with what each one tells you.
_FIELDS = (
    ("SAMPLING_MODE_ID", "MULTISPEC is the survey mode this is written for"),
    ("PIXEL_AVERAGING_WIDTH", "10 means each pixel is about 180 m across"),
    ("MRO:SENSOR_ID", "L is the infrared detector, S the visible one"),
    ("BAND_STORAGE_TYPE", "How the cube is laid out on disk"),
    ("UNIT", "I_OVER_F is reflectance, so values belong in [0, 1]"),
    ("MRO:WAVELENGTH_FILE_NAME", "The table the band centres come from"),
    ("MRO:ATMO_CORRECTION_FLAG", "OFF, so the CO2 band is still in the spectra"),
    ("MRO:PHOTOCLIN_CORRECTION_FLAG", "OFF, so the sun angle is still in them"),
    ("MRO:THERMAL_CORRECTION_MODE", "OFF, so the long bands still carry heat"),
)

_FILTER_KEY = "MRO:HDF_SOFTWARE_NAME"
_FILTER_WHY = (
    "N/A means no spike filter ran upstream, unlike a hyperspectral product, "
    "so the despiking here is not repeating work"
)


def plot(chosen: Cleaned | None) -> widgets.Widget:
    """Tabulate the label fields worth checking before trusting the cleaning.

    Args:
        chosen: The cleaned observation, or None while none is picked.

    Returns:
        The table, or the grey panel when nothing is loaded.
    """
    if chosen is None:
        return panels.unavailable(NO_STRIP)

    strip = chosen.strip
    lines, samples, bands = strip.cube.shape
    rows = [
        ("Product", strip.product_id, "The observation these numbers describe"),
        (
            "Shape",
            f"{lines} lines, {samples} samples, {bands} bands",
            "Bands are what is left after the uncalibrated one is dropped",
        ),
        (
            "Usable columns",
            f"{int(strip.columns.sum())} of {samples}",
            "The rest carry no wavelength, so nothing can be read from them",
        ),
        (
            "Usable bands",
            f"{int(strip.bands.sum())} of {bands}",
            "The rest sit in the opaque window or above the thermal cut",
        ),
        (
            "Band spacing",
            f"{strip.spacing_nm:.1f} nm",
            "Filter widths given in nanometres are converted against this",
        ),
    ]
    rows += [(key, strip.label.get(key, "absent"), why) for key, why in _FIELDS]
    rows.append((_FILTER_KEY, strip.label.get(_FILTER_KEY, "absent"), _FILTER_WHY))
    return tables.written("What the label says", _HEADINGS, rows)


def across(count: int = 6, seed: int | None = 0) -> widgets.Widget:
    """Check that other observations agree with the ones this stage assumes.

    The band table and the dead column list are hardcoded, so they only hold
    while every multispectral survey observation is shaped the same way. Only
    labels are fetched here, a few kilobytes each, so this costs nothing next
    to cleaning a second image.

    Args:
        count: How many observations to compare.
        seed: Fixes the draw so a run can be repeated, or None to vary it.

    Returns:
        A table of the fields that have to agree, and whether they do.
    """
    seen: dict[str, set[str]] = {key: set() for key, _ in _MUST_AGREE}
    with ODEClient() as client:
        for product in fetching.sample(count, seed):
            try:
                label = reading.read_label(fetching.fetch_label(product, client=client))
            except (OSError, ValueError):
                continue
            for key, _ in _MUST_AGREE:
                seen[key].add(label.get(key, "absent"))

    rows = [
        (
            key,
            ", ".join(sorted(seen[key])) or "none read",
            "yes" if len(seen[key]) == 1 else "no",
            why,
        )
        for key, why in _MUST_AGREE
    ]
    return tables.written(f"What {count} observations agree on", _ACROSS_HEADINGS, rows)
