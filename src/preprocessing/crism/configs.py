"""Central configuration for cleaning a CRISM multispectral survey observation."""

from __future__ import annotations

# What a CRISM product writes where it holds no measurement.
FILL = 65535.0

# The bounds I/F can physically take, which a hyperspectral TRDR label records
# for itself as MRO:IF_MIN_VALUE and MRO:IF_MAX_VALUE. crism_ml instead rejects
# only values above 1e3, which lets every negative through.
IF_MIN = 0.0
IF_MAX = 1.0

# Detector columns the MSP wavelength table leaves uncalibrated, so 60 of the
# 64 carry data. Their spectra still read as ordinary numbers, so no bad value
# test finds them.
DEAD_COLUMNS = (0, 1, 2, 63)

# Bands the MSP wavelength table leaves uncalibrated, in the order the file
# stores them. Band 0 is the nominally UV channel kept only for calibration.
DEAD_BANDS = (0,)

# Where the atmosphere is opaque enough that no channel reads the ground.
OPAQUE_NM = (2650.0, 2820.0)

# Above this the surface glows and I/F stops meaning reflectance.
THERMAL_NM = 3900.0

# Band centres of the MSP IR channels that carry a wavelength, in nanometres
# and ascending, taken from the mode's own wavelength table. crism_ml hardcodes
# the equivalent hyperspectral table as BANDS, and its copy is one channel out.
WAVELENGTHS_NM = (
    1022.75, 1048.96, 1081.73, 1153.86, 1212.90, 1252.27,
    1258.84, 1265.40, 1278.53, 1331.06, 1370.47, 1396.75,
    1429.61, 1469.05, 1501.93, 1508.50, 1561.12, 1626.93,
    1659.84, 1692.77, 1752.05, 1811.35, 1877.28, 1930.05,
    1976.24, 1982.84, 2009.24, 2068.66, 2121.50, 2141.32,
    2167.76, 2207.42, 2233.86, 2253.70, 2293.39, 2319.85,
    2333.08, 2352.94, 2392.65, 2432.38, 2458.87, 2531.57,
    2604.08, 2630.46, 2703.01, 3000.34, 3126.18, 3252.22,
    3325.28, 3398.40, 3504.89, 3638.19, 3758.32, 3925.39,
)  # fmt: skip

# Spike removal passes as (window width in nanometres, sigma), widest first.
# crism_ml gives these as channel counts of 11, 7 and 3, which span 72, 46 and
# 20 nm at its 6.55 nm sampling but 398, 253 and 108 nm at the 36 nm sampling
# of MSP, wide enough to swallow a real absorption band.
SPIKE_PASSES_NM = ((72.0, 5.0), (46.0, 5.0), (20.0, 5.0))

# The window and sigma for despiking on per-column statistics, crism_ml's
# size 3 and sigma 5 carried over in nanometres.
COLUMN_WINDOW_NM = 20.0
COLUMN_SIGMA = 5.0

# The narrowest a converted window may be, since a median over fewer than
# three channels cannot reject anything.
MIN_WINDOW_CHANNELS = 3

# Bands whose medians make the false colour red, green and blue, in nanometres.
# crism_ml reads channels 233, 103 and 20 of its own table, which are these.
FALSE_COLOUR_NM = (2555.91, 1697.41, 1152.06)

# How wide the median behind each false colour channel is, in nanometres.
# crism_ml uses 17 channels, which is 111 nm at its sampling.
FALSE_COLOUR_WINDOW_NM = 111.0
