"""
Bedroom recreation - Blender build script (v2: measured from the Scaniverse scan)
================================================================================
How to use:
  1. Open Blender (4.x recommended, 3.2+ should work).
  2. Scripting tab -> New -> paste this whole file -> Run Script (Alt+P).
  3. In the 3D view press Z -> "Material Preview" to see the colours.

Two modes (see USE_SCAN below):
  USE_SCAN = False  (default) The whole room built from clean modelled shapes - no photo
                    textures - at the real 1:1 size and layout measured from your scan.
  USE_SCAN = True   Imports your Scaniverse .fbx instead, straightens it and lines it up
                    with the clean geometry (scan = what you see, clean shapes = collision).

Re-running is safe: it deletes and rebuilds the "MyRoom" collection only.

Room coordinates (metres), looking down from above:
  X = 0     wardrobe wall          X = 3.12  window wall
  Y = 0     bed wall (AC, posters) Y = 3.56  desk wall
  The entry door is in an alcove behind the wardrobe wall, next to the desk wall
  (X -0.60..0, Y 2.36..3.56). Z = 0 is the floor.
"""

import bpy
import bmesh
import math
import os
import glob
from mathutils import Matrix

# ---------------------------------------------------------------------------
# CONFIG
# ---------------------------------------------------------------------------
USE_SCAN = False

# (scan mode only) Tidy the room: cut the clothes/suitcase/cables, messy bed, desk clutter, dresser-top
# clothes and door coats out of the scan, and put clean modelled versions in their place.
TIDY = True

# The project folder (this script, the scans, and the RoomGame Godot project live here)
PROJECT_DIR = r"C:\Users\thema\Downloads\newgame"

# The room scan (only used when USE_SCAN = True)
SCAN_PATH = os.path.join(PROJECT_DIR, "room_scan.fbx")

# Teddy bear scan: cut off the carpet, smoothed, and sat on the bed. Set ADD_TOY = False to skip.
ADD_TOY = True
TOY_PATH = os.path.join(PROJECT_DIR, "toy_scan.fbx")
TOY_POSITION = (2.20, 0.55, 0.625)  # on the duvet, in front of the pillow (bear's bottom-centre)
TOY_FACING_DEG = 180                # 180 = facing into the room (toward the desks)
TOY_SMOOTH = 0.6                    # 0 = raw scan, 1 = very smooth
TOY_SMOOTH_STEPS = 8
TOY_DECIMATE = 0.3                  # keep 30% of the bear's triangles
TOY_TEXTURE_SIZE = 2048             # shrink the bear's photo texture to this (px) for the game

# How the raw scan is turned to line up with the room (measured from your scan)
SCAN_ROT_DEG = -38.84
SCAN_OFFSET = (1.37, 2.09, 0.0)

# Fraction of the scan's 194k triangles to keep (0.4 -> ~78k). Lower = faster game.
DECIMATE_RATIO = 0.4

# Collision naming for the game engine: "godot" adds -col / -colonly suffixes that
# Godot turns into collision automatically on import. "none" leaves names alone.
COLLISION_STYLE = "godot"

# Where to save the game-ready model: straight into the Godot project folder.
# Set to "" to skip exporting.
EXPORT_GLB = r"C:\Users\thema\Downloads\newgame\RoomGame\room.glb"

# Room measurements (from the scan)
ROOM_W = 3.12         # X: wardrobe wall -> window wall
ROOM_D = 3.56         # Y: bed wall -> desk wall
CEILING_H = 2.40
WALL_T = 0.10

ALCOVE_X0 = -0.60     # entry-door alcove behind the wardrobe wall
ALCOVE_Y0 = 2.36      # ...running from here to the desk wall

WIN_Y0, WIN_Y1 = 0.22, 2.64     # window on the window wall (X = ROOM_W), 4 shutter panels
WIN_Z0, WIN_Z1 = 0.98, 2.18

DOOR_X0, DOOR_X1 = -0.53, 0.29  # entry door on the desk wall (Y = ROOM_D), hinged in the alcove corner
DOOR_H = 2.04

WARD_Y0, WARD_Y1 = 0.67, 2.19   # wardrobe double doors on the wardrobe wall (X = 0)
WARD_H = 2.04

COLLECTION_NAME = "MyRoom"

# In scan mode the clean walls sit a few cm behind the scanned walls so they
# only show through where the scan has holes (avoids flickering/z-fighting).
PAD = 0.03 if USE_SCAN else 0.0

# ---------------------------------------------------------------------------
# Scene / collection setup
# ---------------------------------------------------------------------------
def reset_collection(name):
    coll = bpy.data.collections.get(name)
    if coll:
        def wipe(c):
            for child in list(c.children):
                wipe(child)
                bpy.data.collections.remove(child)
            for obj in list(c.objects):
                bpy.data.objects.remove(obj, do_unlink=True)
        wipe(coll)
    else:
        coll = bpy.data.collections.new(name)
        bpy.context.scene.collection.children.link(coll)
    return coll


# Remove Blender's default startup cube - it sits at the origin, right where the dresser is
for _o in list(bpy.data.objects):
    if (_o.type == "MESH" and _o.name.startswith("Cube") and _o.data.name.startswith("Cube")
            and len(_o.data.vertices) == 8 and max(_o.dimensions) <= 2.01):
        bpy.data.objects.remove(_o, do_unlink=True)

ROOT = reset_collection(COLLECTION_NAME)


def sub_collection(name):
    c = bpy.data.collections.new(name)
    ROOT.children.link(c)
    return c


COL_ARCH = sub_collection("Architecture")   # walls, floor, ceiling
COL_DETAIL = sub_collection("Details")      # doors, window, trim, AC (modelled-only)
COL_FURN = sub_collection("Furniture")      # big furniture (collision in scan mode)
COL_PROPS = sub_collection("Props")         # small stuff (modelled-only)
COL_LIGHT = sub_collection("Lights_Camera")

# ---------------------------------------------------------------------------
# Materials
# ---------------------------------------------------------------------------
def _set_input(bsdf, names, value):
    for n in names:
        if n in bsdf.inputs:
            bsdf.inputs[n].default_value = value
            return


def material(name, color, rough=0.5, metallic=0.0, emission=None, strength=1.0, transmission=0.0):
    m = bpy.data.materials.get(name) or bpy.data.materials.new(name)
    m.use_nodes = True
    bsdf = m.node_tree.nodes.get("Principled BSDF")
    rgba = (*color, 1.0)
    bsdf.inputs["Base Color"].default_value = rgba
    bsdf.inputs["Roughness"].default_value = rough
    bsdf.inputs["Metallic"].default_value = metallic
    if emission:
        _set_input(bsdf, ["Emission Color", "Emission"], (*emission, 1.0))
        _set_input(bsdf, ["Emission Strength"], strength)
    if transmission:
        _set_input(bsdf, ["Transmission Weight", "Transmission"], transmission)
    m.diffuse_color = rgba  # colour shown in Solid viewport mode
    return m


def hexcol(h):
    """'#rrggbb' (normal screen colour) -> the linear RGB Blender expects."""
    h = h.lstrip("#")
    out = []
    for i in (0, 2, 4):
        c = int(h[i:i + 2], 16) / 255.0
        out.append(c / 12.92 if c <= 0.04045 else ((c + 0.055) / 1.055) ** 2.4)
    return tuple(out)


