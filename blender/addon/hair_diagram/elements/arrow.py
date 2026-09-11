"""Direction arrows.

One mesh object: a cylindrical shaft capped with a cone. Built as geometry
rather than as a bevelled curve because the head needs a different profile from
the shaft, and because a single mesh keeps the arrow rigid when it is scaled or
re-oriented.

Defined by a start and an end point in world space; the ``origin + direction +
length`` form is a thin wrapper over that.
"""

from __future__ import annotations

import bmesh
import bpy
from mathutils import Matrix, Vector

from .. import config
from ..core import materials
from ..core.errors import HairDiagramError
from . import base

KIND = "ARROW"
COLLECTION = "ARROWS"


def create(
    start,
    end,
    shaft_radius: float = config.ARROW_SHAFT_RADIUS,
    head_length: float = config.ARROW_HEAD_LENGTH,
    head_radius: float = config.ARROW_HEAD_RADIUS,
    segments: int = config.ARROW_SEGMENTS,
    material: bpy.types.Material | None = None,
    name: str | None = None,
    qualifier: str | None = None,
) -> bpy.types.Object:
    """An arrow pointing from ``start`` to ``end``.

    The arrowhead is clamped so it can never be longer than the arrow itself,
    which keeps very short arrows readable instead of degenerate.
    """
    start = Vector(start)
    end = Vector(end)
    direction = end - start
    total = direction.length
    if total <= 1e-6:
        raise HairDiagramError("An arrow needs a non-zero length.")

    head_length = min(head_length, total * 0.6)
    shaft_length = total - head_length

    mesh = bmesh.new()
    # Shaft: from the origin up +Z, then the arrow is rotated into place.
    bmesh.ops.create_cone(
        mesh,
        cap_ends=True,
        cap_tris=False,
        segments=segments,
        radius1=shaft_radius,
        radius2=shaft_radius,
        depth=shaft_length,
        matrix=Matrix.Translation((0.0, 0.0, shaft_length * 0.5)),
    )
    # Head: a cone from the end of the shaft to the tip.
    bmesh.ops.create_cone(
        mesh,
        cap_ends=True,
        cap_tris=False,
        segments=segments,
        radius1=head_radius,
        radius2=0.0,
        depth=head_length,
        matrix=Matrix.Translation((0.0, 0.0, shaft_length + head_length * 0.5)),
    )
    bmesh.ops.recalc_face_normals(mesh, faces=mesh.faces)

    obj = base.mesh_object(
        mesh,
        kind=KIND,
        collection_key=COLLECTION,
        material=material or materials.arrow(),
        name=name,
        qualifier=qualifier,
        smooth=False,
        params={
            "start": start,
            "end": end,
            "shaft_radius": shaft_radius,
            "head_length": head_length,
            "head_radius": head_radius,
        },
    )
    # Assigned as one matrix rather than as location + rotation_euler: that
    # keeps matrix_world correct straight away, so a caller can anchor a label
    # to the arrow's tip in the same tick it was created.
    obj.matrix_world = (
        Matrix.Translation(start) @ direction.to_track_quat("Z", "Y").to_matrix().to_4x4()
    )
    return obj


def create_from_direction(origin, direction, length: float, **kwargs) -> bpy.types.Object:
    """``origin`` plus a direction and a length, for when there is no end point."""
    direction = Vector(direction).normalized()
    return create(origin, Vector(origin) + direction * length, **kwargs)
