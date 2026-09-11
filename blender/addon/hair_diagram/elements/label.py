"""Text labels: ``G1``, ``SP``, ``5 cm``, ``90``.

Labels are Blender text objects using the bundled font only -- no external
typeface is downloaded, which keeps the output safe for commercial publishing
(DECISIONS.md D010).

By default a label billboards: a Copy Rotation constraint aimed at the scene
camera makes the text face the viewer exactly. Because the constraint is
re-targeted by :func:`..view.cameras.set_active`, one label stays readable
across all ten technical cameras without being rebuilt.
"""

from __future__ import annotations

import bpy
from mathutils import Vector

from .. import config
from ..core import collections, materials, naming
from . import base

KIND = "LABEL"
COLLECTION = "LABELS"
BILLBOARD_CONSTRAINT = "HD_BILLBOARD"

# The bundled font covers this, and it saves every call site from worrying
# about how to type it.
DEGREE = "°"


def create(
    text: str,
    location,
    size: float = config.LABEL_SIZE,
    offset=None,
    billboard: bool = True,
    material: bpy.types.Material | None = None,
    align_x: str = "CENTER",
    align_y: str = "CENTER",
    name: str | None = None,
    qualifier: str | None = None,
    collection_key: str = COLLECTION,
) -> bpy.types.Object:
    """Place a text label in the scene.

    ``offset`` is added to ``location``; use it to lift a label clear of the
    geometry it annotates without recomputing the anchor point.
    """
    location = Vector(location)
    if offset is not None:
        location = location + Vector(offset)

    obj_name = name or naming.indexed_name(KIND, qualifier)
    curve = bpy.data.curves.new(obj_name, type="FONT")
    curve.body = str(text)
    curve.size = size
    curve.align_x = align_x
    curve.align_y = align_y
    curve.extrude = 0.0
    curve.offset = 0.0

    obj = bpy.data.objects.new(obj_name, curve)
    collections.link(obj, collection_key)
    curve.materials.append(material or materials.label())
    obj.location = location
    base.tag(obj, KIND, {"text": str(text), "size": size, "billboard": billboard})

    if billboard:
        set_billboard(obj, True)
    return obj


def angle_label(degrees, location, **kwargs) -> bpy.types.Object:
    """``90`` -> a label reading ``90 deg`` with the degree sign."""
    value = int(degrees) if float(degrees).is_integer() else round(float(degrees), 1)
    kwargs.setdefault("material", materials.angle())
    return create(f"{value}{DEGREE}", location, **kwargs)


def set_billboard(obj: bpy.types.Object, enabled: bool, camera=None) -> bpy.types.Object:
    """Turn camera-facing on or off for an existing label."""
    existing = obj.constraints.get(BILLBOARD_CONSTRAINT)
    if not enabled:
        if existing is not None:
            obj.constraints.remove(existing)
        obj["hd_billboard"] = False
        return obj

    constraint = existing or obj.constraints.new("COPY_ROTATION")
    constraint.name = BILLBOARD_CONSTRAINT
    constraint.target = camera or bpy.context.scene.camera
    constraint.mix_mode = "REPLACE"
    constraint.target_space = "WORLD"
    constraint.owner_space = "WORLD"
    obj["hd_billboard"] = True
    return obj