# Natural colours taken from your scan's photo texture (white-balanced against
# the light grey walls in your photos, since the scan was tinted warm by the lamp).
C = hexcol
M = {
    "wall":     material("Wall_Paint", C("#d6d6d2"), 0.9),
    "ceiling":  material("Ceiling_Paint", C("#e4e4e1"), 0.9),
    "trim":     material("Trim_White_Gloss", C("#eceae6"), 0.25),
    "carpet":   material("Carpet_Taupe", C("#7d716b"), 1.0),
    "white":    material("Furniture_White", C("#e6e4df"), 0.45),
    "black":    material("Black_Plastic", C("#29292b"), 0.5),
    "mesh":     material("Chair_Mesh", C("#1e1e20"), 0.8),
    "metal":    material("Brushed_Metal", C("#a9abae"), 0.35, metallic=1.0),
    "handle":   material("Drawer_Handle", C("#2b2a2a"), 0.4, metallic=0.6),
    "sheet":    material("Bed_Sheet_Beige", C("#c4ae94"), 0.9),
    "valance":  material("Bed_Valance_Cream", C("#d8cdbb"), 0.9),
    "duvet":    material("Duvet_White_Blue", C("#c9d0d6"), 0.9),
    "pillow":   material("Pillow_Turquoise", C("#2f9fc4"), 0.8),
    "glass":    material("Window_Glass", C("#e6f0ff"), 0.05, transmission=1.0),
    "sky":      material("Outside_Sky", C("#e6f0ff"), 1.0, emission=hexcol("#e6f0ff"), strength=3.0),
    "screen":   material("Monitor_Screen", C("#2a5bd8"), 0.2, emission=hexcol("#3a6cf0"), strength=2.0),
    "rgb":      material("PC_RGB", C("#e0302a"), 0.3, emission=hexcol("#ff3a2a"), strength=4.0),
    "shade":    material("Lamp_Shade", C("#f3ead2"), 0.8, emission=hexcol("#ffd890"), strength=2.0),
    # Glowing parts the game switches on/off (Godot finds them by these material names)
    "led":      material("Desk_Lamp_LED", C("#fff6e6"), 0.3, emission=hexcol("#fff1d6"), strength=6.0),
    "diffuser": material("Ceiling_Light_Diffuser", C("#f7f7f4"), 0.4, emission=hexcol("#fff8ee"), strength=4.0),
    "bin_pink": material("Bin_Pink", C("#f1b9c6"), 0.6),
    "bin_a":    material("Fabric_Bin_Stripe", C("#a8957c"), 0.9),
    "bin_b":    material("Fabric_Bin_Grey", C("#7b7e86"), 0.9),
    "bin_c":    material("Fabric_Bin_Yellow", C("#d9c77f"), 0.9),
    "bin_d":    material("Fabric_Bin_Blue", C("#8f9bb8"), 0.9),
    "deskmat":  material("Desk_Mat", C("#1c1c1e"), 0.9),
    "keyboard": material("Keyboard_Pink", C("#f0d0d4"), 0.5),
    "laptop":   material("Laptop_Space_Grey", C("#6e6e73"), 0.3, metallic=0.8),
    "laptop_screen": material("Laptop_Screen_Off", C("#111114"), 0.15),
    "plastic":  material("Organiser_Clear_Plastic", C("#e9eaec"), 0.2, transmission=0.35),
    "basket":   material("Basket_Red", C("#b8322e"), 0.6),
    "coat":     material("Coat_Black", C("#1a1a1c"), 0.95),
    "tote":     material("Tote_Bag_Canvas", C("#e8e0cf"), 0.95),
    "bag":      material("Bag_Black", C("#222224"), 0.8),
}

POSTER_MATS = [
    material(f"Poster_{i}", C(h), 0.4)
    for i, h in enumerate([
        "#e2563a", "#3d7fe0", "#9ed43a", "#4fb7e0", "#f2c13a",
        "#68cc80", "#d86ad0", "#3a4aa0", "#f29a4e", "#e6dcc0",
    ])
]

# ---------------------------------------------------------------------------
# Mesh building helper: each Piece becomes ONE object (good for game engines)
# ---------------------------------------------------------------------------
class Piece:
    def __init__(self, name, collection, location=(0, 0, 0)):
        self.name = name
        self.collection = collection
        self.location = location
        self.bm = bmesh.new()
        self.mats = []

    def _mi(self, mat):
        if mat not in self.mats:
            self.mats.append(mat)
        return self.mats.index(mat)

    def box(self, x0, y0, z0, x1, y1, z1, mat):
        """Axis-aligned box between two corners (local coordinates)."""
        x0, x1 = sorted((x0, x1))
        y0, y1 = sorted((y0, y1))
        z0, z1 = sorted((z0, z1))
        co = [(x0, y0, z0), (x1, y0, z0), (x1, y1, z0), (x0, y1, z0),
              (x0, y0, z1), (x1, y0, z1), (x1, y1, z1), (x0, y1, z1)]
        v = [self.bm.verts.new(c) for c in co]
        idx = self._mi(mat)
        for f in [(0, 3, 2, 1), (4, 5, 6, 7), (0, 1, 5, 4),
                  (1, 2, 6, 5), (2, 3, 7, 6), (3, 0, 4, 7)]:
            face = self.bm.faces.new([v[i] for i in f])
            face.material_index = idx
        return self

    def cyl(self, cx, cy, z0, r, h, mat, r_top=None, seg=16):
        """Vertical cylinder (or cone if r_top given) standing on z0."""
        res = bmesh.ops.create_cone(
            self.bm, cap_ends=True, cap_tris=False, segments=seg,
            radius1=r, radius2=r if r_top is None else r_top, depth=h,
            matrix=Matrix.Translation((cx, cy, z0 + h / 2)))
        idx = self._mi(mat)
        for f in {f for v in res["verts"] for f in v.link_faces}:
            f.material_index = idx
        return self

    def finish(self):
        bm = self.bm
        bmesh.ops.recalc_face_normals(bm, faces=bm.faces[:])
        # Simple box-projection UVs (1 UV unit = 1 metre) so textures can be added later
        uv = bm.loops.layers.uv.new("UVMap")
        bm.normal_update()
        for f in bm.faces:
            n = f.normal
            ax = max(range(3), key=lambda i: abs(n[i]))
            for loop in f.loops:
                c = loop.vert.co
                if ax == 0:
                    loop[uv].uv = (c.y, c.z)
                elif ax == 1:
                    loop[uv].uv = (c.x, c.z)
                else:
                    loop[uv].uv = (c.x, c.y)
        mesh = bpy.data.meshes.new(self.name)
        bm.to_mesh(mesh)
        bm.free()
        for m in self.mats:
            mesh.materials.append(m)
        obj = bpy.data.objects.new(self.name, mesh)
        obj.location = self.location
        self.collection.objects.link(obj)
        return obj


