"""A procedural placeholder mannequin head.

Deliberately crude: it exists so the diagram architecture can be developed and
tested without licensing a commercial head model. It is generated from an
ellipsoid with a tapered jaw and a side face profile, plus separate neck and
ear objects.

Ears are separate objects on purpose. Section lines are projected by casting
rays from the head centre, and an ear sticking out of the skull would make
those rays land on the ear instead of the scalp behind it. Keeping the ears out
of ``HD_HEAD_BASE`` means partings follow the skull, which is what a parting
actually does.

Two rules keep it replaceable (DECISIONS.md D005):

1. Only ``HD_HEAD_BASE`` is ever used as a projection target, and it is looked
   up by name. Renaming a purchased head mesh to ``HD_HEAD_BASE`` is the whole
   swap procedure.
2. Nothing in this package writes diagram geometry into the head mesh.
"""

from __future__ import annotations

import math

import bmesh
import bpy
from mathutils import Matrix, Vector

from .. import config
from ..core import collections, materials, naming
from ..core.errors import SceneNotReadyError

HEAD_KIND = "HEAD"
HEAD_QUALIFIER = "BASE"
NECK_QUALIFIER = "NECK"
EAR_QUALIFIERS = {1: "EAR_L", -1: "EAR_R"}   # +1 is the model's left (+X)


def create(replace: bool = True) -> bpy.types.Object:
    """Build (or rebuild) the placeholder head and neck.

    Returns the head object, which is also the projection target used by the
    section-line system.
    """
    head_name = naming.name(HEAD_KIND, HEAD_QUALIFIER)
    neck_name = naming.name(HEAD_KIND, NECK_QUALIFIER)
    ear_names = {side: naming.name(HEAD_KIND, q) for side, q in EAR_QUALIFIERS.items()}

    if replace:
        for obj_name in [head_name, neck_name] + list(ear_names.values()):
            existing = bpy.data.objects.get(obj_name)
            if existing is not None:
                bpy.data.objects.remove(existing, do_unlink=True)

    head = _ensure(head_name, _build_cranium, materials.head)
    _ensure(neck_name, _build_neck, materials.neck)
    for side, ear_name in ear_names.items():
        _ensure(ear_name, lambda s=side: _build_ear(s), materials.head)

    return head


def _ensure(obj_name: str, build, material_factory) -> bpy.types.Object:
    obj = bpy.data.objects.get(obj_name)
    if obj is None:
        obj = _make_object(obj_name, build())
        collections.link(obj, "HEAD")
        materials.assign(obj, material_factory())
        _shade_smooth(obj)
    return obj


def get(required: bool = True):
    """The current head object, or None."""
    head = bpy.data.objects.get(naming.name(HEAD_KIND, HEAD_QUALIFIER))
    if head is None and required:
        raise SceneNotReadyError("No head in the scene. Call create_head() first.")
    return head


# ---------------------------------------------------------------------------
# geometry
# ---------------------------------------------------------------------------

def _build_cranium():
    mesh = bmesh.new()
    bmesh.ops.create_uvsphere(
        mesh,
        u_segments=config.HEAD_SEGMENTS,
        v_segments=config.HEAD_RINGS,
        radius=1.0,
    )
    for vert in mesh.verts:
        vert.co = _shape_head(vert.co)
    bmesh.ops.recalc_face_normals(mesh, faces=mesh.faces)
    return mesh


def _shape_head(unit: Vector) -> Vector:
    """Map a point on the unit sphere onto the head silhouette.

    Three independent profiles are applied as functions of the sphere's height
    parameter ``t``: the width (ear to ear), the face depth and the occiput
    depth. Every profile term uses an exponent above 1 on ``max(0, +-t)``, so
    its slope is zero where the two halves meet -- that is what keeps the
    surface free of the shading crease a plain ``if t < 0`` branch produces.

    The result is a rounded cranium above the centre and a narrowing jaw with a
    receding chin below it: enough for the silhouette to read as a head from
    every technical camera, and nothing more.
    """
    t = unit.z
    up = max(0.0, t)         # 0 at the centre, 1 at the apex
    down = max(0.0, -t)      # 0 at the centre, 1 at the chin

    # Vertical: a quadratic that is smooth through the centre while still
    # putting the apex and the chin at different distances from it.
    mid = (config.HEAD_SEMI_Z_UPPER + config.HEAD_SEMI_Z_LOWER) * 0.5
    skew = (config.HEAD_SEMI_Z_UPPER - config.HEAD_SEMI_Z_LOWER) * 0.5
    z = mid * t + skew * t * t

    # High exponents on ``down`` hold the full width through the temples and
    # then pull in sharply for the jaw, instead of tapering from the centre and
    # making the head read as an egg.
    width = 1.0 - 0.10 * (up ** 2.0) - 0.52 * (down ** 2.4)
    face_depth = 1.0 - 0.08 * (up ** 2.0) - 0.20 * (down ** 2.0)
    back_depth = 1.0 - 0.05 * (up ** 2.0) - 0.62 * (down ** 1.5)

    # The occipital bone. Without it the back of the head is a plain arc and
    # the crown/nape relationship a stylist works from is not readable.
    # A Gaussian rather than another power term: it has to bulge in the middle
    # of the back of the skull and fade both ways, and it stays smooth.
    back_depth += config.OCCIPUT_BULGE * math.exp(
        -(((down - config.OCCIPUT_CENTER) / config.OCCIPUT_WIDTH) ** 2.0)
    )

    x = unit.x * config.HEAD_SEMI_X * width
    y = unit.y * config.HEAD_SEMI_Y
    y *= face_depth if y < 0.0 else back_depth

    # The under-jaw. Lifting the low, rearward part of the surface turns the
    # bottom of the sphere into a jaw line sweeping up towards the ear instead
    # of a rounded bowl. Both factors are squared so the slope is zero where
    # they switch on, which keeps the surface smooth.
    z += config.JAW_LIFT * (down ** 2.0) * (max(0.0, unit.y) ** 2.0)

    # The side profile: brow, nose, lips and chin pushed forward along -Y,
    # faded out around the sides so the back of the head is untouched.
    horizontal = math.hypot(unit.x, unit.y)
    if horizontal > 1e-9:
        frontness = max(0.0, -unit.y / horizontal)
        if frontness > 0.0:
            y -= _face_profile(z) * (frontness ** config.FACE_WRAP)

    return Vector((x, y, z))


