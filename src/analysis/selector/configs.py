"""The thresholds the best time window search itself turns on."""

from __future__ import annotations

# The cells an observation has to reach that no other observation of its own set
# already does, or the window is trimmed of it. At one only a full repeat is
# dropped, and every higher value drops a look that does add ground.
GAIN = 1

# Seconds in a day, which is what every span is measured in.
DAY_SECONDS = 86400.0
