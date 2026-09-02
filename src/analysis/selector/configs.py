"""Central configuration for the best time window search."""

from __future__ import annotations

# How many days of waiting one more percentage point of ground is worth.
DAYS_PER_PERCENT = 10.0

# The cells an observation has to reach that no other observation of its own set
# already does, or the window is trimmed of it. At one only a full repeat is
# dropped, and every higher value drops a look that does add ground.
GAIN = 1

# Seconds in a day, which is what every span is measured in.
DAY_SECONDS = 86400.0
