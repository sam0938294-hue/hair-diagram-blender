"""The small error vocabulary of the system.

Deliberately shallow: one base class so callers can catch everything from this
package, and a handful of specific classes for the failure modes that actually
happen when a diagram script runs unattended.
"""

from __future__ import annotations


class HairDiagramError(Exception):
    """Base class for every error raised by the Hair Diagram System."""


class SceneNotReadyError(HairDiagramError):
    """The scene is missing something the operation needs (head, rig, ...)."""


class CameraNotFoundError(HairDiagramError):
    """A camera key or camera object could not be resolved."""


class PresetError(HairDiagramError):
    """A preset file is missing, malformed, or references unknown names."""


class OutputPathError(HairDiagramError):
    """An output path is unusable (empty, a directory, undeletable, ...)."""


class SurfaceProjectionError(HairDiagramError):
    """A point could not be projected onto the head surface."""