def _face_profile(z: float) -> float:
    """How far the face surface moves forward at height ``z``.

    Smoothstep interpolation through ``config.FACE_PROFILE``, which is ordered
    from the apex down. Outside the table the profile is flat.

    Smoothstep rather than linear: linear interpolation is only C0, so every
    row of the table becomes a crease running horizontally across the face, and
    those creases catch the light on the 3/4 views. Smoothstep has zero slope
    at each knot, so the profile reads as one continuous surface.
    """
    table = config.FACE_PROFILE
    if z >= table[0][0]:
        return table[0][1]
    if z <= table[-1][0]:
        return table[-1][1]
    for (upper_z, upper_v), (lower_z, lower_v) in zip(table, table[1:]):
        if lower_z <= z <= upper_z:
            span = upper_z - lower_z
            if span <= 1e-12:
                return lower_v
            blend = (z - lower_z) / span
            blend = blend * blend * (3.0 - 2.0 * blend)
            return lower_v + (upper_v - lower_v) * blend
    return 0.0


def _build_ear(side: int):
    """One ear. ``side`` is +1 for the model's left.

    A sphere shaped into an ear before it is scaled and placed: the inner face
    is flattened so the ear lies against the skull rather than floating off it,
    the outer face is dished into a concha, and the lower half narrows into a
    lobe. Still schematic, but it reads as an ear at diagram scale instead of
    as a bump.
    """
    mesh = bmesh.new()
    bmesh.ops.create_uvsphere(
        mesh,
        u_segments=config.EAR_SEGMENTS,
        v_segments=config.EAR_RINGS,
        radius=1.0,
    )
    for vert in mesh.verts:
        vert.co = _shape_ear(vert.co)

    thickness, depth, height = config.EAR_SIZE
    centre = Vector(config.EAR_CENTER)
    centre.x *= side

    transform = (
        Matrix.Translation(centre)
        @ Matrix.Rotation(math.radians(config.EAR_TILT_DEG), 4, "X")
        @ Matrix.Diagonal((thickness, depth, height, 1.0))
    )
    bmesh.ops.transform(mesh, matrix=transform, verts=mesh.verts)
    bmesh.ops.recalc_face_normals(mesh, faces=mesh.faces)
    return mesh


def _shape_ear(unit: Vector) -> Vector:
    """Shape a unit sphere into an ear, in the ear's own local axes.

    +X is away from the head, +Y forward, +Z up. Called before the ear is
    scaled to ``config.EAR_SIZE``, so everything here is in sphere units.
    """
    x, y, z = unit.x, unit.y, unit.z

    if x < 0.0:
        x *= 0.30                       # flatten the side against the skull
    else:
        # Dish the outer face: a bell centred a little below the middle.
        dish = math.exp(-((y * y + (z + 0.15) ** 2.0) / 0.30))
        x *= 1.0 - 0.55 * dish

    lobe = max(0.0, -z)                 # narrower towards the lobe
    y *= 1.0 - 0.38 * (lobe ** 1.6)
    x *= 1.0 - 0.25 * (lobe ** 2.0)

    return Vector((x, y, z))


def _build_neck():
    mesh = bmesh.new()
    bmesh.ops.create_cone(
        mesh,
        cap_ends=True,
        cap_tris=False,
        segments=config.NECK_SEGMENTS,
        radius1=config.NECK_RADIUS_BOTTOM,
        radius2=config.NECK_RADIUS_TOP,
        depth=config.NECK_TOP_Z - config.NECK_BOTTOM_Z,
    )
    offset = Vector((
        0.0,
        config.NECK_OFFSET_Y,
        (config.NECK_TOP_Z + config.NECK_BOTTOM_Z) * 0.5,
    ))
    for vert in mesh.verts:
        vert.co += offset
    bmesh.ops.recalc_face_normals(mesh, faces=mesh.faces)
    return mesh


def _make_object(obj_name: str, mesh) -> bpy.types.Object:
    data = bpy.data.meshes.new(obj_name)
    mesh.to_mesh(data)
    mesh.free()
    return bpy.data.objects.new(obj_name, data)


def _shade_smooth(obj: bpy.types.Object) -> None:
    for polygon in obj.data.polygons:
        polygon.use_smooth = True