# ---------------------------------------------------------------------------
# Architecture: floor, ceiling, walls (incl. door alcove)
# ---------------------------------------------------------------------------
W, D, H, T, p = ROOM_W, ROOM_D, CEILING_H, WALL_T, PAD
AX, AY = ALCOVE_X0, ALCOVE_Y0

# (the scanned floor is removed during clean-up, so this clean carpet sits at exactly 0)
floor = Piece("Floor", COL_ARCH).box(AX, 0, -0.05, W, D, 0, M["carpet"])
floor.box(DOOR_X0, D, -0.05, DOOR_X1, D + T + p, 0, M["trim"])   # threshold under the open doorway
floor.finish()

ceil = Piece("Ceiling", COL_ARCH).box(AX - T, -T, H + p, W + T, D + T, H + 0.05 + p, M["ceiling"])
ceil.box(1.30, 3.05, H + p - 0.01, 1.90, 3.35, H + p, M["white"])   # return-air vent (desk side)
ceil.cyl(2.45, 1.70, H + p - 0.01, 0.12, 0.01, M["white"], seg=24)  # round vent (window side)
ceil.finish()

# Round ceiling light in the middle of the room (glows when the top light is on in the game)
cl_fit = Piece("Ceiling_Light", COL_ARCH)
cl_fit.cyl(W / 2, D / 2, H - 0.015, 0.20, 0.015, M["white"], seg=32)     # mounting ring
cl_fit.cyl(W / 2, D / 2, H - 0.07, 0.17, 0.055, M["diffuser"], r_top=0.19, seg=32)
cl_fit.finish()

Piece("Wall_Bed", COL_ARCH).box(-T, -p, 0, W + T, -T - p, H, M["wall"]).finish()
# Desk wall with the doorway cut out (the door opens into the hallway scan, flat.glb)
wd = Piece("Wall_Desk", COL_ARCH)
wd.box(AX - T, D + p, 0, DOOR_X0, D + T + p, H, M["wall"])
wd.box(DOOR_X1, D + p, 0, W + T, D + T + p, H, M["wall"])
wd.box(DOOR_X0, D + p, DOOR_H, DOOR_X1, D + T + p, H, M["wall"])
wd.finish()
Piece("Wall_Wardrobe", COL_ARCH).box(-p, -T, 0, -T - p, AY, H, M["wall"]).finish()
Piece("Wall_Alcove_Side", COL_ARCH).box(AX - T, AY - p, 0, 0, AY - T - p, H, M["wall"]).finish()
Piece("Wall_Alcove_Back", COL_ARCH).box(AX - p, AY - T, 0, AX - T - p, D + T, H, M["wall"]).finish()

# Window wall built around the window opening
ww = Piece("Wall_Window", COL_ARCH)
x0, x1 = W + p, W + T + p
ww.box(x0, -T, 0, x1, WIN_Y0, H, M["wall"])
ww.box(x0, WIN_Y1, 0, x1, D + T, H, M["wall"])
ww.box(x0, WIN_Y0, 0, x1, WIN_Y1, WIN_Z0, M["wall"])
ww.box(x0, WIN_Y0, WIN_Z1, x1, WIN_Y1, H, M["wall"])
ww.finish()

# ---------------------------------------------------------------------------
# Details (only kept when USE_SCAN is False - the scan already shows these)
# ---------------------------------------------------------------------------
fw = 0.07  # architrave width

# Window: glass, glowing "sky", frame and plantation shutters (on X = W)
win = Piece("Window", COL_DETAIL)
win.box(W + 0.045, WIN_Y0, WIN_Z0, W + 0.05, WIN_Y1, WIN_Z1, M["glass"])
win.box(W + T + 0.3, WIN_Y0 - 0.3, WIN_Z0 - 0.3, W + T + 0.31, WIN_Y1 + 0.3, WIN_Z1 + 0.3, M["sky"])
win.box(W - 0.02, WIN_Y0 - fw, WIN_Z0 - fw, W, WIN_Y0, WIN_Z1 + fw, M["trim"])
win.box(W - 0.02, WIN_Y1, WIN_Z0 - fw, W, WIN_Y1 + fw, WIN_Z1 + fw, M["trim"])
win.box(W - 0.02, WIN_Y0, WIN_Z1, W, WIN_Y1, WIN_Z1 + fw, M["trim"])
win.box(W - 0.03, WIN_Y0, WIN_Z0 - fw, W, WIN_Y1, WIN_Z0, M["trim"])
panels = 4
pw = (WIN_Y1 - WIN_Y0) / panels
stile = 0.035
for i in range(panels):
    py0 = WIN_Y0 + i * pw
    py1 = py0 + pw
    win.box(W + 0.01, py0, WIN_Z0, W + 0.05, py0 + stile, WIN_Z1, M["trim"])
    win.box(W + 0.01, py1 - stile, WIN_Z0, W + 0.05, py1, WIN_Z1, M["trim"])
    win.box(W + 0.01, py0, WIN_Z0, W + 0.05, py1, WIN_Z0 + 0.06, M["trim"])
    win.box(W + 0.01, py0, WIN_Z1 - 0.06, W + 0.05, py1, WIN_Z1, M["trim"])
    z = WIN_Z0 + 0.09
    while z < WIN_Z1 - 0.09:
        win.box(W + 0.015, py0 + stile, z, W + 0.045, py1 - stile, z + 0.055, M["trim"])
        z += 0.075
win.finish()

# Entry door on the desk wall (Y = D) inside the alcove: hinges at DOOR_X0 (alcove corner),
# lever handle near DOOR_X1. Narrow architrave on the corner side, as in the photo.
# The frame stays put; the leaf is its own object with its origin on the hinge line, so the
# game can swing it open (E). It opens into the bedroom, toward -Y, like the real one.
door = Piece("Door_Entry", COL_DETAIL)
door.box(AX, D - 0.02, 0, DOOR_X0, D, DOOR_H + fw, M["trim"])
door.box(DOOR_X1, D - 0.02, 0, DOOR_X1 + fw, D, DOOR_H + fw, M["trim"])
door.box(AX, D - 0.02, DOOR_H, DOOR_X1 + fw, D, DOOR_H + fw, M["trim"])
door.finish()

HINGE = (DOOR_X0, D, 0.0)
leaf = Piece("Door_Leaf", COL_DETAIL, location=HINGE)
def lbox(x0, y0, z0, x1, y1, z1, mat):        # leaf boxes, given in room coordinates
    leaf.box(x0 - HINGE[0], y0 - HINGE[1], z0, x1 - HINGE[0], y1 - HINGE[1], z1, mat)
lbox(DOOR_X0 + 0.005, D - 0.04, 0.01, DOOR_X1 - 0.005, D, DOOR_H - 0.005, M["trim"])
for hz in (0.25, 1.0, 1.75):                                                   # hinges
    lbox(DOOR_X0, D - 0.045, hz, DOOR_X0 + 0.015, D - 0.035, hz + 0.10, M["metal"])
hx = DOOR_X1 - 0.07
for side in (1, -1):                       # lever handle on both faces
    fy0, fy1 = (D - 0.06, D - 0.04) if side == 1 else (D, D + 0.02)
    ly0, ly1 = (D - 0.085, D - 0.065) if side == 1 else (D + 0.025, D + 0.045)
    lbox(hx - 0.03, fy0, 0.97, hx + 0.03, fy1, 1.03, M["metal"])               # rose
    lbox(hx - 0.14, ly0, 0.99, hx, ly1, 1.01, M["metal"])                      # lever
