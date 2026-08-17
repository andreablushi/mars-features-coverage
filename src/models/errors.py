"""The errors the pipeline raises."""

from __future__ import annotations


class ODEError(RuntimeError):
    """Raised when ODE reports an error or a query keeps failing."""
