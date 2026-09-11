"""Deterministic object naming.

Blender's automatic ``Curve.023`` names make diagrams impossible to script
against. Every object this system creates goes through here instead.

Convention (DECISIONS.md D004)::

    HD_<KIND>[_<QUALIFIER>][_<NNN>]

Examples::

    HD_HEAD_BASE      HD_CAM_FRONT_LEFT_45      HD_SECTION_001
    HD_ARROW_001      HD_LABEL_ANGLE_001        HD_LIGHT_KEY
"""

from __future__ import annotations

import re

import bpy

from .. import config

_INDEXED = re.compile(r"^(?P<stem>.+)_(?P<index>\d{3,})$")


def name(kind: str, qualifier: str | None = None) -> str:
    """Build an un-numbered name, e.g. ``HD_HEAD_BASE``."""
    parts = [config.PREFIX, kind.upper()]
    if qualifier:
        parts.append(_slug(qualifier))
    return "_".join(parts)


def indexed_name(kind: str, qualifier: str | None = None, digits: int = 3) -> str:
    """Build the next free numbered name, e.g. ``HD_SECTION_001``.

    The counter is derived from what already exists in the blend file, so
    re-running a build script keeps producing readable, gap-free names instead
    of Blender's ``.001`` suffixes.
    """
    stem = name(kind, qualifier)
    used = set()
    for collection in (bpy.data.objects, bpy.data.collections):
        for datablock in collection:
            match = _INDEXED.match(datablock.name)
            if match and match.group("stem") == stem:
                used.add(int(match.group("index")))
    index = 1
    while index in used:
        index += 1
    return f"{stem}_{index:0{digits}d}"


def collection_name(key: str) -> str:
    """``"SECTION_LINES"`` -> ``"HD_SECTION_LINES"``."""
    key = key.strip().upper()
    prefix = config.PREFIX + "_"
    return key if key.startswith(prefix) else prefix + key


def collection_key(collection_or_name) -> str:
    """Inverse of :func:`collection_name`; accepts a Collection or a string."""
    raw = getattr(collection_or_name, "name", collection_or_name)
    prefix = config.PREFIX + "_"
    return raw[len(prefix):] if raw.startswith(prefix) else raw


def camera_name(key: str) -> str:
    """``"front_left_45"`` -> ``"HD_CAM_FRONT_LEFT_45"``."""
    return name("CAM", key)


def _slug(text: str) -> str:
    text = re.sub(r"[^0-9A-Za-z]+", "_", str(text)).strip("_")
    return text.upper()
