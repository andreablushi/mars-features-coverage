"""Central configuration for cleaning a CRISM multispectral survey observation."""

from __future__ import annotations

from utils.disk import paths

# Where the metadata download stage writes what it fetched from ODE.
METADATA_ROOT = paths.METADATA_ROOT

# Where downloaded observations are kept, one directory each.
CACHE_ROOT = paths.CRISM_ROOT

# The wavelength window in nm each detector is trusted over, outside which the
# sensor edge sees almost no light and the reading is noise.
WINDOWS = {"l": (1020.0, 2650.0), "s": (400.0, 1060.0)}

# The range a brightness can take. Light returned cannot exceed light arriving,
# and cannot be negative, but a reading near zero carries noise that lands just
# below it, so the floor allows for that and refuses only the impossible.
BRIGHTNESS = (-0.05, 1.0)

# How far a column has to sit from the line through the two beside it, counted
# in multiples of the curvature its own band carries anyway, before it is read
# as one detector cell rather than as ground. Set above the 5.3 that a real
# 1430 nm absorption reaches, and below the 7 and more that a displaced column
# does.
STRIPE_SIGMA = 6.0