lbox(DOOR_X0 + 0.04, D - 0.07, 1.85, DOOR_X1 - 0.04, D - 0.04, 1.88, M["white"])  # hook rail
lbox(DOOR_X0 + 0.04, D - 0.01, 1.88, DOOR_X0 + 0.07, D - 0.07 + 0.03, DOOR_H - 0.01, M["white"])
lbox(DOOR_X1 - 0.07, D - 0.01, 1.88, DOOR_X1 - 0.04, D - 0.07 + 0.03, DOOR_H - 0.01, M["white"])
door_leaf = leaf.finish()

# Wardrobe double doors on the wardrobe wall (X = 0)
ward = Piece("Wardrobe_Doors", COL_DETAIL)
mid = (WARD_Y0 + WARD_Y1) / 2
ward.box(0, WARD_Y0, 0, 0.04, mid - 0.002, WARD_H, M["trim"])
ward.box(0, mid + 0.002, 0, 0.04, WARD_Y1, WARD_H, M["trim"])
ward.box(0, WARD_Y0 - fw, 0, 0.02, WARD_Y0, WARD_H + fw, M["trim"])
ward.box(0, WARD_Y1, 0, 0.02, WARD_Y1 + fw, WARD_H + fw, M["trim"])
ward.box(0, WARD_Y0 - fw, WARD_H, 0.02, WARD_Y1 + fw, WARD_H + fw, M["trim"])
for hy, sign in ((mid - 0.05, -1), (mid + 0.05, 1)):
    ward.cyl(0.06, hy, 0.98, 0.025, 0.06, M["metal"])
    ward.box(0.055, hy, 1.0, 0.07, hy + sign * 0.12, 1.02, M["metal"])
ward.finish()

# Skirting boards + cornice
trim = Piece("Skirting_Cornice", COL_DETAIL)
sk_h, sk_t, cn = 0.07, 0.015, 0.07
trim.box(0, 0, 0, W, sk_t, sk_h, M["trim"])                              # bed wall
trim.box(DOOR_X1 + fw, D - sk_t, 0, W, D, sk_h, M["trim"])               # desk wall
trim.box(W - sk_t, 0, 0, W, D, sk_h, M["trim"])                          # window wall
trim.box(0, 0, 0, sk_t, WARD_Y0 - fw, sk_h, M["trim"])                   # wardrobe wall
trim.box(0, WARD_Y1 + fw, 0, sk_t, AY, sk_h, M["trim"])
trim.box(AX, AY, 0, 0, AY + sk_t, sk_h, M["trim"])                       # alcove side
trim.box(AX, AY, 0, AX + sk_t, D, sk_h, M["trim"])                       # alcove back
trim.box(0, 0, H - cn, W, cn, H, M["trim"])
trim.box(AX, D - cn, H - cn, W, D, H, M["trim"])
trim.box(W - cn, 0, H - cn, W, D, H, M["trim"])
trim.box(0, 0, H - cn, cn, AY, H, M["trim"])
trim.box(AX, AY, H - cn, 0, AY + cn, H, M["trim"])
trim.box(AX, AY, H - cn, AX + cn, D, H, M["trim"])
trim.finish()

# Air conditioner on the bed wall
ac = Piece("Air_Conditioner", COL_DETAIL)
ac.box(1.12, 0, 2.00, 1.95, 0.22, 2.30, M["white"])
ac.box(1.16, 0.22, 2.03, 1.91, 0.225, 2.07, M["black"])
ac.finish()

# ---------------------------------------------------------------------------
# Furniture (visible when modelled, invisible collision in scan mode)
# ---------------------------------------------------------------------------
# Single bed against the bed wall, head at the window - neatly made
bed = Piece("Bed", COL_FURN)
bed.box(1.05, 0, 0, 3.02, 0.98, 0.36, M["valance"])
bed.box(1.05, 0, 0.36, 3.02, 0.98, 0.58, M["sheet"])
bed.box(1.03, -0.0, 0.30, 2.54, 1.00, 0.63, M["duvet"])     # duvet draped over the sides
bed.box(2.37, -0.0, 0.58, 2.54, 1.00, 0.65, M["sheet"])     # folded-back top sheet
bed.box(2.60, 0.13, 0.58, 2.98, 0.85, 0.70, M["pillow"])    # pillow, centred
bed.finish()

# 4-drawer dresser in the bed-wall / wardrobe-wall corner, drawers facing +Y
dr = Piece("Dresser", COL_FURN)
dx0, dx1, dd, dh = 0.01, 0.77, 0.45, 1.00   # 0.76 wide; dd = body depth (fronts + handles add ~4 cm)
dr.box(dx0, 0, 0, dx1, dd, dh - 0.03, M["white"])
dr.box(dx0 - 0.02, 0, dh - 0.03, dx1 + 0.02, dd + 0.03, dh, M["white"])
dr.box(dx0, dd, 0, dx0 + 0.04, dd + 0.02, dh - 0.03, M["white"])
dr.box(dx1 - 0.04, dd, 0, dx1, dd + 0.02, dh - 0.03, M["white"])
drawer_h = (dh - 0.13) / 4
cx = (dx0 + dx1) / 2
for i in range(4):
    z0 = 0.08 + i * drawer_h
    dr.box(dx0 + 0.05, dd, z0 + 0.01, dx1 - 0.05, dd + 0.02, z0 + drawer_h - 0.01, M["white"])
    dr.box(cx - 0.07, dd + 0.02, z0 + drawer_h * 0.6, cx + 0.07, dd + 0.035, z0 + drawer_h * 0.6 + 0.015, M["handle"])
dr.finish()

# 2x2 cube shelf against the window wall (openings face -X), next to the bed
sh = Piece("Cube_Shelf", COL_FURN)
sy0, sy1, sd, s_h, t = 1.10, 1.87, 0.39, 0.77, 0.035
sx0 = W - sd
sh.box(sx0, sy0, 0, W, sy0 + t, s_h, M["white"])
sh.box(sx0, sy1 - t, 0, W, sy1, s_h, M["white"])
sh.box(sx0, sy0, 0, W, sy1, t, M["white"])
sh.box(sx0, sy0, s_h - t, W, sy1, s_h, M["white"])
smy, smz = (sy0 + sy1) / 2, s_h / 2
sh.box(sx0, smy - t / 2, 0, W, smy + t / 2, s_h, M["white"])
sh.box(sx0, sy0, smz - t / 2, W, sy1, smz + t / 2, M["white"])
sh.box(W - 0.01, sy0, 0, W, sy1, s_h, M["white"])
for (by0, by1, bz0, bz1, m) in [
    (smy + t / 2, sy1 - t, t, smz - t / 2, M["bin_c"]),
    (sy0 + t, smy - t / 2, t, smz - t / 2, M["bin_d"]),
    (smy + t / 2, sy1 - t, smz + t / 2, s_h - t, M["bin_a"]),
    (sy0 + t, smy - t / 2, smz + t / 2, s_h - t, M["bin_b"]),
]:
    sh.box(sx0 + 0.01, by0 + 0.01, bz0, W - 0.03, by1 - 0.01, bz1 - 0.01, m)
