"""Central configuration for the Hair Diagram System.

Everything that is a *convention* (names, colours, sizes, camera layout) lives
here so diagrams stay consistent across hundreds of generated images.

Units
-----
1 Blender unit = 1 metre. The scene unit system is metric with the display
length unit set to centimetres, so measurements read as "13 cm" while the
maths stays in SI. See DECISIONS.md D002.
"""

from __future__ import annotations

# ---------------------------------------------------------------------------
# Naming
# ---------------------------------------------------------------------------

PREFIX = "HD"

# Collections ---------------------------------------------------------------
# Order matters: this is the order they are created in the outliner.
COLLECTIONS = (
    "HEAD",
    "REFERENCE",
    "SECTION_LINES",
    "GUIDE_LINES",
    "ARROWS",
    "ANGLES",
    "MEASUREMENTS",
    "LABELS",
    "HIGHLIGHTS",
    "CAMERAS",
    "LIGHTING",
)

# Collections that a preset may toggle. Keeping this explicit avoids a preset
# accidentally hiding the camera rig.
TOGGLEABLE_COLLECTIONS = tuple(c for c in COLLECTIONS if c not in ("CAMERAS", "LIGHTING"))


# ---------------------------------------------------------------------------
# Head geometry (placeholder mannequin)
# ---------------------------------------------------------------------------
# Half-dimensions of the head, in metres, measured from the head centre.
# Roughly an adult mannequin block: 141 mm across the skull (151 mm including
# the ears), 196 mm deep, 225 mm tall,
# with the crown closer to the centre than the chin is.
HEAD_SEMI_X = 0.0705        # skull breadth; the ears add to this
HEAD_SEMI_Y = 0.0980        # face to occiput
HEAD_SEMI_Z_UPPER = 0.1000  # centre to apex
HEAD_SEMI_Z_LOWER = 0.1120  # centre to chin

HEAD_SEGMENTS = 72
HEAD_RINGS = 40

# Side profile of the face, as (height above the head centre, how far the
# surface moves forward), both in metres. Linearly interpolated and blended
# towards the centre front by FACE_WRAP. Deliberately understated: teaching
# mannequins carry a readable brow/nose/chin silhouette and nothing else --
# no eyes, no mouth, no nostrils.
FACE_PROFILE = (
    (0.100, 0.000),    # apex
    (0.050, 0.006),    # forehead
    (0.015, 0.012),    # brow ridge
    (0.000, 0.004),    # eye line
    (-0.020, 0.014),   # bridge of the nose
    (-0.045, 0.028),   # tip of the nose
    (-0.055, 0.012),   # under the nose
    (-0.072, 0.016),   # lips
    (-0.085, 0.008),   # under the lip
    (-0.096, 0.012),   # chin
    (-0.108, 0.002),   # under the chin
)
FACE_WRAP = 3.0        # higher confines the profile more tightly to the centre

# The occipital bulge at the back of the skull, as a Gaussian on the same
# 0 (head centre) to 1 (chin) parameter the profiles use.
OCCIPUT_BULGE = 0.070
OCCIPUT_CENTER = 0.28
OCCIPUT_WIDTH = 0.24

# How far the underside of the jaw is lifted towards the ear, in metres.
JAW_LIFT = 0.055

# Ears are separate objects so section lines project onto the skull, not over
# the ear. Sizes are half-extents in metres.
EAR_CENTER = (0.0665, 0.0075, -0.0150)   # on the model's left; mirrored for right
EAR_SIZE = (0.0090, 0.0165, 0.0300)      # thickness, depth, height
EAR_TILT_DEG = 12.0                       # top tipped back, as on a real ear
EAR_SEGMENTS = 24
EAR_RINGS = 16

NECK_RADIUS_TOP = 0.050
NECK_RADIUS_BOTTOM = 0.058
NECK_TOP_Z = -0.050     # starts inside the head so the join is not visible
NECK_BOTTOM_Z = -0.200
NECK_OFFSET_Y = 0.022   # the neck sits behind the face, under the occiput
NECK_SEGMENTS = 48


# ---------------------------------------------------------------------------
# Cameras
# ---------------------------------------------------------------------------
# Camera key -> azimuth in degrees, measured in the XY plane.
#   0 deg   = front  (-Y, the direction the face looks)
#   90 deg  = the model's LEFT side (+X)
#   180 deg = back   (+Y)
#   270 deg = the model's RIGHT side (-X)
# See DECISIONS.md D003 for the anatomical naming convention.
CAMERA_AZIMUTHS = {
    "front": 0.0,
    "front_left_45": 45.0,
    "left": 90.0,
    "back_left_45": 135.0,
    "back": 180.0,
    "back_right_45": 225.0,
    "right": 270.0,
    "front_right_45": 315.0,
}

