"""The public API of the Hair Diagram System.

This is the surface every script, test and (later) UI panel should use. The
modules underneath are free to be reorganised; this file is the contract.

    import hair_diagram as hd

    hd.create_scene(clear=True)
    hd.create_head()
    hd.setup_cameras()
    hd.setup_lighting()
    hd.add_section_line(plane_normal=hd.landmarks.SAGITTAL)
    hd.add_arrow(start, end)
    hd.add_label("90", location)
    hd.render_diagram(camera="front_left_45", output_path="exports/demo.png")
"""

from __future__ import annotations

import bpy
from mathutils import Vector

from . import config
from .core import collections as _collections
from .core import materials as _materials
from .core import naming as _naming
from .core import scene as _scene
from .core import surface as _surface
from .elements import angle as _angle
from .elements import arrow as _arrow
from .elements import guide_line as _guide_line
from .elements import highlight as _highlight
from .elements import label as _label
from .elements import measurement as _measurement
from .elements import section_line as _section_line
from .head import landmarks as _landmarks
from .head import mannequin as _mannequin
from .output import presets as _presets
from .output import render as _render
from .view import cameras as _cameras
from .view import lighting as _lighting


__all__ = [
    "create_scene",
    "create_head",
    "setup_cameras",
    "setup_lighting",
    "build_base_scene",
    "set_camera",
    "get_camera",
    "camera_keys",
    "set_collection_visible",
    "save_scene",
    "add_section_line",
    "add_section_line_from_points",
    "add_guide_line",
    "add_arrow",
    "add_arrow_from_direction",
    "add_angle",
    "add_elevation_angle",
    "add_measurement",
    "add_label",
    "add_angle_label",
    "add_highlight_area",
    "project_to_surface",
    "surface_point",
    "surface_normal",
    "landmark",
    "render_diagram",
    "render_all_cameras",
    "save_preset",
    "load_preset",
    "apply_preset",
    "list_presets",
    "landmarks",
    "surface",
    "materials",
    "naming",
    "cameras",
    "config",
]


# ---------------------------------------------------------------------------
# scene
# ---------------------------------------------------------------------------

def create_scene(clear: bool = False, scene: bpy.types.Scene | None = None) -> bpy.types.Scene:
    """Prepare units, render defaults and the ``HD_*`` collection tree."""
    return _scene.create_scene(scene=scene, clear=clear)


def create_head(replace: bool = True) -> bpy.types.Object:
    """Generate the placeholder mannequin head. Returns ``HD_HEAD_BASE``."""
    return _mannequin.create(replace=replace)


def setup_cameras(replace: bool = False) -> dict:
    """Build the ten fixed technical cameras. Returns ``{key: object}``."""
    return _cameras.setup(replace=replace)


def setup_lighting(replace: bool = False) -> dict:
    """Build the studio light rig and the world. Returns ``{key: object}``."""
    return _lighting.setup(replace=replace)


def build_base_scene(clear: bool = True) -> bpy.types.Scene:
    """Scene + head + cameras + lighting, the state every diagram starts from."""
    scene = create_scene(clear=clear)
    create_head()
    setup_cameras()
    setup_lighting()
    return scene


def set_camera(key_or_object) -> bpy.types.Object:
    """Switch the active technical camera; billboard labels follow it."""
    return _cameras.set_active(key_or_object)


def get_camera(key_or_object) -> bpy.types.Object:
    return _cameras.get(key_or_object)


def camera_keys() -> tuple:
    return _cameras.keys()


def set_collection_visible(key: str, visible: bool) -> None:
    _collections.set_visible(key, visible)


def save_scene(filepath: str) -> str:
    """Save the .blend file."""
    return _scene.save(filepath)


# ---------------------------------------------------------------------------
# diagram elements
# ---------------------------------------------------------------------------

