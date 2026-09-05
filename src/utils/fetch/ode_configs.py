"""What ODE is asked at, what every query carries, and what it raises."""

from __future__ import annotations

ODE_BASE_URL = "https://oderest.rsl.wustl.edu/live2/"
ODE_TARGET = "mars"

# What every query asks ODE to answer with.
OUTPUT = {"output": "JSON"}

# A feature running through every longitude is asked for in two halves.
LONGITUDE_HALVES = ((0.0, 180.0), (180.0, 360.0))


class ODEError(RuntimeError):
    """Raised when ODE reports an error or a query keeps failing."""
