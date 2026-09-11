"""Translucent highlight areas on the head surface.

The shape colouring diagrams will need: a panel, slice or placement zone tinted
over the mannequin. It reuses the section-line ray casting, sampling a
rectangle in (azimuth, elevation) space instead of a single arc, so a highlight
lands on the surface for the same reasons a section line does.

Scope note: this is the *primitive*. Named coloring shapes (weave, foil,
balayage placement) belong to the COLORING domain and are not implemented.
"""

from __future__ import annotations

import bmesh
import bpy

from .. import config
from ..core import materials, surface
from ..core.errors import SurfaceProjectionError
from . import base

KIND = "HIGHLIGHT"
COLLECTION = "HIGHLIGHTS"


def create(
    azimuth_range=(-30.0, 30.0),
    elevation_range=(10.0, 60.0),
    steps_u: int = 16,
    steps_v: int = 12,
    offset: float = config.SURFACE_OFFSET * 2.5,
    target: bpy.types.Object | None = None,
    material: bpy.types.Material | None = None,
    name: str | None = None,
    qualifier: str | None = None,
) -> bpy.types.Object:
    """A translucent patch covering a rectangle of the head's angular domain.

    ``azimuth_range`` follows the camera convention (0 is the face, 90 the
    model's left); ``elevation_range`` is degrees above the horizontal, 90
    being the apex.
    """
    steps_u = max(2, steps_u)
    steps_v = max(2, steps_v)
    a0, a1 = float(azimuth_range[0]), float(azimuth_range[1])
    e0, e1 = float(elevation_range[0]), float(elevation_range[1])

    grid = []
    for iv in range(steps_v):
        elevation = e0 + (e1 - e0) * iv / (steps_v - 1)
        row = []
        for iu in range(steps_u):
            azimuth = a0 + (a1 - a0) * iu / (steps_u - 1)
            location, _normal = surface.project(
                surface.spherical_direction(azimuth, elevation),
                target=target,
                offset=offset,
                strict=False,
            )
            if location is None:
                raise SurfaceProjectionError(
                    f"Highlight sample at azimuth {azimuth:.1f}, elevation "
                    f"{elevation:.1f} missed the head surface."
                )
            row.append(location)
        grid.append(row)

    mesh = bmesh.new()
    verts = [[mesh.verts.new(point) for point in row] for row in grid]
    for iv in range(steps_v - 1):
        for iu in range(steps_u - 1):
            mesh.faces.new((
                verts[iv][iu],
                verts[iv][iu + 1],
                verts[iv + 1][iu + 1],
                verts[iv + 1][iu],
            ))
    bmesh.ops.recalc_face_normals(mesh, faces=mesh.faces)

    return base.mesh_object(
        mesh,
        kind=KIND,
        collection_key=COLLECTION,
        material=material or materials.highlight(),
        name=name,
        qualifier=qualifier,
        params={
            "azimuth_range": [a0, a1],
            "elevation_range": [e0, e1],
            "steps_u": steps_u,
            "steps_v": steps_v,
            "offset": offset,
        },
    )
