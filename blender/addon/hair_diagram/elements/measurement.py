"""Measurements: a dimension line with end ticks and a value label.

Reads as ``5 cm``, ``8 cm``, ``13 cm REF``. The value defaults to the true
world-space distance between the two points, converted to the unit asked for,
so a diagram cannot silently disagree with its own geometry. Passing ``value``
explicitly overrides that, which is what a schematic (not-to-scale) diagram
needs.
"""

from __future__ import annotations

import bpy
from mathutils import Matrix, Vector

from .. import config
from ..core import collections, materials, naming
from . import base, label as label_module

KIND = "MEASURE"
COLLECTION = "MEASUREMENTS"

# Multiplier from Blender units (metres) to the displayed unit.
UNIT_SCALE = {"cm": 100.0, "mm": 1000.0, "m": 1.0, "in": 39.3701}


def create(
    start,
    end,
    value: float | None = None,
    unit: str = "cm",
    suffix: str = "",
    decimals: int = 0,
    tick_size: float = 0.008,
    radius: float = config.LINE_RADIUS_MEASURE,
    show_label: bool = True,
    label_size: float = config.LABEL_SIZE,
    label_offset=None,
    material: bpy.types.Material | None = None,
    name: str | None = None,
    qualifier: str | None = None,
) -> bpy.types.Object:
    """A dimension between two world-space points.

    Returns the grouping empty. The numeric value is stored on it as
    ``obj["hd_value"]`` together with ``obj["hd_unit"]``.
    """
    start = Vector(start)
    end = Vector(end)
    axis = end - start
    length = axis.length
    material = material or materials.measurement()

    if value is None:
        value = length * UNIT_SCALE.get(unit, 1.0)

    root = bpy.data.objects.new(name or naming.indexed_name(KIND, qualifier), None)
    root.empty_display_type = "PLAIN_AXES"
    root.empty_display_size = 0.02
    root.matrix_world = Matrix.Translation(start)
    collections.link(root, COLLECTION)
    base.tag(root, KIND, {
        "start": start,
        "end": end,
        "value": float(value),
        "unit": unit,
        "suffix": suffix,
    })
    root["hd_value"] = float(value)
    root["hd_unit"] = unit

    line = base.polyline(
        [start, end],
        kind=KIND,
        collection_key=COLLECTION,
        material=material,
        radius=radius,
        name=f"{root.name}_LINE",
        smooth=False,
        params={"length_m": length},
    )
    _parent(line, root)

    tick_axis = _tick_axis(axis)
    for suffix_name, point in (("A", start), ("B", end)):
        tick = base.polyline(
            [point - tick_axis * tick_size, point + tick_axis * tick_size],
            kind=KIND,
            collection_key=COLLECTION,
            material=material,
            radius=radius,
            name=f"{root.name}_TICK_{suffix_name}",
            smooth=False,
            params={"tick": suffix_name},
        )
        _parent(tick, root)

    if show_label:
        text = format_value(value, unit, decimals, suffix)
        offset = Vector(label_offset) if label_offset is not None else tick_axis * (tick_size * 3.0)
        tag = label_module.create(
            text,
            (start + end) * 0.5 + offset,
            size=label_size,
            material=material,
            name=f"{root.name}_LABEL",
            collection_key=COLLECTION,
        )
        # Part of the measurement, not a standalone label -- see angle.py.
        base.tag(tag, KIND, {"role": "label", "text": text})
        _parent(tag, root)

    return root


def format_value(value: float, unit: str = "cm", decimals: int = 0, suffix: str = "") -> str:
    """``13.0, "cm", 0, "REF"`` -> ``"13 cm REF"``."""
    number = f"{float(value):.{decimals}f}"
    text = f"{number} {unit}".strip()
    return f"{text} {suffix}".strip() if suffix else text


def _tick_axis(axis: Vector) -> Vector:
    """A direction perpendicular to the dimension, biased towards world up."""
    up = Vector((0.0, 0.0, 1.0))
    if abs(axis.normalized().dot(up)) > 0.98:
        up = Vector((0.0, -1.0, 0.0))
    perpendicular = axis.cross(up)
    if perpendicular.length_squared < 1e-12:
        perpendicular = Vector((1.0, 0.0, 0.0))
    return perpendicular.normalized()


def _parent(child: bpy.types.Object, root: bpy.types.Object) -> None:
    base.parent_to(child, root)
