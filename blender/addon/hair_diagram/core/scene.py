"""Scene-level setup: units, colour management, render defaults, collections.

``create_scene()`` is the single entry point every script and every test calls
first. It is idempotent, so it can be re-run inside an open Blender session
without duplicating anything.
"""

from __future__ import annotations

import bpy

from .. import config
from . import collections, naming


def create_scene(scene: bpy.types.Scene | None = None, clear: bool = False) -> bpy.types.Scene:
    """Prepare a scene for diagram work.

    ``clear=True`` removes the default startup objects (Cube, Light, Camera)
    and any previous ``HD_`` objects -- what a background build script wants.
    """
    scene = scene or bpy.context.scene
    if clear:
        clear_scene(scene)
    apply_units(scene)
    apply_render_defaults(scene)
    collections.ensure_collections(scene)
    return scene


def clear_scene(scene: bpy.types.Scene | None = None) -> None:
    """Remove all objects from the scene and purge orphaned data."""
    scene = scene or bpy.context.scene
    for obj in list(bpy.data.objects):
        bpy.data.objects.remove(obj, do_unlink=True)
    for collection in list(bpy.data.collections):
        bpy.data.collections.remove(collection)
    purge_orphans()


def purge_orphans() -> None:
    """Drop datablocks nothing references any more (meshes, curves, ...)."""
    for _ in range(4):
        removed = False
        for container in (
            bpy.data.meshes,
            bpy.data.curves,
            bpy.data.cameras,
            bpy.data.lights,
            bpy.data.materials,
        ):
            for datablock in list(container):
                if datablock.users == 0:
                    container.remove(datablock)
                    removed = True
        if not removed:
            break


def apply_units(scene: bpy.types.Scene) -> None:
    """Metric, 1 unit = 1 m, displayed in centimetres (DECISIONS.md D002)."""
    units = scene.unit_settings
    units.system = "METRIC"
    units.scale_length = 1.0
    units.length_unit = "CENTIMETERS"


def apply_render_defaults(scene: bpy.types.Scene) -> None:
    """Engine, samples, resolution and colour management for flat diagrams."""
    render = scene.render
    render.engine = config.RENDER_ENGINE
    render.resolution_x = config.RENDER_WIDTH
    render.resolution_y = config.RENDER_HEIGHT
    render.resolution_percentage = 100
    render.film_transparent = config.RENDER_TRANSPARENT
    render.image_settings.file_format = "PNG"
    render.image_settings.color_mode = "RGBA"
    render.image_settings.color_depth = "8"
    render.image_settings.compression = 15

    # No tone mapping: a diagram's colours must survive the render untouched.
    try:
        scene.view_settings.view_transform = config.VIEW_TRANSFORM
        scene.view_settings.look = "None"
        scene.view_settings.exposure = 0.0
        scene.view_settings.gamma = 1.0
    except (TypeError, AttributeError):
        pass

    apply_engine_settings(scene)


def apply_engine_settings(scene: bpy.types.Scene) -> None:
    """Per-engine quality settings, applied only where the engine has them."""
    engine = scene.render.engine

    if engine == "BLENDER_EEVEE":
        eevee = scene.eevee
        eevee.taa_render_samples = config.RENDER_SAMPLES
        eevee.taa_samples = min(16, config.RENDER_SAMPLES)
        if "use_raytracing" in eevee.bl_rna.properties:
            eevee.use_raytracing = False   # diagrams need no reflections
    elif engine == "BLENDER_WORKBENCH":
        shading = scene.display.shading
        shading.light = "STUDIO"
        shading.color_type = "MATERIAL"
        shading.show_object_outline = True
        shading.show_cavity = False
        shading.show_specular_highlight = False
        scene.display.render_aa = "16"
    elif engine == "CYCLES" and hasattr(scene, "cycles"):
        scene.cycles.samples = config.RENDER_SAMPLES
        scene.cycles.use_denoising = True


def set_engine(engine: str, scene: bpy.types.Scene | None = None) -> str:
    """Switch render engine and re-apply that engine's settings."""
    scene = scene or bpy.context.scene
    scene.render.engine = engine
    apply_engine_settings(scene)
    return scene.render.engine


def save(filepath: str) -> str:
    """Save the current blend file, creating parent directories as needed."""
    import os

    directory = os.path.dirname(os.path.abspath(filepath))
    os.makedirs(directory, exist_ok=True)
    bpy.ops.wm.save_as_mainfile(filepath=os.path.abspath(filepath))
    return os.path.abspath(filepath)
