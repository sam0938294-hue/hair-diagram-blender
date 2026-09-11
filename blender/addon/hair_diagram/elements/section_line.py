"""Section lines: technical partings drawn on the head surface.

A section is defined by a *plane* through the head plus an angular sweep inside
that plane. Every classical parting falls out of those parameters:

===================  ===========================================================
centre line          plane_normal = LEFT,  0 -> 180 deg  (over the top)
horizontal section   plane_normal = UP,    full sweep at a given height
radial section       plane_normal rotated about UP by the radial angle
vertical section      plane_normal = FRONT, full or partial sweep
===================  ===========================================================

Only the generic generator is implemented. Building the named library on top of
it belongs to the CUTTING / COLORING / PERM domains, which are out of scope for
this milestone -- but they need no new machinery, only argument presets.
"""

from __future__ import annotations

import bpy
from mathutils import Vector

from .. import config
from ..core import materials, surface
from . import base

KIND = "SECTION"
COLLECTION = "SECTION_LINES"


def create(
    plane_normal=None,
    start_deg: float = 0.0,
    end_deg: float = 180.0,
    samples: int = 96,
    offset: float = config.SURFACE_OFFSET,
    radius: float = config.LINE_RADIUS_SECTION,
    origin=None,
    target: bpy.types.Object | None = None,
    material: bpy.types.Material | None = None,
    name: str | None = None,
    qualifier: str | None = None,
    cyclic: bool = False,
    dash=config.DASH_SOLID,
) -> bpy.types.Object:
    """Draw one section line lying on the head surface.

    Parameters
    ----------
    plane_normal:
        Normal of the plane the section sweeps in. Defaults to the sagittal
        plane, which gives the centre line.
    start_deg, end_deg:
        Sweep range measured from the plane's reference axis (see
        :func:`..core.surface.plane_basis`). For the default sagittal plane,
        0 deg is the apex, 90 deg the face, -90 deg the occiput.
    offset:
        How far the line floats above the surface, in metres.
    origin:
        Point the rays radiate from. Defaults to the head centre; moving it is
        how off-centre partings are produced later.
    dash:
        ``(on, off)`` lengths in metres, or None for a solid line. See
        ``config.DASH_GUIDE``.
    """
    plane_normal = Vector(plane_normal) if plane_normal is not None else Vector((1.0, 0.0, 0.0))
    directions = surface.arc_directions(plane_normal, start_deg, end_deg, samples)
    points, _normals = surface.project_many(
        directions, target=target, offset=offset, origin=origin
    )

    return base.polyline(
        points,
        kind=KIND,
        collection_key=COLLECTION,
        material=material or materials.section(),
        radius=radius,
        name=name,
        qualifier=qualifier,
        cyclic=cyclic,
        dash=dash,
        params={
            "plane_normal": plane_normal,
            "start_deg": start_deg,
            "end_deg": end_deg,
            "samples": samples,
            "offset": offset,
            "radius": radius,
            "origin": Vector(origin) if origin is not None else None,
        },
    )


def create_from_points(
    points,
    radius: float = config.LINE_RADIUS_SECTION,
    material: bpy.types.Material | None = None,
    name: str | None = None,
    qualifier: str | None = None,
    cyclic: bool = False,
    dash=config.DASH_SOLID,
) -> bpy.types.Object:
    """A section line from explicit world-space points.

    The escape hatch for shapes the plane sweep cannot express, such as a
    hairline traced from a reference photo.
    """
    return base.polyline(
        points,
        kind=KIND,
        collection_key=COLLECTION,
        material=material or materials.section(),
        radius=radius,
        name=name,
        qualifier=qualifier,
        cyclic=cyclic,
        dash=dash,
        params={"explicit_points": len(list(points)), "radius": radius},
    )
