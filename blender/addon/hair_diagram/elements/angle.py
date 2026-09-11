"""Angle indicators: two legs, an arc between them, and a numeric label.

Cutting diagrams live on 0 / 45 / 90 / 135 / 180 degrees of elevation, so this
is the shape that will be reused most. Only the indicator itself is built here;
the haircutting semantics (what is being elevated from where) belong to the
CUTTING domain and are out of scope.

The parts are parented to an empty so an angle behaves as one object.
"""

from __future__ import annotations

import math

import bpy
from mathutils import Matrix, Vector

from .. import config
from ..core import collections, materials, naming
from ..core.errors import HairDiagramError
from . import base, label as label_module

KIND = "ANGLE"
COLLECTION = "ANGLES"


def create(
    vertex,
    direction_a,
    direction_b,
    leg_length: float = 0.09,
    arc_radius: float = 0.045,
    arc_samples: int = 32,
    radius: float = config.LINE_RADIUS_ANGLE,
    show_label: bool = True,
    label_text: str | None = None,
    label_size: float = config.LABEL_SIZE,
    material: bpy.types.Material | None = None,
    name: str | None = None,
    qualifier: str | None = None,
) -> bpy.types.Object:
    """Draw the angle between two directions meeting at ``vertex``.

    Returns the empty that groups the legs, the arc and the label. The measured
    value is stored on it as ``obj["hd_degrees"]``, so downstream code never has
    to re-derive it from geometry.
    """
    vertex = Vector(vertex)
    a = Vector(direction_a).normalized()
    b = Vector(direction_b).normalized()
    if a.length_squared == 0.0 or b.length_squared == 0.0:
        raise HairDiagramError("Angle legs must be non-zero directions.")

    degrees = math.degrees(a.angle(b))
    material = material or materials.angle()

    root = bpy.data.objects.new(name or naming.indexed_name(KIND, qualifier), None)
    root.empty_display_type = "PLAIN_AXES"
    root.empty_display_size = 0.02
    root.matrix_world = Matrix.Translation(vertex)
    collections.link(root, COLLECTION)
    base.tag(root, KIND, {
        "vertex": vertex,
        "direction_a": a,
        "direction_b": b,
        "degrees": degrees,
        "leg_length": leg_length,
        "arc_radius": arc_radius,
    })
    root["hd_degrees"] = degrees

    for suffix, direction in (("A", a), ("B", b)):
        leg = base.polyline(
            [vertex, vertex + direction * leg_length],
            kind=KIND,
            collection_key=COLLECTION,
            material=material,
            radius=radius,
            name=f"{root.name}_LEG_{suffix}",
            smooth=False,
            params={"leg": suffix},
        )
        base.parent_to(leg, root)

    arc_points = _arc(vertex, a, b, arc_radius, arc_samples)
    arc = base.polyline(
        arc_points,
        kind=KIND,
        collection_key=COLLECTION,
        material=material,
        radius=radius,
        name=f"{root.name}_ARC",
        params={"arc_radius": arc_radius},
    )
    base.parent_to(arc, root)

    if show_label:
        bisector = (a + b)
        if bisector.length_squared < 1e-9:      # a straight 180 degree angle
            bisector = a.cross(Vector((0.0, 0.0, 1.0)))
            if bisector.length_squared < 1e-9:
                bisector = a.cross(Vector((1.0, 0.0, 0.0)))
        bisector.normalize()
        text = label_text if label_text is not None else _format(degrees)
        tag = label_module.create(
            text,
            vertex + bisector * (arc_radius * 1.35),
            size=label_size,
            material=material,
            name=f"{root.name}_LABEL",
            collection_key=COLLECTION,
        )
        # Re-tagged as part of the angle: a sub-label belongs to its parent
        # element, so queries for standalone labels do not pick it up.
        base.tag(tag, KIND, {"role": "label", "degrees": degrees})
        base.parent_to(tag, root)

    return root


def create_elevation(
    vertex,
    reference_direction,
    degrees: float,
    plane_normal,
    **kwargs,
) -> bpy.types.Object:
    """An angle of ``degrees`` opened from a reference direction.

    This is the form cutting diagrams want: "90 degrees up from the head
    surface", rather than two directions the caller has to compute.

    ``plane_normal`` names the plane the elevation opens in. It is
    orthogonalised against the reference first: rotating about a raw axis that
    is not perpendicular to the reference sweeps a cone, and the angle between
    the two legs then comes out smaller than the number asked for -- a 90
    degree elevation off a slanted surface normal would measure 78 degrees.
    """
    from ..core import surface

    reference = Vector(reference_direction).normalized()
    axis = Vector(plane_normal).normalized()
    axis = axis - reference * axis.dot(reference)
    if axis.length < 1e-6:
        raise HairDiagramError(
            "plane_normal is parallel to reference_direction, so it does not "
            "define a plane to open the angle in. Pick an axis across it."
        )
    rotated = surface.rotate_axis(reference, degrees, axis.normalized())
    kwargs.setdefault("label_text", _format(degrees))
    return create(vertex, reference, rotated, **kwargs)


def _arc(vertex: Vector, a: Vector, b: Vector, radius: float, samples: int):
    """Points along the shorter arc from ``a`` to ``b``, centred on ``vertex``."""
    total = a.angle(b)
    axis = a.cross(b)
    if axis.length_squared < 1e-12:            # parallel or anti-parallel legs
        axis = a.cross(Vector((0.0, 0.0, 1.0)))
        if axis.length_squared < 1e-12:
            axis = a.cross(Vector((1.0, 0.0, 0.0)))
    axis.normalize()

    from mathutils import Matrix

    samples = max(3, samples)
    return [
        vertex + (Matrix.Rotation(total * i / (samples - 1), 3, axis) @ a) * radius
        for i in range(samples)
    ]


def _format(degrees: float) -> str:
    value = round(float(degrees), 1)
    text = str(int(value)) if float(value).is_integer() else str(value)
    return f"{text}{label_module.DEGREE}"
