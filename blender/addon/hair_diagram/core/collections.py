"""Creation and visibility control of the diagram collection tree.

Every diagram object lives in exactly one of these collections, so an entire
class of annotation can be switched off with one call -- which is what presets
and multi-variant diagram batches are built on.
"""

from __future__ import annotations

import bpy

from .. import config
from . import naming
from .errors import SceneNotReadyError


def ensure_collections(scene: bpy.types.Scene | None = None) -> dict[str, bpy.types.Collection]:
    """Create the whole ``HD_*`` collection tree if it is not there yet.

    Idempotent: calling it on an existing scene returns the existing
    collections untouched.
    """
    scene = scene or bpy.context.scene
    result: dict[str, bpy.types.Collection] = {}
    for key in config.COLLECTIONS:
        full = naming.collection_name(key)
        collection = bpy.data.collections.get(full)
        if collection is None:
            collection = bpy.data.collections.new(full)
        if collection.name not in scene.collection.children:
            scene.collection.children.link(collection)
        result[key] = collection
    return result


def get(key: str, scene: bpy.types.Scene | None = None) -> bpy.types.Collection:
    """Return one collection by key (``"ARROWS"``), raising if it is absent."""
    full = naming.collection_name(key)
    collection = bpy.data.collections.get(full)
    if collection is None:
        raise SceneNotReadyError(
            f"Collection {full!r} does not exist. Call create_scene() first."
        )
    return collection


def link(obj: bpy.types.Object, key: str, scene: bpy.types.Scene | None = None) -> bpy.types.Object:
    """Move ``obj`` into collection ``key``, unlinking it from anywhere else."""
    scene = scene or bpy.context.scene
    target = get(key, scene)
    for current in list(obj.users_collection):
        current.objects.unlink(obj)
    target.objects.link(obj)
    return obj


def set_visible(key: str, visible: bool, scene: bpy.types.Scene | None = None) -> None:
    """Show/hide a collection in both the viewport and renders."""
    collection = get(key, scene)
    collection.hide_viewport = not visible
    collection.hide_render = not visible
    layer = _find_layer_collection(
        (scene or bpy.context.scene).view_layers[0].layer_collection, collection.name
    )
    if layer is not None:
        layer.hide_viewport = not visible
        layer.exclude = False


def apply_visibility(visible_keys, scene: bpy.types.Scene | None = None) -> None:
    """Show exactly ``visible_keys``; hide every other toggleable collection.

    CAMERAS and LIGHTING are never hidden by this -- hiding them would break
    rendering, and no preset has a reason to.
    """
    wanted = {naming.collection_key(k).upper() for k in visible_keys}
    unknown = wanted - set(config.COLLECTIONS)
    if unknown:
        raise SceneNotReadyError(
            f"Unknown collection(s): {sorted(unknown)}. "
            f"Valid keys: {list(config.COLLECTIONS)}"
        )
    for key in config.TOGGLEABLE_COLLECTIONS:
        set_visible(key, key in wanted, scene)


def visible_keys(scene: bpy.types.Scene | None = None) -> list[str]:
    """The toggleable collections that are currently visible in renders."""
    return [k for k in config.TOGGLEABLE_COLLECTIONS if not get(k, scene).hide_render]


def _find_layer_collection(root, target_name: str):
    if root.collection.name == target_name:
        return root
    for child in root.children:
        found = _find_layer_collection(child, target_name)
        if found is not None:
            return found
    return None