CAMERA_TOP = "top"
CAMERA_KEYS = tuple(CAMERA_AZIMUTHS) + (CAMERA_TOP,)
DEFAULT_CAMERA = "front_left_45"

CAMERA_DISTANCE = 1.2          # metres from the head centre; ortho, so this
                               # only affects clipping, not framing
CAMERA_ELEVATION_DEG = 0.0     # horizontal cameras look straight at the head
# The aim point, a little below the head centre so head and nape both sit in
# frame. The head centre itself stays at the origin.
CAMERA_TARGET = (0.0, 0.0, -0.045)
CAMERA_ORTHO_SCALE = 0.40      # framed width/height in metres -> identical
                               # framing on every camera
CAMERA_CLIP_START = 0.05
CAMERA_CLIP_END = 5.0


# ---------------------------------------------------------------------------
# Style
# ---------------------------------------------------------------------------
# RGBA, linear-ish values are fine for a flat technical look.
COLOR_HEAD = (0.620, 0.622, 0.640, 1.0)
COLOR_NECK = (0.560, 0.562, 0.580, 1.0)
COLOR_SECTION = (0.055, 0.060, 0.075, 1.0)
COLOR_GUIDE = (0.180, 0.380, 0.780, 1.0)
COLOR_ARROW = (0.850, 0.180, 0.130, 1.0)
COLOR_ANGLE = (0.100, 0.480, 0.280, 1.0)
COLOR_MEASURE = (0.930, 0.560, 0.050, 1.0)
COLOR_LABEL = (0.055, 0.060, 0.075, 1.0)
COLOR_HIGHLIGHT = (0.180, 0.550, 0.900, 0.35)

# Line thickness, in metres (bevel radius of the curve).
LINE_RADIUS_SECTION = 0.0018
LINE_RADIUS_GUIDE = 0.0014
LINE_RADIUS_ANGLE = 0.0012
LINE_RADIUS_MEASURE = 0.0012

# Dash patterns as (drawn length, gap length) in metres, measured along the
# line. Solid vs dashed is notation, not decoration: in professional teaching
# diagrams a panel boundary is solid and a projected or reference guide is
# dashed. Pass DASH_SOLID (None) for a continuous line.
DASH_SOLID = None
DASH_GUIDE = (0.011, 0.007)      # projected guides, front guide (FG)
DASH_FINE = (0.005, 0.004)       # construction and reference lines

# How far diagram lines float above the head surface so they never z-fight.
SURFACE_OFFSET = 0.0016

# Initial reference junction, adjusted from 18 degrees after the owner's
# annotated 2026-09-12 screenshot. This is a drawing position, not a standard.
REFERENCE_BP_ELEVATION = 12.0

LABEL_SIZE = 0.022             # cap height in metres
LABEL_OFFSET = 0.030           # default float above the anchor point

ARROW_SHAFT_RADIUS = 0.0030
ARROW_HEAD_LENGTH = 0.026
ARROW_HEAD_RADIUS = 0.0105
ARROW_SEGMENTS = 20


# ---------------------------------------------------------------------------
# Lighting
# ---------------------------------------------------------------------------
WORLD_STRENGTH = 0.30
WORLD_COLOR = (1.0, 1.0, 1.0)

# (name, direction the light points from, energy). Directions are unit-ish
# vectors from the head centre towards the lamp.
LIGHT_RIG = (
    ("KEY", (0.55, -0.85, 0.60), 1.5),
    ("FILL", (-0.75, -0.55, 0.15), 0.9),
    ("RIM", (0.10, 0.90, 0.45), 1.1),
    ("BACK_FILL", (-0.20, 0.70, -0.35), 0.6),
)
LIGHT_DISTANCE = 2.5
LIGHT_ANGLE = 0.35   # soft-ish sun angle in radians


# ---------------------------------------------------------------------------
# Render
# ---------------------------------------------------------------------------
RENDER_ENGINE = "BLENDER_EEVEE"   # see DECISIONS.md D006
RENDER_SAMPLES = 32
RENDER_WIDTH = 2000
RENDER_HEIGHT = 2000
RENDER_TRANSPARENT = True
RENDER_BACKGROUND = (1.0, 1.0, 1.0, 1.0)   # used when transparent is False
VIEW_TRANSFORM = "Standard"                # no filmic tone map on diagrams

EXPORT_DIR = "exports"
PRESET_DIR = "blender/presets"
