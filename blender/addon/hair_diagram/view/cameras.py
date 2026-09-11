"""The fixed technical camera rig.

Nine cameras at fixed azimuths around the head plus one from above. They are
orthographic and all share one ``ortho_scale``, which is what makes a set of
diagrams comparable: an element that measures 30 px on the front view measures
30 px on the back view too (DECISIONS.md D007).

Cameras are aimed analytically at creation time rather than with Track To
constraints, so a background render needs no dependency-graph evaluation to
produce the right framing.
"""

from __future__ import annotations

import math

import bpy
from mathutils import Vector

from .. import config
from ..core import collections, naming
from ..core.errors import CameraNotFoundError


def setup(scene: bpy.types.Scene | None = None, replace: bool = False) -> dict:
    """Create every camera in :data:`config.CAMERA_KEYS`.

    Idempotent. Returns ``{key: camera object}`` and leaves
    :data:`config.DEFAULT_CAMERA` active.
    """
    scene = scene or bpy.context.scene
    cameras = {}
    for key in config.CAMERA_KEYS:
        cameras[key] = _ensure_camera(key, scene, replace)
    set_active(config.DEFAULT_CAMERA, scene)
    return cameras


def get(key_or_object, scene: bpy.types.Scene | None = None) -> bpy.types.Object:
    """Resolve a camera key (``"front_left_45"``) or object to a camera object."""
    if isinstance(key_or_object, bpy.types.Object):
        if key_or_object.type != "CAMERA":
            raise CameraNotFoundError(f"{key_or_object.name!r} is not a camera.")
        return key_or_object

    key = str(key_or_object).strip().lower()
    camera = bpy.data.objects.get(naming.camera_name(key))
    if camera is None:
        camera = bpy.data.objects.get(str(key_or_object))
    if camera is None or camera.type != "CAMERA":
        raise CameraNotFoundError(
            f"No camera for {key_or_object!r}. "
            f"Available keys: {list(config.CAMERA_KEYS)}. "
            "Call setup_cameras() if the rig has not been built yet."
        )
    return camera


def set_active(key_or_object, scene: bpy.types.Scene | None = None) -> bpy.types.Object:
    """Make a camera the scene camera; billboard labels re-aim at it."""
    scene = scene or bpy.context.scene
    camera = get(key_or_object, scene)
    scene.camera = camera
    _retarget_billboards(camera)
    return camera


def active_key(scene: bpy.types.Scene | None = None) -> str | None:
    """The key of the current scene camera, if it is one of ours."""
    scene = scene or bpy.context.scene
    if scene.camera is None:
        return None
    return scene.camera.get("hd_camera_key")


def keys() -> tuple:
    return config.CAMERA_KEYS


# ---------------------------------------------------------------------------
# internals
# ---------------------------------------------------------------------------

def _ensure_camera(key: str, scene: bpy.types.Scene, replace: bool) -> bpy.types.Object:
    obj_name = naming.camera_name(key)
    if replace:
        existing = bpy.data.objects.get(obj_name)
        if existing is not None:
            bpy.data.objects.remove(existing, do_unlink=True)

    camera = bpy.data.objects.get(obj_name)
    if camera is None:
        data = bpy.data.cameras.new(obj_name)
        camera = bpy.data.objects.new(obj_name, data)
        collections.link(camera, "CAMERAS")

    data = camera.data
    data.type = "ORTHO"
    data.ortho_scale = config.CAMERA_ORTHO_SCALE
    data.clip_start = config.CAMERA_CLIP_START
    data.clip_end = config.CAMERA_CLIP_END

    camera.location, camera.rotation_euler = _placement(key)
    camera.rotation_mode = "XYZ"
    camera["hd_camera_key"] = key
    return camera


def _placement(key: str):
    """Position and rotation for one camera key, in world space."""
    target = Vector(config.CAMERA_TARGET)

    if key == config.CAMERA_TOP:
        # Looking straight down. Rotated 180 degrees about Z so the face points
        # to the top of the frame and the model's left falls on the left of the
        # frame -- what a stylist standing behind the client sees.
        location = target + Vector((0.0, 0.0, config.CAMERA_DISTANCE))
        return location, (0.0, 0.0, math.pi)

    azimuth = math.radians(config.CAMERA_AZIMUTHS[key])
    elevation = math.radians(config.CAMERA_ELEVATION_DEG)
    horizontal = math.cos(elevation)
    direction = Vector((
        horizontal * math.sin(azimuth),
        -horizontal * math.cos(azimuth),
        math.sin(elevation),
    ))
    location = target + direction * config.CAMERA_DISTANCE
    rotation = (target - location).to_track_quat("-Z", "Y").to_euler("XYZ")
    return location, rotation


def _retarget_billboards(camera: bpy.types.Object) -> None:
    """Point every camera-facing label at the newly active camera.

    Billboarding is a Copy Rotation constraint, so switching cameras is a
    matter of re-pointing those constraints rather than recomputing transforms.
    """
    for obj in bpy.data.objects:
        if not obj.get("hd_billboard"):
            continue
        constraint = obj.constraints.get("HD_BILLBOARD")
        if constraint is not None:
            constraint.target = camera
