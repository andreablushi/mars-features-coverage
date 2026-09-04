"""What a SHARAD radargram is published as, and where it lands."""

from __future__ import annotations

import re

from building.common.naming import Naming
from building.common.product_cache import ProductCache
from building.metadata.models import observation as observation_axes
from utils.disk import paths

# The two products one track is published as.
OBSERVATION = "observation"
GEOMETRY = "geometry"
KINDS = (OBSERVATION, GEOMETRY)

# How ODE spells one product of a track, which writes its kind after the track
# the observation on its own ends at.
NAMING = Naming(
    re.compile(r"^(?P<track>s_\d+)(?:_(?P<marker>rgram|geom))?$"),
    identity="{track}",
    marks=("marker",),
    template="{track}_{marker}",
    fields={OBSERVATION: {"marker": "rgram"}, GEOMETRY: {"marker": "geom"}},
)

# What each axis of the radargram is called.
DIMS = ("delay", "trace")

# What each axis of it holds, in the order it is stored. A sounder walks a line
# rather than sweeping ground, so only one axis is placed.
AXES = (observation_axes.DELAY, observation_axes.GROUND)

# Which geometry field places a trace.
PLACEMENT = {"latitude": "LATITUDE", "longitude": "LONGITUDE"}

# Which fields the spacecraft's height above the ground is read between, in km,
# since that is what the delay axis is turned into a depth through.
RADII = {"ground": "MARS RADIUS", "spacecraft": "SPACECRAFT RADIUS"}

# Where each product of an observation is kept. The geometry is a table rather
# than an image, and sits in a subdirectory of its own.
CACHE = ProductCache(
    paths.SHARAD_ROOT,
    {OBSERVATION: (".lbl", ".img"), GEOMETRY: (".lbl", ".tab")},
    {GEOMETRY: "geom"},
)