def add_section_line(**kwargs) -> bpy.types.Object:
    """A parting projected onto the head surface. See ``section_line.create``."""
    return _section_line.create(**kwargs)


def add_section_line_from_points(points, **kwargs) -> bpy.types.Object:
    return _section_line.create_from_points(points, **kwargs)


def add_guide_line(points, **kwargs) -> bpy.types.Object:
    """A free line through space (not projected)."""
    return _guide_line.create(points, **kwargs)


def add_arrow(start, end, **kwargs) -> bpy.types.Object:
    """A 3D direction arrow from ``start`` to ``end``."""
    return _arrow.create(start, end, **kwargs)


def add_arrow_from_direction(origin, direction, length: float, **kwargs) -> bpy.types.Object:
    return _arrow.create_from_direction(origin, direction, length, **kwargs)


def add_angle(vertex, direction_a, direction_b, **kwargs) -> bpy.types.Object:
    """An angle indicator: two legs, an arc and a degree label."""
    return _angle.create(vertex, direction_a, direction_b, **kwargs)


def add_elevation_angle(vertex, reference_direction, degrees: float, plane_normal, **kwargs):
    """An angle opened ``degrees`` from a reference direction."""
    return _angle.create_elevation(vertex, reference_direction, degrees, plane_normal, **kwargs)


def add_measurement(start, end, **kwargs) -> bpy.types.Object:
    """A dimension line with end ticks and a ``5 cm`` style label."""
    return _measurement.create(start, end, **kwargs)


def add_label(text: str, location, **kwargs) -> bpy.types.Object:
    """A text label; camera-facing by default."""
    return _label.create(text, location, **kwargs)


def add_angle_label(degrees, location, **kwargs) -> bpy.types.Object:
    """A label reading e.g. ``90`` with the degree sign appended."""
    return _label.angle_label(degrees, location, **kwargs)


def add_highlight_area(**kwargs) -> bpy.types.Object:
    """A translucent patch on the head surface."""
    return _highlight.create(**kwargs)


# ---------------------------------------------------------------------------
# geometry helpers
# ---------------------------------------------------------------------------

def project_to_surface(direction, **kwargs):
    """``(location, normal)`` where a direction from the head centre exits."""
    return _surface.project(direction, **kwargs)


def surface_point(azimuth_deg: float, elevation_deg: float, offset: float = 0.0) -> Vector:
    """The surface point at an azimuth/elevation, in world space."""
    location, _normal = _surface.project(
        _surface.spherical_direction(azimuth_deg, elevation_deg), offset=offset
    )
    return location


def surface_normal(azimuth_deg: float, elevation_deg: float) -> Vector:
    """The outward surface normal at an azimuth/elevation."""
    _location, normal = _surface.project(
        _surface.spherical_direction(azimuth_deg, elevation_deg)
    )
    return normal


def landmark(name: str, offset: float = 0.0) -> Vector:
    """A named landmark point, e.g. ``"APEX"``."""
    return _landmarks.landmark(name, offset=offset)


# ---------------------------------------------------------------------------
# output
# ---------------------------------------------------------------------------

def render_diagram(**kwargs) -> str:
    """Render a PNG. See ``output.render.render_diagram`` for the arguments."""
    return _render.render_diagram(**kwargs)


def render_all_cameras(**kwargs) -> dict:
    return _render.render_all_cameras(**kwargs)


def save_preset(name: str, **kwargs) -> str:
    return _presets.save_preset(name, **kwargs)


def load_preset(name_or_path: str, **kwargs) -> dict:
    return _presets.load_preset(name_or_path, **kwargs)


def apply_preset(preset, **kwargs) -> dict:
    return _presets.apply_preset(preset, **kwargs)


def list_presets(**kwargs) -> list:
    return _presets.list_presets(**kwargs)


# Sub-modules re-exported for callers that need more than the facade offers.
landmarks = _landmarks
surface = _surface
materials = _materials
naming = _naming
cameras = _cameras