sh.finish()


def desk(name, x0, x1, depth):
    d = Piece(name, COL_FURN)
    y0 = D - depth
    d.box(x0, y0, 0.69, x1, D, 0.72, M["white"])
    inset = 0.06
    for lx, ly in ((x0 + inset, y0 + inset), (x1 - inset, y0 + inset),
                   (x0 + inset, D - inset), (x1 - inset, D - inset)):
        d.cyl(lx, ly, 0.0, 0.025, 0.69, M["white"])
    return d.finish()


desk("Desk_Main", 1.70, 3.10, 0.80)    # PC desk, window end
desk("Desk_Small", 0.70, 1.70, 0.60)   # near the door alcove


def office_chair(name, cx, cy, facing_deg, headrest):
    """Simple office chair; local +X is the direction the person faces."""
    ch = Piece(name, COL_FURN, location=(cx, cy, 0))
    for a in range(5):
        ang = math.radians(a * 72)
        ex, ey = math.cos(ang) * 0.30, math.sin(ang) * 0.30
        for s in range(6):
            px, py = ex * s / 6, ey * s / 6
            ch.box(px - 0.025, py - 0.025, 0.06, px + 0.025, py + 0.025, 0.10, M["black"])
        ch.cyl(ex, ey, 0.0, 0.03, 0.06, M["black"], seg=10)
    ch.cyl(0, 0, 0.10, 0.03, 0.33, M["black"])
    ch.box(-0.25, -0.25, 0.43, 0.25, 0.25, 0.50, M["black"])
    ch.box(-0.30, -0.23, 0.55, -0.26, 0.23, 1.05, M["mesh"])
    ch.box(-0.30, -0.03, 0.43, -0.25, 0.03, 0.56, M["black"])
    for side in (-1, 1):
        ch.box(-0.15, side * 0.27 - 0.03, 0.50, -0.10, side * 0.27 + 0.03, 0.66, M["black"])
        ch.box(-0.20, side * 0.27 - 0.035, 0.66, 0.12, side * 0.27 + 0.035, 0.69, M["black"])
    if headrest:
        ch.box(-0.31, -0.14, 1.12, -0.27, 0.14, 1.30, M["mesh"])
        ch.box(-0.30, -0.02, 1.05, -0.28, 0.02, 1.12, M["black"])
    obj = ch.finish()
    obj.rotation_euler[2] = math.radians(facing_deg)
    return obj


office_chair("Chair_Gaming", 2.45, 2.45, 90, headrest=True)   # tucked in at the PC desk
office_chair("Chair_Small", 1.20, 2.70, 90, headrest=False)

# ---------------------------------------------------------------------------
# Props (modelled-only)
# ---------------------------------------------------------------------------
top = 0.72
pc = Piece("PC_Setup", COL_PROPS)
pc.box(1.73, D - 0.47, top, 1.96, D - 0.03, top + 0.46, M["black"])            # tower
pc.box(1.96, D - 0.44, top + 0.05, 1.965, D - 0.06, top + 0.41, M["rgb"])      # glass side glow
pc.box(2.40, D - 0.20, top, 2.50, D - 0.12, top + 0.01, M["black"])            # monitor foot
pc.box(2.43, D - 0.17, top, 2.47, D - 0.15, top + 0.15, M["black"])            # neck
pc.box(2.14, D - 0.20, top + 0.10, 2.76, D - 0.17, top + 0.47, M["black"])     # monitor
pc.box(2.155, D - 0.205, top + 0.115, 2.745, D - 0.20, top + 0.455, M["screen"])
pc.box(2.00, D - 0.62, top, 2.95, D - 0.20, top + 0.003, M["deskmat"])
pc.box(2.25, D - 0.50, top + 0.003, 2.65, D - 0.36, top + 0.03, M["keyboard"])
pc.box(2.80, D - 0.45, top + 0.003, 2.86, D - 0.39, top + 0.04, M["black"])
pc.finish()

# LED desk lamp standing on the PC tower, short arm reaching RIGHT (toward the window /
# over the PC desk), with a glowing LED strip under the head (the game turns it on/off).
dl = Piece("Desk_Lamp", COL_PROPS)
lb_x, lb_y, lb_z = 1.84, D - 0.20, top + 0.46          # base on top of the tower
arm_end = lb_x + 0.30                                   # arm length 30 cm
dl.cyl(lb_x, lb_y, lb_z, 0.06, 0.02, M["white"], seg=24)                 # base
dl.cyl(lb_x, lb_y, lb_z + 0.02, 0.012, 0.36, M["white"])                 # upright
dl.cyl(lb_x, lb_y, lb_z + 0.37, 0.018, 0.03, M["white"])                 # joint
dl.box(lb_x, lb_y - 0.012, lb_z + 0.38, arm_end, lb_y + 0.012, lb_z + 0.40, M["white"])          # arm
dl.box(arm_end - 0.16, lb_y - 0.03, lb_z + 0.365, arm_end + 0.02, lb_y + 0.03, lb_z + 0.40, M["white"])  # head
dl.box(arm_end - 0.145, lb_y - 0.018, lb_z + 0.360, arm_end + 0.005, lb_y + 0.018, lb_z + 0.365, M["led"])
dl.finish()

lamp = Piece("Table_Lamp", COL_PROPS)
lamp.cyl(W - 0.20, 1.25, s_h, 0.08, 0.02, M["white"], seg=24)
lamp.cyl(W - 0.20, 1.25, s_h + 0.02, 0.008, 0.40, M["white"])
lamp.cyl(W - 0.20, 1.25, s_h + 0.30, 0.16, 0.22, M["shade"], r_top=0.13, seg=32)
lamp.finish()

Piece("Humidifier", COL_PROPS).cyl(W - 0.20, 1.72, s_h, 0.07, 0.22, M["white"], seg=24).finish()

# Laptop: open, in the middle of the small desk, screen facing the chair
lp = Piece("Laptop", COL_PROPS)
lx0, lx1, ly0, ly1 = 1.045, 1.355, 3.02, 3.24
lp.box(lx0, ly0, top, lx1, ly1, top + 0.015, M["laptop"])                    # base
lp.box(lx0 + 0.03, ly0 + 0.03, top + 0.015, lx1 - 0.03, ly0 + 0.13, top + 0.017, M["black"])  # keys
lp.box(lx0, ly1, top + 0.015, lx1, ly1 + 0.008, top + 0.225, M["laptop"])   # lid
lp.box(lx0 + 0.012, ly1 - 0.001, top + 0.025, lx1 - 0.012, ly1, top + 0.215, M["laptop_screen"])
lp.finish()

