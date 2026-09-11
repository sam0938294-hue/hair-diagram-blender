"""PNG rendering.

One function does the work. It saves and restores every scene setting it
touches, so rendering ten cameras in a loop cannot leave the scene in a
different state than it found it -- the property that makes batch generation
of hundreds of diagrams safe.
"""

from __future__ import annotations

import os

import bpy

from .. import config
from ..core import scene as scene_module
from ..core.errors import OutputPathError, SceneNotReadyError
from ..view import cameras


def render_diagram(
    camera=None,
    width: int = config.RENDER_WIDTH,
    height: int = config.RENDER_HEIGHT,
    transparent: bool = config.RENDER_TRANSPARENT,
    background=None,
    output_path: str = "exports/diagram.png",
    samples: int | None = None,
    engine: str | None = None,
    scene: bpy.types.Scene | None = None,
) -> str:
    """Render one diagram to a PNG and return its absolute path.

    Parameters
    ----------
    camera:
        Camera key (``"front_left_45"``) or camera object. Defaults to the
        scene's current camera.
    transparent:
        True writes an RGBA PNG with an empty background -- the default,
        because a diagram is usually placed onto a page later.
    background:
        RGBA fill used when ``transparent`` is False.
    """
    scene = scene or bpy.context.scene
    path = _prepare_path(output_path)

    if camera is not None:
        cameras.set_active(camera, scene)
    if scene.camera is None:
        raise SceneNotReadyError(
            "The scene has no active camera. Pass camera=... or call setup_cameras()."
        )

    render = scene.render
    saved = {
        "engine": render.engine,
        "resolution_x": render.resolution_x,
        "resolution_y": render.resolution_y,
        "resolution_percentage": render.resolution_percentage,
        "film_transparent": render.film_transparent,
        "filepath": render.filepath,
        "file_format": render.image_settings.file_format,
        "color_mode": render.image_settings.color_mode,
    }
    world_saved = _read_world_color(scene)

    try:
        if engine is not None:
            scene_module.set_engine(engine, scene)
        if samples is not None:
            _set_samples(scene, samples)

        render.resolution_x = int(width)
        render.resolution_y = int(height)
        render.resolution_percentage = 100
        render.film_transparent = bool(transparent)
        render.image_settings.file_format = "PNG"
        render.image_settings.color_mode = "RGBA" if transparent else "RGB"
        render.filepath = path

        if not transparent:
            _write_world_color(scene, background or config.RENDER_BACKGROUND)

        bpy.ops.render.render(write_still=True)
    finally:
        render.engine = saved["engine"]
        render.resolution_x = saved["resolution_x"]
        render.resolution_y = saved["resolution_y"]
        render.resolution_percentage = saved["resolution_percentage"]
        render.film_transparent = saved["film_transparent"]
        render.filepath = saved["filepath"]
        render.image_settings.file_format = saved["file_format"]
        render.image_settings.color_mode = saved["color_mode"]
        if world_saved is not None:
            _write_world_color(scene, world_saved)

    if not os.path.exists(path):
        raise OutputPathError(
            f"Blender reported success but no file appeared at {path!r}."
        )
    return path


def render_all_cameras(
    output_dir: str = config.EXPORT_DIR,
    stem: str = "diagram",
    keys=None,
    **kwargs,
) -> dict:
    """Render the same scene from several cameras. Returns ``{key: path}``."""
    keys = tuple(keys) if keys else cameras.keys()
    results = {}
    for key in keys:
        results[key] = render_diagram(
            camera=key,
            output_path=os.path.join(output_dir, f"{stem}_{key}.png"),
            **kwargs,
        )
    return results


# ---------------------------------------------------------------------------
# internals
# ---------------------------------------------------------------------------

def _prepare_path(output_path: str) -> str:
    if not output_path or not str(output_path).strip():
        raise OutputPathError("output_path must not be empty.")
    path = os.path.abspath(bpy.path.abspath(str(output_path)))
    if os.path.isdir(path):
        raise OutputPathError(f"output_path {path!r} is a directory, not a file.")
    if not path.lower().endswith(".png"):
        path += ".png"
    directory = os.path.dirname(path)
    try:
        os.makedirs(directory, exist_ok=True)
    except OSError as error:
        raise OutputPathError(f"Cannot create output directory {directory!r}: {error}") from error
    if not os.access(directory, os.W_OK):
        raise OutputPathError(f"Output directory {directory!r} is not writable.")
    return path


def _set_samples(scene: bpy.types.Scene, samples: int) -> None:
    engine = scene.render.engine
    if engine == "BLENDER_EEVEE":
        scene.eevee.taa_render_samples = int(samples)
    elif engine == "CYCLES" and hasattr(scene, "cycles"):
        scene.cycles.samples = int(samples)


def _read_world_color(scene: bpy.types.Scene):
    node = _background_node(scene)
    return tuple(node.inputs["Color"].default_value) if node else None


def _write_world_color(scene: bpy.types.Scene, color) -> None:
    node = _background_node(scene)
    if node is None:
        return
    color = tuple(float(c) for c in color)
    node.inputs["Color"].default_value = color if len(color) == 4 else color + (1.0,)


def _background_node(scene: bpy.types.Scene):
    world = scene.world
    if world is None or not world.use_nodes:
        return None
    for node in world.node_tree.nodes:
        if node.type == "BACKGROUND":
            return node
    return None
