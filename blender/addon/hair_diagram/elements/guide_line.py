"""Guide lines: free straight or curved lines that are not surface partings.

Where a section line is projected onto the head, a guide line is drawn through
open space -- a hair strand held out at an elevation, a projected perimeter, a
construction line. Same curve representation, different collection and colour,
so the two can be toggled independently in a diagram.
"""

from __future__ import annotations

import bpy
from mathutils import Vector

from .. import config
from ..core import materials
from . import base

KIND = "GUIDE"
COLLECTION = "GUIDE_LINES"


def create(
    points,
    radius: float = config.LINE_RADIUS_GUIDE,
    material: bpy.types.Material | None = None,
    name: str | None = None,
    qualifier: str | None = None,
    smooth: bool = False,
    cyclic: bool = False,
    dash=config.DASH_SOLID,
) -> bpy.types.Object:
    """A guide line through explicit world-space points.

    Pass ``dash=config.DASH_GUIDE`` for the dashed style that marks a projected
    or reference line rather than a real boundary.
    """
    points = [Vector(p) for p in points]
    return base.polyline(
        points,
        kind=KIND,
        collection_key=COLLECTION,
        material=material or materials.guide(),
        radius=radius,
        name=name,
        qualifier=qualifier,
        cyclic=cyclic,
        smooth=smooth,
        dash=dash,
        params={"points": points, "radius": radius},
    )


def create_segment(start, end, **kwargs) -> bpy.types.Object:
    """The common two-point case."""
    return create([start, end], **kwargs)