# Plastic drawer organiser with the red basket on top - small desk, door end, against the wall
org = Piece("Drawer_Organiser", COL_PROPS)
ox0, ox1, oy0, oy1 = 0.76, 1.02, D - 0.37, D - 0.02
org.box(ox0, oy0, top, ox1, oy1, top + 0.24, M["white"])                      # frame
rows_o, cols_o = 3, 2
dw, dh2 = (ox1 - ox0 - 0.02) / cols_o, (0.24 - 0.02) / rows_o
for r in range(rows_o):
    for c in range(cols_o):
        x0_ = ox0 + 0.01 + c * dw
        z0_ = top + 0.01 + r * dh2
        org.box(x0_ + 0.004, oy0 - 0.012, z0_ + 0.004, x0_ + dw - 0.004, oy0, z0_ + dh2 - 0.004, M["plastic"])
        org.box(x0_ + dw / 2 - 0.02, oy0 - 0.018, z0_ + dh2 / 2 - 0.005,
                x0_ + dw / 2 + 0.02, oy0 - 0.012, z0_ + dh2 / 2 + 0.005, M["white"])   # pull
bt = top + 0.24
org.box(ox0 + 0.01, oy0 + 0.04, bt, ox1 - 0.01, oy1 - 0.04, bt + 0.012, M["basket"])   # basket floor
org.box(ox0 + 0.01, oy0 + 0.04, bt, ox0 + 0.02, oy1 - 0.04, bt + 0.08, M["basket"])    # basket sides
org.box(ox1 - 0.02, oy0 + 0.04, bt, ox1 - 0.01, oy1 - 0.04, bt + 0.08, M["basket"])
org.box(ox0 + 0.01, oy0 + 0.04, bt, ox1 - 0.01, oy0 + 0.05, bt + 0.08, M["basket"])
org.box(ox0 + 0.01, oy1 - 0.05, bt, ox1 - 0.01, oy1 - 0.04, bt + 0.08, M["basket"])
org.finish()

# Clothes on the over-door hook rail: two long black coats, then a canvas tote with a black bag
# (they hang off the door face and stick out into the room, toward -Y)
cl = Piece("Door_Clothes", COL_PROPS)
fy = D - 0.04             # door face
for i in range(6):        # hooks along the rail
    hxk = DOOR_X0 + 0.10 + i * (DOOR_X1 - DOOR_X0 - 0.20) / 5
    cl.box(hxk - 0.008, fy - 0.06, 1.80, hxk + 0.008, fy - 0.03, 1.86, M["white"])
    cl.box(hxk - 0.008, fy - 0.065, 1.80, hxk + 0.008, fy - 0.05, 1.83, M["white"])


def coat(x0, x1, z_bottom, depth, out):
    w = x1 - x0
    cl.box(x0 + w * 0.22, fy - out, 1.70, x1 - w * 0.22, fy - out - depth * 0.8, 1.83, M["coat"])  # shoulders
    cl.box(x0, fy - out, z_bottom, x1, fy - out - depth, 1.72, M["coat"])                         # body
    cl.box(x0 - 0.03, fy - out - depth * 0.2, 1.05, x0, fy - out - depth * 0.8, 1.68, M["coat"])  # sleeves
    cl.box(x1, fy - out - depth * 0.2, 1.05, x1 + 0.03, fy - out - depth * 0.8, 1.68, M["coat"])


# Coats near the hinge side, tote + black bag further along (matches the photo and scan)
coat(-0.46, -0.17, 0.95, 0.08, 0.005)          # long coat
coat(-0.30, -0.03, 1.05, 0.09, 0.07)           # second coat, hanging in front
cl.box(-0.24, fy - 0.07, 1.76, -0.08, fy - 0.17, 1.88, M["coat"])   # its hood
cl.box(0.01, fy - 0.005, 1.22, 0.23, fy - 0.05, 1.70, M["bag"])      # black bag behind
cl.box(0.00, fy - 0.05, 1.30, 0.20, fy - 0.10, 1.64, M["tote"])      # canvas tote
for sx in (0.03, 0.15):                                              # tote straps up to the hook
    cl.box(sx, fy - 0.06, 1.64, sx + 0.02, fy - 0.075, 1.84, M["tote"])
door_clothes = cl.finish()
door_clothes.parent = door_leaf               # the coats swing with the door
door_clothes.matrix_parent_inverse = Matrix.Translation(HINGE).inverted()

post = Piece("Posters", COL_PROPS)
cols, rows, cw, chh, gap = 3, 4, 0.20, 0.10, 0.02
n = 0
for r in range(rows):
    for c in range(cols):
        if r == rows - 1 and c == cols - 1:
            continue
        x = 0.15 + c * (cw + gap)
        z = 2.01 - r * (chh + gap)
        post.box(x, 0, z - chh, x + cw, 0.003, z, POSTER_MATS[n % len(POSTER_MATS)])
        n += 1
post.finish()

# Rubbish bin tucked under the PC desk, toward the back, clear of the legs and chair
BIN_X, BIN_Y = 2.05, 3.28
Piece("Bin", COL_PROPS).cyl(BIN_X, BIN_Y, 0, 0.15, 0.32, M["white"], r_top=0.17, seg=24) \
    .cyl(BIN_X, BIN_Y, 0.30, 0.172, 0.03, M["bin_pink"], seg=24).finish()

# ---------------------------------------------------------------------------
# Lights + first-person camera
# ---------------------------------------------------------------------------
def add_light(name, kind, loc, energy, color=(1, 1, 1), size=None, rot=None):
    data = bpy.data.lights.new(name, kind)
    data.energy = energy
    data.color = color
    if size is not None and kind == "AREA":
        data.size = size
    obj = bpy.data.objects.new(name, data)
    obj.location = loc
    if rot:
        obj.rotation_euler = rot
    COL_LIGHT.objects.link(obj)
    return obj


add_light("Ceiling_Light", "AREA", (W / 2, D / 2, H - 0.02), 150, size=0.4)
add_light("Lamp_Bulb", "POINT", (W - 0.20, 1.25, s_h + 0.38), 25, color=(1.0, 0.8, 0.5))
add_light("Window_Daylight", "AREA", (W + 0.3, (WIN_Y0 + WIN_Y1) / 2, (WIN_Z0 + WIN_Z1) / 2), 200,
          color=(0.85, 0.92, 1.0), size=1.9, rot=(0, math.radians(90), 0))

cam_data = bpy.data.cameras.new("Player_Eye")
cam_data.lens = 18
cam = bpy.data.objects.new("Player_Eye", cam_data)
cam.location = (0.35, 2.0, 1.6)                                  # by the wardrobe
cam.rotation_euler = (math.radians(85), 0, math.radians(-90))    # looking at the window
COL_LIGHT.objects.link(cam)
bpy.context.scene.camera = cam

# ---------------------------------------------------------------------------
# Scan mode: import, align, simplify, and turn clean geometry into collision
# ---------------------------------------------------------------------------
def find_scan():
    if SCAN_PATH:
        return SCAN_PATH
    downloads = os.path.join(os.path.expanduser("~"), "Downloads")
    files = glob.glob(os.path.join(downloads, "Scaniverse*.fbx"))
    if not files:
        raise FileNotFoundError("No Scaniverse*.fbx in Downloads - set SCAN_PATH at the top of the script.")
    return max(files, key=os.path.getmtime)


