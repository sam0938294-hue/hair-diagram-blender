"""A minimal, fixed studio rig.

Four sun lamps plus a flat white world. Suns are used rather than area lights
because a sun's illumination does not depend on distance, so the head reads
identically no matter how the framing changes later.

The goal is legibility from every technical camera, not mood: no camera angle
in the rig should leave part of the head unreadably dark.
"""

from __future__ import annotations

import bpy
from mathutils import Vector

from .. import config
from ..core import collections, naming


def setup(scene: bpy.types.Scene | None = None, replace: bool = False) -> dict:
    """Create the light rig and the world shader. Idempotent."""
    scene = scene or bpy.context.scene
    lights = {}
    for key, direction, energy in config.LIGHT_RIG:
        lights[key] = _ensure_sun(key, direction, energy, replace)
    _ensure_world(scene)
    return lights


def _ensure_sun(key: str, direction, energy: float, replace: bool) -> bpy.types.Object:
    obj_name = naming.name("LIGHT", key)
    if replace:
        existing = bpy.data.objects.get(obj_name)
        if existing is not None:
            bpy.data.objects.remove(existing, do_unlink=True)

    light = bpy.data.objects.get(obj_name)
    if light is None:
        data = bpy.data.lights.new(obj_name, type="SUN")
        light = bpy.data.objects.new(obj_name, data)
        collections.link(light, "LIGHTING")

    data = light.data
    data.type = "SUN"
    data.energy = energy
    data.angle = config.LIGHT_ANGLE
    data.color = (1.0, 1.0, 1.0)

    offset = Vector(direction).normalized() * config.LIGHT_DISTANCE
    light.location = offset
    light.rotation_euler = (-offset).to_track_quat("-Z", "Y").to_euler("XYZ")
    return light


def _ensure_world(scene: bpy.types.Scene) -> bpy.types.World:
    world = scene.world
    if world is None:
        world = bpy.data.worlds.get(naming.name("WORLD"))
        if world is None:
            world = bpy.data.worlds.new(naming.name("WORLD"))
        scene.world = world

    world.use_nodes = True
    tree = world.node_tree
    tree.nodes.clear()
    output = tree.nodes.new("ShaderNodeOutputWorld")
    output.location = (200, 0)
    background = tree.nodes.new("ShaderNodeBackground")
    background.location = (0, 0)
    background.inputs["Color"].default_value = tuple(config.WORLD_COLOR) + (1.0,)
    background.inputs["Strength"].default_value = config.WORLD_STRENGTH
    tree.links.new(background.outputs["Background"], output.inputs["Surface"])
    return world
