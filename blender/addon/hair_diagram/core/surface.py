"""Projecting diagram geometry onto the head surface.

This is the one piece of the system that touches the head mesh, and it does so
through ray casting only -- never through modifiers bound to a particular mesh
and never by editing the head. Swap in a commercial head model and every
section line still lands on it, as long as the model is roughly star-shaped
around its centre (all real heads are). See DECISIONS.md D005.

Everything here works in *world* space; the local-space conversion for
``Object.ray_cast`` happens internally.
"""

from __future__ import annotations

import math

import bpy
from mathutils import Matrix, Vector

from .. import config
from . import naming
from .errors import SceneNotReadyError, SurfaceProjectionError

# How far outside the head rays start when probing inwards.
_PROBE_DISTANCE = 1.0


def default_target() -> bpy.types.Object:
    """The object diagram lines are projected onto (``HD_HEAD_BASE``).

    Resolved by name rather than by import, so replacing the placeholder with a
    purchased head model is a matter of naming that object correctly.
    """
    target = bpy.data.objects.get(naming.name("HEAD", "BASE"))
    if target is None:
        raise SceneNotReadyError(
            f"No projection target named {naming.name('HEAD', 'BASE')!r}. "
            "Call create_head() first, or rename your own head mesh to it."
        )
    return target


def head_center(target: bpy.types.Object | None = None) -> Vector:
    """The origin rays are cast from. Currently the head object's origin."""
    target = target or default_target()
    return target.matrix_world.translation.copy()


def project(
    direction,
    target: bpy.types.Object | None = None,
    offset: float = config.SURFACE_OFFSET,
    origin=None,
    strict: bool = True,
):
    """Find where ``direction`` leaves the head, offset along the surface normal.

    Returns ``(location, normal)`` in world space, or ``(None, None)`` when the
    ray misses and ``strict`` is False.

    Two casts are attempted. The first comes from outside the head inwards,
    which reliably picks the *outer* shell even where the surface is concave
    (behind the ear, under the occiput). The second, a fallback, goes from the
    centre outwards.
    """
    target = target or default_target()
    origin = Vector(origin) if origin is not None else head_center(target)
    direction = Vector(direction).normalized()
    if direction.length_squared == 0.0:
        raise SurfaceProjectionError("Projection direction must not be a zero vector.")

    depsgraph = bpy.context.evaluated_depsgraph_get()
    evaluated = target.evaluated_get(depsgraph)
    to_local = evaluated.matrix_world.inverted()
    normal_matrix = evaluated.matrix_world.to_3x3().inverted().transposed()

    far = origin + direction * _PROBE_DISTANCE
    attempts = (
        (far, -direction, _PROBE_DISTANCE * 2.0),   # outside -> in
        (origin, direction, _PROBE_DISTANCE),        # centre -> out
    )
    for ray_origin, ray_direction, distance in attempts:
        hit, location, normal, _index = evaluated.ray_cast(
            to_local @ ray_origin,
            (to_local.to_3x3() @ ray_direction).normalized(),
            distance=distance,
        )
        if hit:
            world_location = evaluated.matrix_world @ location
            world_normal = (normal_matrix @ normal).normalized()
            if world_normal.dot(direction) < 0.0:
                world_normal.negate()
            return world_location + world_normal * offset, world_normal

    if strict:
        raise SurfaceProjectionError(
            f"Ray along {tuple(round(c, 4) for c in direction)} never hit "
            f"{target.name!r}. Is the projection origin inside the mesh?"
        )
    return None, None


def project_many(directions, **kwargs):
    """:func:`project` over an iterable, returning ``(locations, normals)``."""
    locations, normals = [], []
    for direction in directions:
        location, normal = project(direction, **kwargs)
        if location is not None:
            locations.append(location)
            normals.append(normal)
    return locations, normals


# ---------------------------------------------------------------------------
# direction generators -- the parametric half of the section system
# ---------------------------------------------------------------------------

def spherical_direction(azimuth_deg: float, elevation_deg: float) -> Vector:
    """A direction from the head centre.

    ``azimuth`` follows the camera convention: 0 deg faces the front (-Y),
    90 deg the model's left (+X). ``elevation`` is degrees above the horizontal
    plane, so +90 deg is the apex.
    """
    azimuth = math.radians(azimuth_deg)
    elevation = math.radians(elevation_deg)
    horizontal = math.cos(elevation)
    return Vector((
        horizontal * math.sin(azimuth),
        -horizontal * math.cos(azimuth),
        math.sin(elevation),
    ))


def plane_basis(plane_normal) -> tuple[Vector, Vector]:
    """A reproducible orthonormal basis ``(u, v)`` for a plane.

    ``u`` is the world up axis projected into the plane, falling back to the
    front axis for horizontal planes. Fixing this rule is what makes a section
    line's start angle mean the same thing every time it is generated.
    """
    normal = Vector(plane_normal).normalized()
    reference = Vector((0.0, 0.0, 1.0))
    if abs(normal.dot(reference)) > 0.999:
        reference = Vector((0.0, -1.0, 0.0))
    u = (reference - normal * reference.dot(normal)).normalized()
    v = normal.cross(u).normalized()
    return u, v


def arc_directions(
    plane_normal,
    start_deg: float = 0.0,
    end_deg: float = 360.0,
    count: int = 96,
):
    """Directions sweeping an arc inside a plane, for a section line.

    The angle is measured from :func:`plane_basis`'s ``u`` axis towards ``v``.
    """
    if count < 2:
        raise SurfaceProjectionError("An arc needs at least 2 sample points.")
    u, v = plane_basis(plane_normal)
    start = math.radians(start_deg)
    end = math.radians(end_deg)
    step = (end - start) / (count - 1)
    return [
        (u * math.cos(start + step * i) + v * math.sin(start + step * i)).normalized()
        for i in range(count)
    ]


def rotate_axis(axis, angle_deg: float, around) -> Vector:
    """``axis`` rotated by ``angle_deg`` around another vector."""
    return Matrix.Rotation(math.radians(angle_deg), 3, Vector(around).normalized()) @ Vector(axis)
