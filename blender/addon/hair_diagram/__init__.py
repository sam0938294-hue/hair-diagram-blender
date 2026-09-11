"""Hair Diagram System -- a reusable technical diagram toolkit for Blender.

Python APIs and a Chinese interactive sidebar share the same geometry tools.
The v0.3 editor stores independently editable diagram items in the blend file.

Usage inside Blender or from ``blender --background``::

    import hair_diagram as hd
    hd.build_base_scene()
    hd.render_diagram(camera="front", output_path="exports/front.png")
"""

from __future__ import annotations

bl_info = {
    "name": "Hair Diagram",
    "author": "Hair Diagram System",
    "version": (0, 3, 0),
    "blender": (5, 2, 0),
    "location": "View3D > Sidebar > Hair Diagram",
    "description": "Parametric technical diagrams for hairdressing education.",
    "category": "3D View",
}

__version__ = "0.3.0"

from .api import *          # noqa: F401,F403  -- the documented public surface
from . import api           # noqa: F401
from . import config        # noqa: F401


def register() -> None:
    from . import teaching
    teaching.register()
    from . import editor
    editor.register()


def unregister() -> None:
    from . import editor
    editor.unregister()
    from . import teaching
    teaching.unregister()
