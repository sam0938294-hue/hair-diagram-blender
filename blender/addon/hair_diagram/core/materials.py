"""Flat, readable materials for technical diagrams.

Two families only:

* **surface** -- the mannequin. Diffuse, unsaturated, no specular highlights
  that would compete with the annotation.
* **ink** -- every diagram line, arrow, label and arc. Emission shaders, so the
  colour is exactly the configured colour from every camera angle regardless of
  the lighting. That is what makes a batch of 200 diagrams look consistent.

Each material also sets ``diffuse_color`` so the Workbench engine and the solid
viewport show the same colours as a render.
"""

from __future__ import annotations

import bpy

from .. import config
from . import naming


def ensure_ink(key: str, color) -> bpy.types.Material:
    """An unlit, fully saturated material used for annotation geometry."""
    mat = _get_or_create(naming.name("MAT_INK", key))
    if mat.get("hd_kind") == "ink":
        return mat
    mat["hd_kind"] = "ink"
    mat.use_nodes = True
    tree = mat.node_tree
    tree.nodes.clear()
    out = tree.nodes.new("ShaderNodeOutputMaterial")
    out.location = (200, 0)
    emit = tree.nodes.new("ShaderNodeEmission")
    emit.location = (0, 0)
    emit.inputs["Color"].default_value = _rgba(color)
    emit.inputs["Strength"].default_value = 1.0
    tree.links.new(emit.outputs["Emission"], out.inputs["Surface"])
    mat.diffuse_color = _rgba(color)
    mat.roughness = 1.0
    return mat


def ensure_surface(key: str, color) -> bpy.types.Material:
    """A matte material for the mannequin head and other solid geometry."""
    mat = _get_or_create(naming.name("MAT_SURF", key))
    if mat.get("hd_kind") == "surface":
        return mat
    mat["hd_kind"] = "surface"
    mat.use_nodes = True
    tree = mat.node_tree
    tree.nodes.clear()
    out = tree.nodes.new("ShaderNodeOutputMaterial")
    out.location = (200, 0)
    bsdf = tree.nodes.new("ShaderNodeBsdfPrincipled")
    bsdf.location = (0, 0)
    bsdf.inputs["Base Color"].default_value = _rgba(color)
    _set_input(bsdf, "Roughness", 0.85)
    _set_input(bsdf, "Specular IOR Level", 0.15)
    _set_input(bsdf, "Metallic", 0.0)
    tree.links.new(bsdf.outputs["BSDF"], out.inputs["Surface"])
    mat.diffuse_color = _rgba(color)
    mat.roughness = 0.85
    return mat


def ensure_translucent(key: str, color) -> bpy.types.Material:
    """A see-through material for highlight areas (coloring panels later)."""
    mat = _get_or_create(naming.name("MAT_GLASS", key))
    if mat.get("hd_kind") == "translucent":
        return mat
    mat["hd_kind"] = "translucent"
    mat.use_nodes = True
    tree = mat.node_tree
    tree.nodes.clear()
    out = tree.nodes.new("ShaderNodeOutputMaterial")
    out.location = (400, 0)
    emit = tree.nodes.new("ShaderNodeEmission")
    emit.location = (0, 100)
    emit.inputs["Color"].default_value = _rgba(color)
    emit.inputs["Strength"].default_value = 1.0
    transparent = tree.nodes.new("ShaderNodeBsdfTransparent")
    transparent.location = (0, -100)
    mix = tree.nodes.new("ShaderNodeMixShader")
    mix.location = (200, 0)
    mix.inputs["Fac"].default_value = float(_rgba(color)[3])
    tree.links.new(transparent.outputs["BSDF"], mix.inputs[1])
    tree.links.new(emit.outputs["Emission"], mix.inputs[2])
    tree.links.new(mix.outputs["Shader"], out.inputs["Surface"])
    mat.diffuse_color = _rgba(color)
    _set_blended(mat)
    return mat


def assign(obj: bpy.types.Object, mat: bpy.types.Material) -> bpy.types.Object:
    """Replace every material slot of ``obj`` with a single material."""
    data = obj.data
    if not hasattr(data, "materials"):
        return obj
    data.materials.clear()
    data.materials.append(mat)
    return obj


# ---------------------------------------------------------------------------
# internals
# ---------------------------------------------------------------------------

def _get_or_create(full_name: str) -> bpy.types.Material:
    mat = bpy.data.materials.get(full_name)
    return mat if mat is not None else bpy.data.materials.new(full_name)


def _rgba(color) -> tuple[float, float, float, float]:
    color = tuple(float(c) for c in color)
    return color if len(color) == 4 else color + (1.0,)


def _set_input(node, socket_name: str, value) -> None:
    """Set a Principled input if this Blender build has it under that name."""
    socket = node.inputs.get(socket_name)
    if socket is not None:
        socket.default_value = value


def _set_blended(mat: bpy.types.Material) -> None:
    """Ask for real alpha blending across EEVEE generations.

    Blender 4.2+ renamed ``blend_method`` to ``surface_render_method``; both
    spellings are tried so the module keeps working either way.
    """
    if "surface_render_method" in mat.bl_rna.properties:
        mat.surface_render_method = "BLENDED"
    elif "blend_method" in mat.bl_rna.properties:
        mat.blend_method = "BLEND"
    if "show_transparent_back" in mat.bl_rna.properties:
        mat.show_transparent_back = False


# ---------------------------------------------------------------------------
# named shortcuts used across the package
# ---------------------------------------------------------------------------

def head() -> bpy.types.Material:
    return ensure_surface("HEAD", config.COLOR_HEAD)


def neck() -> bpy.types.Material:
    return ensure_surface("NECK", config.COLOR_NECK)


def section() -> bpy.types.Material:
    return ensure_ink("SECTION", config.COLOR_SECTION)


def guide() -> bpy.types.Material:
    return ensure_ink("GUIDE", config.COLOR_GUIDE)


def arrow() -> bpy.types.Material:
    return ensure_ink("ARROW", config.COLOR_ARROW)


def angle() -> bpy.types.Material:
    return ensure_ink("ANGLE", config.COLOR_ANGLE)


def measurement() -> bpy.types.Material:
    return ensure_ink("MEASURE", config.COLOR_MEASURE)


def label() -> bpy.types.Material:
    return ensure_ink("LABEL", config.COLOR_LABEL)


def highlight() -> bpy.types.Material:
    return ensure_translucent("HIGHLIGHT", config.COLOR_HIGHLIGHT)
