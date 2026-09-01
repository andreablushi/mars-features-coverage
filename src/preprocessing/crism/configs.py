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


# How wide in nm the moving median that smooths a column's spectrum reaches.
# crism_ml counts this in channels, which means a different width on every
# downlink configuration: its three channels are 20 nm hyperspectral but 112 nm
# on a coarse survey scan and 89 nm on a fine one. Fixing the width instead
# keeps one physical meaning, and at every configuration flown it still works
# out to the three bands crism_ml uses.
STRIPE_WIDTH = 80.0

# How many standard deviations above its own column's mean a band has to sit to
# be read as a spike, one threshold per detector. crism_ml uses 5 over 248
# hyperspectral bands. A survey scan carries far fewer, and over n bands no
# score can exceed (n-1)/sqrt(n): 6.48 for L at 44 bands, 7.28 at 55, 4.01 for
# S at 18 and 4.69 at 24. Each is set above the highest a real absorption was
# measured to reach on that detector, 7.07 on L and 4.59 on S.
STRIPE_SIGMA = {"l": 7.5, "s": 4.7}

# Where the Martian atmosphere absorbs inside each detector's window, in nm.
# Only the 2.0 um CO2 band is strong enough to be worth the loss: it is the one
# the volcano scan correction exists for. The weak CO2 band near 1435 nm and the
# CO band near 2350 nm are left in place, because they sit on top of the OH and
# carbonate features that the surface is being modelled for. The visible
# detector's window carries no absorption worth dropping.
ATMOSPHERIC = {"l": ((1940.0, 2090.0),), "s": ()}

# The windows crism_ml despikes the ratioed spectra with, its 11, 7 and 3
# channels written as the nm they cover at hyperspectral sampling. Survey bands
# are wide enough that all three come out as three bands, so the passes narrow
# nothing and simply repeat.
#
# The deviation is 20 rather than crism_ml's 5. At 5 a one band absorption is
# indistinguishable from a spike to a three band median: it flags 35 per cent of
# pixels at 1430 nm against 0.03 per cent at the bands either side, and keeps
# only 16 per cent of the pixel to pixel variation in that absorption. At 20 the
# same scan keeps 99.7 per cent of it and the step still reaches the extremes,
# which run past 100 deviations.
SPIKE_PASSES = ((72.0, 20.0), (46.0, 20.0), (20.0, 20.0))
