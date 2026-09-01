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


# How many bands wide the moving median that smooths a column's spectrum is.
# Three is crism_ml's value and the smallest a median can be.
STRIPE_SIZE = 3

# How many standard deviations above its own column's mean a band has to sit to
# be read as a spike, one threshold per detector. crism_ml uses 5 over 248
# hyperspectral bands. A survey scan carries far fewer, and over n bands no
# score can exceed (n-1)/sqrt(n): 6.48 for L at 44 bands, 7.28 at 55, 4.01 for
# S at 18 and 4.69 at 24. Each is set above the highest a real absorption was
# measured to reach on that detector, 7.07 on L and 4.59 on S.
STRIPE_SIGMA = {"l": 7.5, "s": 4.7}