def import_scan():
    path = find_scan()
    print("Importing scan:", path)
    before = set(bpy.data.objects)
    bpy.ops.import_scene.fbx(filepath=path)
    new = [o for o in bpy.data.objects if o not in before]
    col = sub_collection("Scan")
    meshes = []
    for o in new:
        for c in list(o.users_collection):
            c.objects.unlink(o)
        if o.type != "MESH":
            bpy.data.objects.remove(o, do_unlink=True)
            continue
        col.objects.link(o)
        meshes.append(o)
    if not meshes:
        raise RuntimeError("The FBX contained no mesh.")

    # Guard against unit mix-ups (scan should be ~3-5 m across)
    biggest = max(max(o.dimensions) for o in meshes)
    s = 0.01 if biggest > 50 else (100.0 if biggest < 0.5 else 1.0)

    align = (Matrix.Translation(SCAN_OFFSET)
             @ Matrix.Rotation(math.radians(SCAN_ROT_DEG), 4, "Z")
             @ Matrix.Scale(s, 4))
    for i, o in enumerate(meshes):
        o.parent = None
        o.data.transform(align @ o.matrix_world)   # bake transform into the mesh
        o.matrix_world = Matrix.Identity(4)
        o.name = "Scan_Visual" if i == 0 else f"Scan_Visual_{i}"
        dec = o.modifiers.new("Decimate", "DECIMATE")
        dec.ratio = DECIMATE_RATIO
    print(f"Scan aligned ({len(meshes)} mesh, unit scale x{s}), decimate ratio {DECIMATE_RATIO}")
    return meshes


# Boxes (x0, y0, z0, x1, y1, z1) in room coordinates. Scan faces whose centre is
# inside a CLUTTER zone are deleted, unless they are inside a KEEP zone.
_M = 0.08  # stay this far off the walls so the scanned walls/wardrobe/shutters survive
CLUTTER_ZONES = [
    (AX - 0.3, -0.3, -1.0, W + 0.3, D + 0.3, 0.04),               # whole scanned floor
    (_M, _M, 0.04, W - _M, D - _M, 1.45),                          # floor clutter, chairs, suitcase
    (AX + _M, AY + _M, 0.04, _M, D - _M, 1.45),                    # floor of the door alcove
    (1.10, -0.10, 0.04, W + 0.10, 1.00, 0.93),                     # messy bed
    (-0.10, -0.10, 0.04, 0.92, 0.55, 1.45),                        # dresser + clothes on top
    (0.65, D - 0.75, 0.04, W + 0.10, D + 0.10, 1.75),              # desks + everything on them
    (AX - 0.10, D - 0.50, 0.04, DOOR_X1 + 0.05, D + 0.10, 2.05),   # coats hanging on the door
    (W - 0.20, 1.95, 0.04, W + 0.30, D + 0.10, 0.93),              # stuff between shelf and desk
]
KEEP_ZONES = [
    (W - 0.48, 1.02, 0.04, W + 0.30, 1.95, 1.35),                  # cube shelf + lamp + humidifier
]


def _inside(c, z):
    return z[0] <= c.x <= z[3] and z[1] <= c.y <= z[4] and z[2] <= c.z <= z[5]


def tidy_scan(obj):
    bm = bmesh.new()
    bm.from_mesh(obj.data)
    kill = []
    for f in bm.faces:
        c = f.calc_center_median()
        if any(_inside(c, z) for z in CLUTTER_ZONES) and not any(_inside(c, z) for z in KEEP_ZONES):
            kill.append(f)
    before = len(bm.faces)
    bmesh.ops.delete(bm, geom=kill, context="FACES")
    loose = [v for v in bm.verts if not v.link_faces]
    bmesh.ops.delete(bm, geom=loose, context="VERTS")
    bm.to_mesh(obj.data)
    bm.free()
    obj.data.update()
    print(f"Tidy: removed {len(kill)} of {before} scan faces")


def mark_collision(obj, visible):
    if COLLISION_STYLE == "godot":
        obj.name = obj.name + ("-col" if visible else "-colonly")
    if not visible:
        obj.display_type = "WIRE"
        obj.hide_render = True


if USE_SCAN:
    # What stays modelled on top of the scan
    keep_detail = {"Door_Entry"} if TIDY else set()
    keep_props = {"PC_Setup", "Desk_Lamp", "Bin"} if TIDY else set()
    for c, keep in ((COL_DETAIL, keep_detail), (COL_PROPS, keep_props)):
        for o in list(c.objects):
            if o.name not in keep:
                bpy.data.objects.remove(o, do_unlink=True)
    for o in COL_ARCH.objects:       # visible: patches the scan's holes + collision
        mark_collision(o, visible=True)
    for o in COL_FURN.objects:
        # tidy mode: the clean bed/desks/dresser/chairs replace the messy scanned ones
        mark_collision(o, visible=TIDY)
    for o in bpy.data.objects:        # the scan already has the lamp glow baked in
        if o.name in ("Lamp_Bulb",):
            bpy.data.objects.remove(o, do_unlink=True)
    for scan_obj in import_scan():
        if TIDY:
            tidy_scan(scan_obj)
else:
    # Modelled mode: everything is visible, and the room + furniture are solid in the game
    # (Details too, so you can't jump out through the window opening)
    for o in list(COL_ARCH.objects) + list(COL_DETAIL.objects) + list(COL_FURN.objects):
        mark_collision(o, visible=True)

# Show colours/textures in the viewport
for area in bpy.context.screen.areas if bpy.context.screen else []:
    if area.type == "VIEW_3D":
        area.spaces.active.shading.type = "MATERIAL"


