"""Shared plumbing for every diagram element.

The element layer is deliberately a set of small functions rather than a class
hierarchy (DECISIONS.md D008). Every element module ends up doing the same four
things, which is exactly what lives here:

* turn a list of points into a curve (solid or dashed), or a bmesh into a
  mesh object
* give it a deterministic name
* put it in the right collection with the right material
* stamp the parameters that produced it onto the object

That last step matters most: an element carries its own recipe in
``obj["hd_params"]``, so a diagram can be inspected, diffed and regenerated
instead of being an opaque pile of vertices.
"""

from __future__ import annotations

import json

import bmesh
import bpy
from mathutils import Vector

from ..core import collections, naming


def polyline(
    points,
    kind: str,
    collection_key: str,
    material: bpy.types.Material,
    radius: float,
    name: str | None = None,
    qualifier: str | None = None,
    cyclic: bool = False,
    smooth: bool = True,
    dash=None,
    params: dict | None = None,
) -> bpy.types.Object:
    """Build a bevelled curve through ``points`` -- the standard diagram line.

    ``radius`` is the visible half-thickness in metres. Curves are used rather
    than mesh tubes so thickness stays a single editable number.

    ``dash`` is ``(on_length, off_length)`` in metres. Solid and dashed are
    load-bearing notation in a technical diagram -- a panel boundary is solid, a
    projected guide is dashed -- so a dashed line is built as real geometry:
    the polyline is cut by arc length and each drawn run becomes its own spline
    inside the same curve object. The dash therefore measures the same on the
    page whatever the line's shape, and the whole line is still one object.
    """
    points = [Vector(p) for p in points]
    if len(points) < 2:
        raise ValueError(f"A {kind} line needs at least 2 points, got {len(points)}.")

    obj_name = name or naming.indexed_name(kind, qualifier)
    curve = bpy.data.curves.new(obj_name, type="CURVE")
    curve.dimensions = "3D"
    curve.resolution_u = 12
    curve.bevel_depth = radius
    curve.bevel_resolution = 4
    curve.fill_mode = "FULL"
    curve.use_fill_caps = True

    runs = dash_runs(points, dash) if dash else [points]
    for run in runs:
        # Dashed runs are cut along the source polyline, so a POLY spline
        # reproduces them exactly; smoothing them would move the cut points.
        use_nurbs = smooth and not dash
        spline = curve.splines.new("NURBS" if use_nurbs else "POLY")
        spline.points.add(len(run) - 1)
        for spline_point, point in zip(spline.points, run):
            spline_point.co = (point.x, point.y, point.z, 1.0)
        spline.use_cyclic_u = cyclic and not dash
        if use_nurbs:
            spline.order_u = min(4, len(run))
            spline.use_endpoint_u = not cyclic
            spline.use_bezier_u = False

    obj = bpy.data.objects.new(obj_name, curve)
    collections.link(obj, collection_key)
    curve.materials.append(material)
    if dash and params is not None:
        params = dict(params, dash=list(dash))
    tag(obj, kind, params)
    return obj


def mesh_object(
    mesh: bmesh.types.BMesh,
    kind: str,
    collection_key: str,
    material: bpy.types.Material,
    name: str | None = None,
    qualifier: str | None = None,
    smooth: bool = True,
    params: dict | None = None,
) -> bpy.types.Object:
    """Turn a bmesh into a named, collected, materialised object."""
    obj_name = name or naming.indexed_name(kind, qualifier)
    data = bpy.data.meshes.new(obj_name)
    mesh.to_mesh(data)
    mesh.free()
    if smooth:
        for polygon in data.polygons:
            polygon.use_smooth = True

    obj = bpy.data.objects.new(obj_name, data)
    collections.link(obj, collection_key)
    data.materials.append(material)
    tag(obj, kind, params)
    return obj


def tag(obj: bpy.types.Object, kind: str, params: dict | None = None) -> bpy.types.Object:
    """Stamp the element kind and its creation parameters onto the object.

    Also switches shadow casting off. Annotation is drawn *on* the diagram, not
    lit within it: a section line that drops a shadow across the mannequin
    reads as a second, wrong line.
    """
    obj["hd_kind"] = kind.lower()
    obj["hd_params"] = json.dumps(_serialisable(params or {}), sort_keys=True)
    if hasattr(obj, "visible_shadow"):
        obj.visible_shadow = False
    return obj


def dash_runs(points, dash):
    """Cut a polyline into the drawn runs of a dash pattern.

    ``dash`` is ``(on_length, off_length)`` in metres, measured along the line,
    so the pattern is independent of how densely the polyline was sampled.
    Returns a list of point lists; run boundaries are interpolated onto the
    original segments, so the dashes lie exactly on the source line.
    """
    on_length, off_length = (float(dash[0]), float(dash[1]))
    if on_length <= 0.0 or off_length <= 0.0:
        return [list(points)]

    runs = []
    current = [points[0]]
    drawing = True
    remaining = on_length

    for start, end in zip(points, points[1:]):
        span = (end - start).length
        if span <= 1e-12:
            continue
        travelled = 0.0
        while span - travelled > remaining:
            travelled += remaining
            cut = start.lerp(end, travelled / span)
            if drawing:
                current.append(cut)
                if len(current) >= 2:
                    runs.append(current)
                current = []
            else:
                current = [cut]
            drawing = not drawing
            remaining = on_length if drawing else off_length
        remaining -= span - travelled
        if drawing:
            current.append(end)

    if drawing and len(current) >= 2:
        runs.append(current)
    return runs


def parent_to(child: bpy.types.Object, root: bpy.types.Object) -> bpy.types.Object:
    """Parent ``child`` to ``root`` without moving it.

    Uses ``matrix_basis`` rather than ``matrix_world``: an object created this
    tick has not been through the dependency graph yet, so its ``matrix_world``
    is still the identity and a parent inverse taken from it would offset every
    child by the root's own transform. ``matrix_basis`` is correct immediately.
    """
    child.parent = root
    child.matrix_parent_inverse = root.matrix_basis.inverted()
    return child


def read_params(obj: bpy.types.Object) -> dict:
    """Recover the parameters an element was created with."""
    raw = obj.get("hd_params")
    if not raw:
        return {}
    try:
        return json.loads(raw)
    except (TypeError, ValueError):
        return {}


def elements_of_kind(kind: str) -> list:
    """Every object in the file created as ``kind``."""
    wanted = kind.lower()
    return [o for o in bpy.data.objects if o.get("hd_kind") == wanted]


def _serialisable(value):
    """Make Vectors, tuples and floats JSON-safe without losing meaning."""
    if isinstance(value, dict):
        return {str(k): _serialisable(v) for k, v in value.items()}
    if isinstance(value, Vector):
        return [round(float(c), 6) for c in value]
    if isinstance(value, (list, tuple)):
        return [_serialisable(v) for v in value]
    if isinstance(value, float):
        return round(value, 6)
    if isinstance(value, (int, str, bool)) or value is None:
        return value
    return str(value)
