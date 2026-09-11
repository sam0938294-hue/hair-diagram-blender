"""JSON presets: a saved view of the scene.

A preset answers "which camera, which layers, what size" -- the settings that
change between two diagrams of the *same* scene. It deliberately does not
describe the diagram objects themselves yet; that schema arrives with the
CUTTING / COLORING / PERM domains, and ``version`` is here so those files can
be told apart from these (DECISIONS.md D011).

Schema (version 1)::

    {
      "version": 1,
      "name": "demo_front_45",
      "camera": "front_left_45",
      "visible_collections": ["HEAD", "SECTION_LINES", "ARROWS", "LABELS"],
      "render": {"width": 2000, "height": 2000, "transparent": true}
    }

Every key except ``name`` is optional; a missing key means "leave it alone".
"""

from __future__ import annotations

import json
import os

import bpy

from .. import config
from ..core import collections, naming
from ..core.errors import PresetError
from ..view import cameras

VERSION = 1
EXTENSION = ".json"


def capture(name: str, scene: bpy.types.Scene | None = None) -> dict:
    """Build a preset dict from the scene as it stands right now."""
    scene = scene or bpy.context.scene
    return {
        "version": VERSION,
        "name": str(name),
        "camera": cameras.active_key(scene) or config.DEFAULT_CAMERA,
        "visible_collections": collections.visible_keys(scene),
        "render": {
            "width": scene.render.resolution_x,
            "height": scene.render.resolution_y,
            "transparent": bool(scene.render.film_transparent),
        },
    }


def save_preset(name: str, directory: str = config.PRESET_DIR, scene=None, data=None) -> str:
    """Write a preset to ``<directory>/<name>.json`` and return the path."""
    data = data or capture(name, scene)
    validate(data)
    path = _path(name, directory)
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as handle:
        json.dump(data, handle, indent=2, ensure_ascii=False)
        handle.write("\n")
    return path


def load_preset(name_or_path: str, directory: str = config.PRESET_DIR) -> dict:
    """Read a preset by name or by path. Raises PresetError if unusable."""
    path = name_or_path if str(name_or_path).lower().endswith(EXTENSION) else _path(
        name_or_path, directory
    )
    path = os.path.abspath(path)
    if not os.path.exists(path):
        raise PresetError(f"No preset at {path!r}.")
    try:
        with open(path, "r", encoding="utf-8") as handle:
            data = json.load(handle)
    except (OSError, ValueError) as error:
        raise PresetError(f"Preset {path!r} could not be read: {error}") from error
    validate(data)
    return data


def apply_preset(preset, scene: bpy.types.Scene | None = None) -> dict:
    """Apply a preset dict, or a name/path to load one from. Returns the dict."""
    scene = scene or bpy.context.scene
    data = preset if isinstance(preset, dict) else load_preset(preset)
    validate(data)

    if data.get("camera"):
        cameras.set_active(data["camera"], scene)
    if data.get("visible_collections") is not None:
        collections.apply_visibility(data["visible_collections"], scene)

    render = data.get("render") or {}
    if "width" in render:
        scene.render.resolution_x = int(render["width"])
    if "height" in render:
        scene.render.resolution_y = int(render["height"])
    if "transparent" in render:
        scene.render.film_transparent = bool(render["transparent"])
    return data


def list_presets(directory: str = config.PRESET_DIR) -> list:
    """Names of every preset in a directory, sorted."""
    directory = os.path.abspath(directory)
    if not os.path.isdir(directory):
        return []
    return sorted(
        os.path.splitext(f)[0] for f in os.listdir(directory) if f.endswith(EXTENSION)
    )


def validate(data) -> dict:
    """Check a preset's shape and vocabulary before it touches the scene."""
    if not isinstance(data, dict):
        raise PresetError(f"A preset must be a JSON object, got {type(data).__name__}.")
    if not data.get("name"):
        raise PresetError("A preset needs a non-empty 'name'.")

    version = data.get("version", VERSION)
    if not isinstance(version, int) or version > VERSION:
        raise PresetError(
            f"Preset version {version!r} is newer than this build supports (v{VERSION})."
        )

    camera = data.get("camera")
    if camera is not None and camera not in config.CAMERA_KEYS:
        raise PresetError(
            f"Preset {data['name']!r} references unknown camera {camera!r}. "
            f"Valid: {list(config.CAMERA_KEYS)}"
        )

    visible = data.get("visible_collections")
    if visible is not None:
        if not isinstance(visible, list):
            raise PresetError("'visible_collections' must be a list of collection keys.")
        unknown = {naming.collection_key(k).upper() for k in visible} - set(config.COLLECTIONS)
        if unknown:
            raise PresetError(
                f"Preset {data['name']!r} references unknown collection(s) {sorted(unknown)}."
            )

    render = data.get("render")
    if render is not None and not isinstance(render, dict):
        raise PresetError("'render' must be an object.")
    return data


def _path(name: str, directory: str) -> str:
    stem = str(name).strip()
    if not stem:
        raise PresetError("A preset name must not be empty.")
    if not stem.endswith(EXTENSION):
        stem += EXTENSION
    return os.path.abspath(os.path.join(directory, stem))