# ---------------------------------------------------------------------------
# Teddy bear: import the scan, cut it off the carpet, smooth it, sit it on the bed
# ---------------------------------------------------------------------------
def import_toy():
    if not os.path.exists(TOY_PATH):
        print("Toy scan not found:", TOY_PATH)
        return None
    before = set(bpy.data.objects)
    bpy.ops.import_scene.fbx(filepath=TOY_PATH)
    new = [o for o in bpy.data.objects if o not in before]
    toy = None
    for o in new:
        for c_ in list(o.users_collection):
            c_.objects.unlink(o)
        if o.type == "MESH" and toy is None:
            toy = o
        else:
            bpy.data.objects.remove(o, do_unlink=True)
    if toy is None:
        return None
    col = sub_collection("Toy")
    col.objects.link(toy)

    s = 0.01 if max(toy.dimensions) > 50 else 1.0          # unit guard
    toy.data.transform(Matrix.Scale(s, 4) @ toy.matrix_world)
    toy.matrix_world = Matrix.Identity(4)

    bm = bmesh.new()
    bm.from_mesh(toy.data)
    # The scan is split along its texture seams; weld them so the bear is one piece
    # (colours are stored per corner, so they're kept).
    bmesh.ops.remove_doubles(bm, verts=bm.verts, dist=0.0005)
    bm.faces.ensure_lookup_table()
    centres = [f.calc_center_median() for f in bm.faces]

    # The carpet is at z ~ 0. Find the bear: stuff standing up off the floor near the middle.
    above = [c_ for c_ in centres if c_.z > 0.03 and math.hypot(c_.x, c_.y) < 0.4]
    above.sort(key=lambda v: v.x)
    cx = above[len(above) // 2].x
    above.sort(key=lambda v: v.y)
    cy = above[len(above) // 2].y
    ground = min(c_.z for c_ in centres)

    # 1) cut away the carpet and anything far from the bear
    kill = [f for f, c_ in zip(bm.faces, centres)
            if c_.z < ground + 0.025 or math.hypot(c_.x - cx, c_.y - cy) > 0.20]
    bmesh.ops.delete(bm, geom=kill, context="FACES")

    # 2) keep only the biggest connected piece (drops floating specks and carpet fluff)
    bm.faces.ensure_lookup_table()
    seen, islands = set(), []
    for f in bm.faces:
        if f.index in seen:
            continue
        stack, island = [f], []
        seen.add(f.index)
        while stack:
            cur = stack.pop()
            island.append(cur)
            for e in cur.edges:
                for nb in e.link_faces:
                    if nb.index not in seen:
                        seen.add(nb.index)
                        stack.append(nb)
        islands.append(island)
    islands.sort(key=len, reverse=True)
    junk = [f for isl in islands[1:] for f in isl]
    bmesh.ops.delete(bm, geom=junk, context="FACES")
    bmesh.ops.delete(bm, geom=[v for v in bm.verts if not v.link_faces], context="VERTS")

    # 3) move so the bear's bottom-centre is at the origin
    xs = [v.co.x for v in bm.verts]; ys = [v.co.y for v in bm.verts]; zs = [v.co.z for v in bm.verts]
    shift = (-(min(xs) + max(xs)) / 2, -(min(ys) + max(ys)) / 2, -min(zs))
    bmesh.ops.translate(bm, verts=bm.verts, vec=shift)

    # 3b) close the open bottom (the scanner never saw under Bob - he was sitting on the carpet)
    #     with soft tan fur, slightly domed, plus the two embroidered paw pads on his feet.
    fur_idx = len(toy.data.materials)
    toy.data.materials.append(material("Bob_Bottom_Fur", C("#c4935f"), 0.95))
    pad_idx = len(toy.data.materials)
    toy.data.materials.append(material("Bob_Paw_Pads", C("#b8894a"), 0.6, metallic=0.3))
    boundary = [e for e in bm.edges if e.is_boundary]
    filled = bmesh.ops.holes_fill(bm, edges=boundary, sides=0)["faces"]
    if filled:
        poked = bmesh.ops.poke(bm, faces=filled)          # fan each patch to a centre point
        for f in poked["faces"]:
            f.material_index = fur_idx
            f.smooth = True
        for v in poked["verts"]:                          # dome the middle very slightly
            v.co.z = max(0.0, v.co.z - 0.004)
    # paw pads: flat ovals under the two front feet (Bob faces -Y here)
    bm.verts.index_update()
    first_pad_vert = len(bm.verts)          # pads are added last, so their verts come after this
    for side in (-1, 1):
        pad = bmesh.ops.create_circle(bm, cap_ends=True, cap_tris=False, segments=12, radius=0.02,
                                      matrix=Matrix.Translation((side * 0.045, -0.045, -0.001))
                                      @ Matrix.Scale(1.25, 4, (0, 1, 0)))
        pad_faces = list({f for v in pad["verts"] for f in v.link_faces})
        bmesh.ops.reverse_faces(bm, faces=pad_faces)       # face downwards
        for f in pad_faces:
            f.material_index = pad_idx
    # cream pom-pom tail low on his back (Bob's back faces +Y here)
    tail_idx = len(toy.data.materials)
    toy.data.materials.append(material("Bob_Tail", C("#efe6cf"), 1.0))
    tail_z = 0.035
    bm.verts.ensure_lookup_table()
    back_pts = [v.co.y for v in bm.verts[:first_pad_vert] if abs(v.co.x) < 0.03 and abs(v.co.z - tail_z) < 0.02]
    back_y = max(back_pts) if back_pts else 0.075
    tail = bmesh.ops.create_uvsphere(bm, u_segments=16, v_segments=10, radius=0.022,
                                     matrix=Matrix.Translation((0.0, back_y - 0.004, tail_z)))
    for f in {f for v in tail["verts"] for f in v.link_faces}:
        f.material_index = tail_idx
        f.smooth = True
    print(f"Bob: closed {len(filled)} hole(s) underneath, added paw pads and his pom-pom tail")

    bm.to_mesh(toy.data)
    bm.free()
    toy.data.update()
    # everything except the paw pads gets smoothed (so the pads keep their shape)
    smooth_group = toy.vertex_groups.new(name="Smooth")
    smooth_group.add(list(range(first_pad_vert)), 1.0, "REPLACE")
    for poly in toy.data.polygons:
        poly.use_smooth = True                               # soft shading, no faceting

    # 4) smooth out the scan noise, then lighten it for the game
    sm = toy.modifiers.new("Smooth", "SMOOTH")
    sm.factor = TOY_SMOOTH
    sm.iterations = TOY_SMOOTH_STEPS
    sm.vertex_group = "Smooth"
    dec = toy.modifiers.new("Decimate", "DECIMATE")
    dec.ratio = TOY_DECIMATE

    # 5) shrink the photo texture so the game file stays small
    for slot in toy.material_slots:
        if slot.material and slot.material.use_nodes:
            for node in slot.material.node_tree.nodes:
                img = getattr(node, "image", None)
                if img and max(img.size) > TOY_TEXTURE_SIZE:
                    img.scale(TOY_TEXTURE_SIZE, TOY_TEXTURE_SIZE)
                    img.pack()
                if img and EXPORT_GLB:
                    # Also save it next to room.glb as a PNG: the game loads it from there,
                    # because Godot can't decode the JPEG Blender embeds in the .glb.
                    try:
                        tmp = img.copy()
                        tmp.file_format = "PNG"
                        tmp.save(filepath=os.path.join(os.path.dirname(EXPORT_GLB), "bear_texture.png"))
                        bpy.data.images.remove(tmp)
                    except Exception as err:
                        print("Couldn't save bear_texture.png (the existing one will be used):", err)
            bsdf = slot.material.node_tree.nodes.get("Principled BSDF")
            if bsdf:
                bsdf.inputs["Roughness"].default_value = 0.9     # soft, fuzzy - no shiny highlights

    toy.name = "Bob"   # the teddy bear
    toy.location = TOY_POSITION
    toy.rotation_euler = (0, 0, math.radians(TOY_FACING_DEG))
    print(f"Teddy bear added: {len(toy.data.polygons)} faces before decimate, size {tuple(round(d, 2) for d in toy.dimensions)}")
    return toy


if ADD_TOY:
    import_toy()

# ---------------------------------------------------------------------------
# Optional export for a game engine (Godot / Unity / Unreal all import .glb)
# ---------------------------------------------------------------------------
if EXPORT_GLB:
    bpy.ops.object.select_all(action="DESELECT")
    for o in ROOT.all_objects:
        if o.type == "MESH":
            o.select_set(True)
    bpy.ops.export_scene.gltf(filepath=EXPORT_GLB, use_selection=True,
                              export_format="GLB", export_apply=True)
    print("Exported to", EXPORT_GLB)

print(f"Room built: {len(ROOT.all_objects)} objects in '{COLLECTION_NAME}' (scan mode: {USE_SCAN})")
