"""The head coordinate convention and its landmarks.

Convention (DECISIONS.md D003), in Blender world axes::

    face / front  -> -Y        back / occiput -> +Y
    model's LEFT  -> +X        model's RIGHT  -> -X
    up / apex     -> +Z        head centre    -> (0, 0, 0)

"Left" and "right" are always the model's left and right, the way a stylist
describes a client, never the viewer's. Camera names follow the same rule: the
``left`` camera shows the model's left side.

Only the six landmarks needed today are implemented. ``LANDMARK_DIRECTIONS``
is the extension point: crown, occipital, nape, temple, parietal ridge, front
hairline and ear points are added as entries here, and every consumer picks
them up automatically.
"""

from __future__ import annotations

from mathutils import Vector

from ..core import surface
from ..core.errors import SceneNotReadyError

# Unit axes of the convention. Use these instead of literal tuples so a future
# change of convention is a one-line change.
FRONT = Vector((0.0, -1.0, 0.0))
BACK = Vector((0.0, 1.0, 0.0))
LEFT = Vector((1.0, 0.0, 0.0))
RIGHT = Vector((-1.0, 0.0, 0.0))
UP = Vector((0.0, 0.0, 1.0))
DOWN = Vector((0.0, 0.0, -1.0))

# Plane normals worth naming.
SAGITTAL = LEFT       # splits left from right -- the centre line lives here
CORONAL = FRONT       # splits front from back
TRANSVERSE = UP       # the horizontal plane

# name -> (azimuth degrees, elevation degrees), fed to
# surface.spherical_direction(). Azimuth 0 is the face, 90 the model's left.
LANDMARK_DIRECTIONS = {
    "FRONT": (0.0, 0.0),
    "BACK": (180.0, 0.0),
    "LEFT": (90.0, 0.0),
    "RIGHT": (270.0, 0.0),
    "APEX": (0.0, 90.0),
}


def center(target=None) -> Vector:
    """The head centre -- the origin of the whole convention."""
    return surface.head_center(target)


def landmark(name: str, offset: float = 0.0, target=None) -> Vector:
    """A named point on the current head surface, in world space.

    Computed by ray casting, so landmarks track whatever head mesh is loaded
    rather than being hard-coded to the placeholder's proportions.
    """
    key = name.strip().upper()
    if key == "CENTER":
        return center(target)
    if key not in LANDMARK_DIRECTIONS:
        known = ["CENTER"] + sorted(LANDMARK_DIRECTIONS)
        raise SceneNotReadyError(f"Unknown landmark {name!r}. Known: {known}")
    azimuth, elevation = LANDMARK_DIRECTIONS[key]
    location, _normal = surface.project(
        surface.spherical_direction(azimuth, elevation), target=target, offset=offset
    )
    return location


def all_landmarks(offset: float = 0.0, target=None) -> dict:
    """Every landmark at once -- handy for tests and debug overlays."""
    points = {"CENTER": center(target)}
    for key in LANDMARK_DIRECTIONS:
        points[key] = landmark(key, offset=offset, target=target)
    return points
