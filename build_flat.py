"""
The rest of the flat - Blender build script (clean modelled version)
=====================================================================
Builds the hallway, stairs, toilet, bathroom, living room and balcony as clean modelled
shapes (like build_room.py does for the bedroom), laid out 1:1 from the Scaniverse scan
room2_scan.fbx (measured / lined up in scans/flat.json, scans/measure_room2/), and exports
RoomGame/flat.glb.

Run headless:  blender -b --factory-startup --python build_flat.py
or in Blender: Scripting tab -> open this file -> Run Script (rebuilds the "MyFlat" collection).

Coordinates are the bedroom's (metres, Z up): bedroom X 0..3.12, Y 0..3.56, bedroom door in
the desk wall at X -0.53..0.29 (hallway face of that wall at Y 3.66). Godot = (x, z, -y).

Names the game uses:
  *-col             solid in Godot (walls, floors, big furniture)
  Flat_Light_N      empties: a ceiling light goes here (main.gd _make_flat_lights)
  Ceiling_Light_Diffuser   material: the lamp shades glow with the top light (mood 1)
  Chair_*           E sits you down here (origin = the seat; local +X = the way you face,
                    so sofas / armchairs have rot 90, the desk chair rot -90)
  Door_*            doors E opens (origin on the hinge; main.gd DOOR_SWING says how far)
  Flat_TV_Screen / Flat_PC_Screen   materials: the game shows the TV / computer picture there
  Flat_Stair_Ramp   invisible slope over the stairs that you actually walk on (main.gd hides it)
"""

import bpy
import bmesh
import math
import os
import random
from mathutils import Matrix

PROJECT_DIR = r"C:\Users\thema\Downloads\newgame"
EXPORT_GLB = os.path.join(PROJECT_DIR, "RoomGame", "flat.glb")
COLLECTION_NAME = "MyFlat"

H = 2.42          # ceiling height
T = 0.10          # wall thickness
random.seed(7)

# ---------------------------------------------------------------------------
# Scene setup
# ---------------------------------------------------------------------------
for _o in list(bpy.data.objects):
    if (_o.type == "MESH" and _o.name.startswith("Cube") and len(_o.data.vertices) == 8):
        bpy.data.objects.remove(_o, do_unlink=True)


def reset_collection(name):
    coll = bpy.data.collections.get(name)
    if coll:
        for obj in list(coll.all_objects):
            bpy.data.objects.remove(obj, do_unlink=True)
        for child in list(coll.children_recursive):
            bpy.data.collections.remove(child)
    else:
        coll = bpy.data.collections.new(name)
        bpy.context.scene.collection.children.link(coll)
    return coll


ROOT = reset_collection(COLLECTION_NAME)


# ---------------------------------------------------------------------------
# Materials (screen colours, converted to linear)
# ---------------------------------------------------------------------------
def hexcol(h):
    h = h.lstrip("#")
    out = []
    for i in (0, 2, 4):
        c = int(h[i:i + 2], 16) / 255.0
        out.append(c / 12.92 if c <= 0.04045 else ((c + 0.055) / 1.055) ** 2.4)
    return tuple(out)


def material(name, hex_colour, rough=0.6, metallic=0.0, emission=None, strength=1.0, alpha=1.0):
    m = bpy.data.materials.get(name) or bpy.data.materials.new(name)
    m.use_nodes = True
    bsdf = m.node_tree.nodes.get("Principled BSDF")
    rgba = (*hexcol(hex_colour), 1.0)
    bsdf.inputs["Base Color"].default_value = rgba
    bsdf.inputs["Roughness"].default_value = rough
    bsdf.inputs["Metallic"].default_value = metallic
    if emission:
        for n in ("Emission Color", "Emission"):
            if n in bsdf.inputs:
                bsdf.inputs[n].default_value = (*hexcol(emission), 1.0)
                break
        bsdf.inputs["Emission Strength"].default_value = strength
    if alpha < 1.0:
        bsdf.inputs["Alpha"].default_value = alpha
        if hasattr(m, "surface_render_method"):
            m.surface_render_method = "BLENDED"
        elif hasattr(m, "blend_method"):
            m.blend_method = "BLEND"
    m.diffuse_color = rgba
    return m


M = {
    "wall":      material("Flat_Wall_Paint", "#dddcd6", 0.9),
    "ceiling":   material("Flat_Ceiling_Paint", "#ecebe7", 0.9),
    "trim":      material("Flat_Trim_White", "#f3f2ee", 0.3),
    "laminate":  material("Flat_Floor_Dark_Wood", "#3d302a", 0.55),
    "carpet":    material("Flat_Carpet_Grey", "#a39e98", 1.0),
    "tile":      material("Flat_Floor_Tile", "#85827e", 0.4),
    "wall_tile": material("Flat_Wall_Tile_Grey", "#a19d97", 0.35),
    "dark_tile": material("Flat_Shower_Tile", "#5a5a5f", 0.35),
    "door":      material("Flat_Door_White", "#f1f0ec", 0.4),
    "handle":    material("Flat_Handle_Steel", "#b8babd", 0.3, metallic=1.0),
    "steel":     material("Flat_Steel", "#c9cbce", 0.25, metallic=1.0),
    "glass":     material("Flat_Glass", "#d8ecf2", 0.05, alpha=0.22),
    "mirror":    material("Flat_Mirror", "#c4d0d8", 0.08),
    "bath_mirror": material("Flat_Bath_Mirror", "#c4d0d8", 0.05),     # main.gd makes this one really reflect            # (a real reflection would need a probe)
    "white":     material("Flat_Furniture_White", "#ecebe7", 0.45),
    "porcelain": material("Flat_Porcelain", "#f6f6f4", 0.15),
    "vent":      material("Flat_Vent", "#e2e1dc", 0.6),
    "black":     material("Flat_Black", "#232325", 0.5),
    "screen":    material("Flat_Screen_Black", "#0c0c0f", 0.12),
    "wood_dark": material("Flat_Wood_Dark", "#4b3324", 0.55),
    "wood_lt":   material("Flat_Wood_Light", "#b88a57", 0.55),
    "deck":      material("Flat_Deck_Wood", "#8c5b3b", 0.8),
    "leather":   material("Flat_Leather_Dark", "#2e2724", 0.5),
    "fabric":    material("Flat_Fabric_Grey", "#8e9095", 0.95),
    "navy":      material("Flat_Fabric_Navy", "#2e3a63", 0.95),
    "pink":      material("Flat_Cushion_Pink", "#b23255", 0.9),
    "plush":     material("Flat_Plush_White", "#f2f0ea", 1.0),
    "cowhide":   material("Flat_Cowhide", "#6e4b33", 0.95),
    "rug_blue":  material("Flat_Rug_Blue", "#5d6e9e", 1.0),
    "bathmat":   material("Flat_Bath_Mat_Wood", "#a87a52", 0.7),
    "curtain":   material("Flat_Curtain_Grey", "#8c939d", 0.95),
    "blind":     material("Flat_Blind_Dark", "#30343c", 0.9),
    "board":     material("Flat_Dartboard", "#1d1d1d", 0.8),
    "board_red": material("Flat_Dartboard_Red", "#b8262b", 0.8),
    "board_cream": material("Flat_Dartboard_Cream", "#e9dcc0", 0.8),
    "suitcase":  material("Flat_Suitcase_Navy", "#2f4060", 0.4),
    "basket":    material("Flat_Basket_White", "#e8e6e0", 0.8),
    "towel":     material("Flat_Towel_Blue", "#7fa3c7", 1.0),
    "grass":     material("Flat_Outside_Grass", "#6f9a50", 1.0),
    "trunk":     material("Flat_Outside_Trunk", "#5b4636", 1.0),
    "leaves":    material("Flat_Outside_Leaves", "#4d7a3a", 1.0),
    "house":     material("Flat_Outside_House", "#c9b9a4", 1.0),
    "roof":      material("Flat_Outside_Roof", "#6b5c58", 1.0),
    "sky":       material("Flat_Outside_Sky", "#cfe3f6", 1.0, emission="#cfe3f6", strength=1.6),
    # Same name as the bedroom's lamp, so the game switches these with the top light
    "diffuser":  material("Ceiling_Light_Diffuser", "#f7f7f4", 0.4, emission="#fff8ee", strength=4.0),
}
TOY_COLOURS = ["#e2563a", "#3d7fe0", "#9ed43a", "#f2c13a", "#d86ad0", "#4fb7e0", "#f29a4e", "#68cc80"]
TOYS = [material(f"Flat_Toy_{i}", h, 0.6) for i, h in enumerate(TOY_COLOURS)]


# ---------------------------------------------------------------------------
# One object per Piece (boxes / cylinders in room coordinates)
# ---------------------------------------------------------------------------
from mathutils import Vector

M.update({
    "tv_screen": material("Flat_TV_Screen", "#0c0c0f", 0.12),       # the game puts the TV picture here
    "pc_screen": material("Flat_PC_Screen", "#0c0c0f", 0.12),       # ... and the living-room computer's
    "leather_seam": material("Flat_Leather_Seam", "#221d1b", 0.6),
    "linen":     material("Flat_Fabric_Linen", "#b9b2a6", 0.95),
    "shirt_a":   material("Flat_Clothes_A", "#3f5e8c", 0.95),
    "shirt_b":   material("Flat_Clothes_B", "#c9c3b8", 0.95),
    "shirt_c":   material("Flat_Clothes_C", "#7b3b45", 0.95),
    "shirt_d":   material("Flat_Clothes_D", "#2f2f33", 0.95),
    "box_card":  material("Flat_Cardboard", "#b58d5e", 0.9),
    "closet_in": material("Flat_Closet_Inside", "#d4d1c8", 0.9),
})


# ---------------------------------------------------------------------------
# One object per Piece (boxes / rounded boxes / cylinders / spheres in room coordinates)
# ---------------------------------------------------------------------------
class Piece:
    """bevel > 0 rounds every sharp edge of the piece's plain boxes by that radius
    (furniture looks soft and game-like instead of blocky). rot = the object's turn
    around Z in degrees; chairs use it so their local +X is the way you face."""

    def __init__(self, name, origin=(0, 0, 0), solid=False, bevel=0.0, bevel_seg=2, rot=0.0):
        self.name = name
        self.origin = origin          # object origin (geometry is still given in room coords)
        self.solid = solid
        self.bevel = bevel
        self.bevel_seg = bevel_seg
        self.rot = rot
        self.bm = bmesh.new()
        self.mats = []

    def _mi(self, mat):
        if mat not in self.mats:
            self.mats.append(mat)
        return self.mats.index(mat)

    def _box(self, x0, y0, z0, x1, y1, z1, mat):
        x0, x1 = sorted((x0, x1))
        y0, y1 = sorted((y0, y1))
        z0, z1 = sorted((z0, z1))
        ox, oy, oz = self.origin
        co = [(x0, y0, z0), (x1, y0, z0), (x1, y1, z0), (x0, y1, z0),
              (x0, y0, z1), (x1, y0, z1), (x1, y1, z1), (x0, y1, z1)]
        v = [self.bm.verts.new((c[0] - ox, c[1] - oy, c[2] - oz)) for c in co]
        idx = self._mi(mat)
        for f in [(0, 3, 2, 1), (4, 5, 6, 7), (0, 1, 5, 4), (1, 2, 6, 5), (2, 3, 7, 6), (3, 0, 4, 7)]:
            self.bm.faces.new([v[i] for i in f]).material_index = idx
        return v

    def box(self, x0, y0, z0, x1, y1, z1, mat):
        self._box(x0, y0, z0, x1, y1, z1, mat)
        return self

    def rbox(self, x0, y0, z0, x1, y1, z1, mat, r=0.03, seg=3, tilt=0.0, axis="X", pivot=None):
        """Box with rounded edges (radius r), smooth shaded - cushions, cabinets, doors.
        tilt (degrees) turns it around `axis` through `pivot` (room coords)."""
        before = set(self.bm.verts)
        v = self._box(x0, y0, z0, x1, y1, z1, mat)
        r = min(r, 0.49 * min(abs(x1 - x0), abs(y1 - y0), abs(z1 - z0)))
        if r > 0.0005:
            edges = list({e for vert in v for e in vert.link_edges})
            res = bmesh.ops.bevel(self.bm, geom=edges, offset=r, offset_type="OFFSET",
                                  segments=seg, profile=0.5, affect="EDGES", clamp_overlap=True)
            idx = self._mi(mat)
            for f in res["faces"]:
                f.smooth = True
                f.material_index = idx          # the rounded edge keeps the box's own colour
        if tilt:
            new = [vert for vert in self.bm.verts if vert not in before]
            ox, oy, oz = self.origin
            px, py, pz = pivot if pivot else ((x0 + x1) / 2, (y0 + y1) / 2, (z0 + z1) / 2)
            bmesh.ops.rotate(self.bm, cent=(px - ox, py - oy, pz - oz),
                             matrix=Matrix.Rotation(math.radians(tilt), 3, axis), verts=new)
        return self

    def _smooth_sides(self, res):
        for f in {f for v in res["verts"] for f in v.link_faces}:
            if len(f.verts) == 4:
                f.smooth = True

    def cyl(self, cx, cy, z0, r, h, mat, r_top=None, seg=20, axis="Z"):
        ox, oy, oz = self.origin
        if axis == "Z":
            mtx = Matrix.Translation((cx - ox, cy - oy, z0 - oz + h / 2))
        elif axis == "Y":     # lying along Y: (cx, cz=z0) is the centre line, starts at y=cy
            mtx = Matrix.Translation((cx - ox, cy - oy + h / 2, z0 - oz)) @ Matrix.Rotation(math.pi / 2, 4, "X")
        else:                 # along X, starts at x=cx
            mtx = Matrix.Translation((cx - ox + h / 2, cy - oy, z0 - oz)) @ Matrix.Rotation(math.pi / 2, 4, "Y")
        res = bmesh.ops.create_cone(self.bm, cap_ends=True, cap_tris=False, segments=seg,
                                    radius1=r, radius2=r if r_top is None else r_top, depth=h, matrix=mtx)
        idx = self._mi(mat)
        for f in {f for v in res["verts"] for f in v.link_faces}:
            f.material_index = idx
        self._smooth_sides(res)
        return self

    def tube(self, p0, p1, r, mat, seg=12):
        """Round bar from point p0 to p1 (handrails, chair legs, balusters)."""
        a, b = Vector(p0), Vector(p1)
        d = b - a
        mid = (a + b) / 2 - Vector(self.origin)
        q = Vector((0, 0, 1)).rotation_difference(d.normalized())
        mtx = Matrix.Translation(mid) @ q.to_matrix().to_4x4()
        res = bmesh.ops.create_cone(self.bm, cap_ends=True, cap_tris=False, segments=seg,
                                    radius1=r, radius2=r, depth=d.length, matrix=mtx)
        idx = self._mi(mat)
        for f in {f for v in res["verts"] for f in v.link_faces}:
            f.material_index = idx
        self._smooth_sides(res)
        return self

    def sphere(self, cx, cy, cz, r, mat, scale=(1, 1, 1), seg=16):
        ox, oy, oz = self.origin
        mtx = Matrix.Translation((cx - ox, cy - oy, cz - oz)) @ Matrix.Diagonal((*scale, 1))
        res = bmesh.ops.create_uvsphere(self.bm, u_segments=seg, v_segments=seg // 2, radius=r, matrix=mtx)
        idx = self._mi(mat)
        for f in {f for v in res["verts"] for f in v.link_faces}:
            f.material_index = idx
            f.smooth = True
        return self

    def finish(self, smooth=False):
        bm = self.bm
        if self.bevel > 0:
            edges = [e for e in bm.edges if len(e.link_faces) == 2
                     and not any(f.smooth for f in e.link_faces) and e.calc_face_angle(0) > 0.8]
            if edges:
                res = bmesh.ops.bevel(bm, geom=edges, offset=self.bevel, offset_type="OFFSET",
                                      segments=self.bevel_seg, profile=0.5, affect="EDGES", clamp_overlap=True)
                for f in res["faces"]:
                    f.smooth = True
        if self.rot:
            bmesh.ops.rotate(bm, cent=(0, 0, 0), matrix=Matrix.Rotation(math.radians(-self.rot), 3, "Z"),
                             verts=bm.verts[:])
        bmesh.ops.recalc_face_normals(bm, faces=bm.faces[:])
        uv = bm.loops.layers.uv.new("UVMap")
        bm.normal_update()
        for f in bm.faces:
            n = f.normal
            ax = max(range(3), key=lambda i: abs(n[i]))
            for loop in f.loops:
                c = loop.vert.co
                loop[uv].uv = (c.y, c.z) if ax == 0 else ((c.x, c.z) if ax == 1 else (c.x, c.y))
            if smooth:
                f.smooth = True
        mesh = bpy.data.meshes.new(self.name)
        bm.to_mesh(mesh)
        bm.free()
        for m in self.mats:
            mesh.materials.append(m)
        obj = bpy.data.objects.new(self.name + ("-col" if self.solid else ""), mesh)
        obj.location = self.origin
        obj.rotation_euler[2] = math.radians(self.rot)
        ROOT.objects.link(obj)
        return obj


def marker(name, x, y, z):
    e = bpy.data.objects.new(name, None)
    e.location = (x, y, z)
    ROOT.objects.link(e)


# ---------------------------------------------------------------------------
# Walls: a wall is a box with rectangular holes (doors / windows) cut out of it
# ---------------------------------------------------------------------------
def wall(p, x0, y0, x1, y1, z0=0.0, z1=H, holes=(), mat=None):
    """Box wall from (x0,y0) to (x1,y1). holes = [(a0, a1, b0, b1)] along the wall's long axis
    (a, in room coords) and height (b). Built from the solid pieces around the holes."""
    mat = mat or M["wall"]
    along_x = abs(x1 - x0) >= abs(y1 - y0)
    lo, hi = (min(x0, x1), max(x0, x1)) if along_x else (min(y0, y1), max(y0, y1))

    def seg(a0, a1, b0, b1):
        if a1 - a0 < 0.001 or b1 - b0 < 0.001:
            return
        if along_x:
            p.box(a0, y0, b0, a1, y1, b1, mat)
        else:
            p.box(x0, a0, b0, x1, a1, b1, mat)

    a = lo
    for (h0, h1, b0, b1) in sorted(holes):
        seg(a, h0, z0, z1)             # full-height piece before the hole
        seg(h0, h1, z0, b0)            # under it (window sill wall)
        seg(h0, h1, b1, z1)            # over it
        a = h1
    seg(a, hi, z0, z1)


def frame(p, along_x, line0, line1, a0, a1, z0, z1, depth_out=0.014, w=0.065):
    """White door/window frame (architrave) on both faces of a wall around a hole."""
    for face, sgn in ((line0, -1), (line1, 1)):
        f0, f1 = sorted((face, face + sgn * depth_out))
        parts = [(a0 - w, a0, z0, z1 + w), (a1, a1 + w, z0, z1 + w), (a0 - w, a1 + w, z1, z1 + w)]
        if z0 > 0.05:
            parts.append((a0 - w, a1 + w, z0 - w, z0))
        for (b0, b1, c0, c1) in parts:
            if along_x:
                p.box(b0, f0, c0, b1, f1, c1, M["trim"])
            else:
                p.box(f0, b0, c0, f1, b1, c1, M["trim"])
    # the jamb lining inside the opening
    for a in (a0, a1):
        s = 1 if a == a0 else -1
        if along_x:
            p.box(a, line0, z0, a + s * 0.012, line1, z1, M["trim"])
        else:
            p.box(line0, a, z0, line1, a + s * 0.012, z1, M["trim"])
    if along_x:
        p.box(a0, line0, z1 - 0.012, a1, line1, z1, M["trim"])
    else:
        p.box(line0, a0, z1 - 0.012, line1, a1, z1, M["trim"])


def door_slab(p, along_x, a0, a1, mid, z0=0.0, h=2.03, thick=0.04, handle_at=None, panels=True,
              face_mat=None):
    """A white door leaf from a0 to a1 (along x or y), centred on the line `mid`, with two
    raised panels on each face and lever handles near `handle_at`."""
    t = thick / 2
    if along_x:
        p.rbox(a0, mid - t, z0, a1, mid + t, z0 + h, M["door"], r=0.008, seg=2)
    else:
        p.rbox(mid - t, a0, z0, mid + t, a1, z0 + h, M["door"], r=0.008, seg=2)
    lo, hi = min(a0, a1), max(a0, a1)
    for s in (-1, 1):
        f = mid + s * t
        if panels:
            for (c0, c1) in ((z0 + 0.12, z0 + 0.92), (z0 + 1.08, z0 + h - 0.12)):
                b0, b1 = lo + 0.1, hi - 0.1
                if along_x:
                    p.rbox(b0, f, c0, b1, f + s * 0.008, c1, face_mat or M["door"], r=0.004, seg=2)
                else:
                    p.rbox(f, b0, c0, f + s * 0.008, b1, c1, face_mat or M["door"], r=0.004, seg=2)
        if handle_at is not None:
            hz = z0 + 1.0
            dirn = 1 if handle_at < (lo + hi) / 2 else -1            # lever points to the middle
            if along_x:
                p.cyl(handle_at, f if s > 0 else f - 0.012, hz, 0.022, 0.012, M["handle"], seg=14, axis="Y")
                p.tube((handle_at, f + s * 0.012, hz), (handle_at, f + s * 0.055, hz), 0.009, M["handle"])
                p.tube((handle_at, f + s * 0.055, hz), (handle_at + dirn * 0.12, f + s * 0.055, hz), 0.010, M["handle"])
            else:
                p.cyl(f if s > 0 else f - 0.012, handle_at, hz, 0.022, 0.012, M["handle"], seg=14, axis="X")
                p.tube((f + s * 0.012, handle_at, hz), (f + s * 0.055, handle_at, hz), 0.009, M["handle"])
                p.tube((f + s * 0.055, handle_at, hz), (f + s * 0.055, handle_at + dirn * 0.12, hz), 0.010, M["handle"])


def closed_door(p, along_x, line0, line1, a0, a1, handle_side=1, z0=0.0, h=2.04):
    """A shut white door filling a doorway (with frame, panels and lever handles)."""
    mid = (line0 + line1) / 2
    door_slab(p, along_x, a0 + 0.005, a1 - 0.005, mid, z0, h - 0.01,
              handle_at=(a1 - 0.07) if handle_side > 0 else (a0 + 0.07))
    frame(p, along_x, line0, line1, a0, a1, z0, z0 + h)


def hinged_door(name, hinge_x, hinge_y, along, width, swing_note=""):
    """A door that opens with E in the game: its own object, origin on the hinge.
    along = '+x' / '-x' / '+y' / '-y': the way the closed leaf runs from the hinge."""
    p = Piece(name, origin=(hinge_x, hinge_y, 0), solid=True)
    sgn = 1 if along[0] == "+" else -1
    a0 = (hinge_x if along[1] == "x" else hinge_y) + sgn * 0.005
    a1 = a0 + sgn * (width - 0.01)
    mid = hinge_y if along[1] == "x" else hinge_x
    door_slab(p, along[1] == "x", a0, a1, mid, 0.005, 2.02, handle_at=a1 - sgn * 0.07)
    # hinge knuckles
    for z in (0.25, 1.0, 1.75):
        p.cyl(hinge_x, hinge_y, z, 0.011, 0.09, M["handle"], seg=10)
    return p.finish()


def skirting(p, segments, h=0.085, d=0.014):
    """segments: (x0, y0, x1, y1, side) - side = which way the room is (+x, -x, +y, -y)."""
    for (x0, y0, x1, y1, side) in segments:
        if side == "+y":
            p.box(x0, y0, 0, x1, y0 + d, h, M["trim"])
        elif side == "-y":
            p.box(x0, y0 - d, 0, x1, y0, h, M["trim"])
        elif side == "+x":
            p.box(x0, y0, 0, x0 + d, y1, h, M["trim"])
        else:
            p.box(x0 - d, y0, 0, x0, y1, h, M["trim"])


def cornice(p, segments, h=0.07, d=0.05):
    """Cove cornice: a quarter-round where the wall meets the ceiling."""
    for (x0, y0, x1, y1, side) in segments:
        if side in ("+y", "-y"):
            s = 1 if side == "+y" else -1
            p.cyl(x0, y0, H, d, x1 - x0, M["trim"], seg=16, axis="X")
        else:
            p.cyl(x0, y0, H, d, y1 - y0, M["trim"], seg=16, axis="Y")


# ---------------------------------------------------------------------------
# Layout (measured from the scan; see the top-down picture in scans/)
# ---------------------------------------------------------------------------
# Hallway: west corridor X -3.3..-0.45, Y 3.66..5.4; it widens at X -0.45 to Y 6.45 and runs
# east to the living room. Opposite the bedroom door: the hall closet (X -0.40..1.00).
# The stairs (well X 2.05..5.5, Y 3.75..5.35) start at the living-room end (top, X 5.5) and go
# straight down toward the bedroom end, all the way to the ground floor (ground.glb, made from
# ground_scan.fbx by the scan-to-room skill: its floor is 2.76 m below this one). Both scans agree
# on the well (X 2.05..5.45) and the flight (~15 steps of ~25 cm).
HALL_S = 3.66        # hallway face of the bedroom's desk wall
HALL_W = -3.30       # west end of the corridor
COR_N = 5.40         # north wall of the narrow corridor
HALL_N = 6.45        # north wall of the wide hallway (closet, toilet + bathroom doors)
WIDE_X = -0.45       # where the hallway widens
STAIR_X0, STAIR_X1 = 2.05, 5.50
STAIR_Y0, STAIR_Y1 = 3.75, 5.35
GROUND_Z = -2.76     # ground floor level (ground.glb)
GROUND_CEIL = GROUND_Z + 2.68 - 0.04   # just under the ground floor's ceiling: the well walls stop here
STAIR_STEPS = 15
STAIR_RISE = -GROUND_Z / STAIR_STEPS
STAIR_BOTTOM = GROUND_Z
RUN_X0 = STAIR_X0    # bottom of the flight: it runs out onto the ground floor (no landing)
TREAD = (STAIR_X1 - RUN_X0) / STAIR_STEPS
LIV_X0, LIV_X1 = 5.60, 10.55
LIV_Y0, LIV_Y1 = 3.80, 9.10
TOIL_X0, TOIL_X1, TOIL_Y1 = 1.10, 2.70, 7.55
BATH_X0, BATH_Y1 = 2.60, 9.30
BALC_X1, BALC_Y0, BALC_Y1 = 12.30, 3.85, 8.45
SLIDE_Y0, SLIDE_Y1 = 5.35, 7.65     # balcony sliding door in the living room's east wall
TOILET_DOOR = (1.50, 2.20)
BATH_DOOR = (3.00, 3.75)
CLOSET = (-0.40, 1.00)              # hall closet opening (opposite the bedroom door)
CLOSET_BACK = 7.05

# ---------------------------------------------------------------- floors and ceiling
fl = Piece("Flat_Floor", solid=True)
fl.box(HALL_W - T, HALL_S, -0.05, WIDE_X, COR_N, 0, M["laminate"])            # west corridor
fl.box(WIDE_X, HALL_S, -0.05, STAIR_X0, HALL_N, 0, M["laminate"])            # wide hall + landing
fl.box(STAIR_X0, STAIR_Y1, -0.05, LIV_X0, HALL_N, 0, M["laminate"])          # beside the stair well
fl.box(LIV_X0 - 0.05, LIV_Y0, -0.05, LIV_X1, LIV_Y1, 0, M["carpet"])          # living room
fl.box(CLOSET[0], HALL_N, -0.05, CLOSET[1], CLOSET_BACK, 0, M["laminate"])    # closet
fl.box(TOILET_DOOR[0], HALL_N, -0.05, TOILET_DOOR[1], HALL_N + T, 0.005, M["trim"])   # thresholds
fl.box(BATH_DOOR[0], HALL_N, -0.05, BATH_DOOR[1], HALL_N + T, 0.005, M["trim"])
fl.box(TOIL_X0, HALL_N + T, -0.05, TOIL_X1, TOIL_Y1, 0.0, M["tile"])          # toilet
fl.box(TOIL_X1, HALL_N + T, -0.05, LIV_X0 - 0.05, BATH_Y1, 0.0, M["tile"])    # bathroom
fl.box(BATH_X0, TOIL_Y1, -0.05, TOIL_X1, BATH_Y1, 0.0, M["tile"])
fl.box(LIV_X1, SLIDE_Y0, -0.05, LIV_X1 + T, SLIDE_Y1, 0.005, M["steel"])      # door track
fl.finish()

deck = Piece("Flat_Balcony_Deck", solid=True)
deck.box(LIV_X1 + T, BALC_Y0, -0.12, BALC_X1, BALC_Y1, -0.03, M["deck"])
for i in range(int((BALC_X1 - LIV_X1) / 0.14)):                                # board gaps
    x = LIV_X1 + T + 0.14 * (i + 1)
    deck.box(x - 0.006, BALC_Y0 + 0.01, -0.031, x, BALC_Y1 - 0.01, -0.028, M["wood_dark"])
deck.finish()

ce = Piece("Flat_Ceiling", solid=True)
ce.box(HALL_W - T, 3.56, H, LIV_X1 + T, BATH_Y1 + T, H + 0.05, M["ceiling"])
ce.finish()

# ---------------------------------------------------------------- walls
wl = Piece("Flat_Walls", solid=True)
# south: west of the bedroom, beside the stair well (it goes down with the stairs), living room
wl.box(HALL_W - T, 3.56, 0, -0.60, HALL_S, H, M["wall"])
# (beside the bedroom it starts at the bedroom wall's hallway face, so the two don't overlap)
wall(wl, STAIR_X0 - T, HALL_S, 3.22, STAIR_Y0, z0=GROUND_CEIL)
wall(wl, 3.22, 3.56, LIV_X0, STAIR_Y0, z0=GROUND_CEIL,
     holes=[(4.25, 4.85, 1.2, 1.95)])                                         # frosted stair window
wall(wl, LIV_X0 - 0.05, LIV_Y0 - T, LIV_X1 + T, LIV_Y0,
     holes=[(5.85, 6.40, 0.95, 2.05), (8.55, 9.30, 0.95, 2.05)])               # living room windows
# west end and the corridor's north wall (two shut doors: other rooms)
wall(wl, HALL_W - T, 3.56, HALL_W, COR_N + T, holes=[(4.15, 4.95, 0, 2.04)])
wall(wl, HALL_W - T, COR_N, WIDE_X, COR_N + T, holes=[(-1.30, -0.55, 0, 2.04)])
wl.box(WIDE_X - T, COR_N, 0, WIDE_X, HALL_N + T, H, M["wall"])               # where the hall widens
# hallway north wall: the closet, the toilet and the bathroom doorways
wall(wl, WIDE_X - T, HALL_N, LIV_X0, HALL_N + T,
     holes=[(CLOSET[0], CLOSET[1], 0, 2.10), (TOILET_DOOR[0], TOILET_DOOR[1], 0, 2.04),
            (BATH_DOOR[0], BATH_DOOR[1], 0, 2.04)])
# the closet behind it
wl.box(CLOSET[0] - T, HALL_N, 0, CLOSET[0], CLOSET_BACK + T, H, M["wall"])
wl.box(CLOSET[0] - T, CLOSET_BACK, 0, TOIL_X0, CLOSET_BACK + T, H, M["wall"])
# toilet
wl.box(TOIL_X0 - T, HALL_N, 0, TOIL_X0, TOIL_Y1 + T, H, M["wall"])
wl.box(TOIL_X0 - T, TOIL_Y1, 0, TOIL_X1 + T, TOIL_Y1 + T, H, M["wall"])
wl.box(TOIL_X1, HALL_N, 0, TOIL_X1 + T, TOIL_Y1 + T, H, M["wall"])
# bathroom
wl.box(BATH_X0 - T, TOIL_Y1, 0, BATH_X0, BATH_Y1 + T, H, M["wall"])
wall(wl, BATH_X0 - T, BATH_Y1, LIV_X0, BATH_Y1 + T, holes=[(4.15, 5.25, 1.3, 2.05)])   # window over the bath
wl.box(LIV_X0 - 0.05, HALL_N, 0, LIV_X0 + 0.05, BATH_Y1 + T, H, M["wall"])  # bathroom | living room
# living room north + east (the sliding door to the balcony)
wl.box(LIV_X0, LIV_Y1, 0, LIV_X1 + T, LIV_Y1 + T, H, M["wall"])
wl.box(LIV_X0, LIV_Y1, 0, LIV_X1 + T, BATH_Y1 + T, H, M["wall"])             # (behind the wardrobe)
wall(wl, LIV_X1, LIV_Y0 - T, LIV_X1 + T, LIV_Y1 + T, holes=[(SLIDE_Y0, SLIDE_Y1, 0, 2.15)])
# stair well: the wall under the hall floor edge, the top end wall, the bottom end wall - down to
# the ground floor's ceiling (below that the ground floor scan has its own walls)
wl.box(STAIR_X0, STAIR_Y1, GROUND_CEIL, STAIR_X1 + T, STAIR_Y1 + T, 0, M["wall"])
wl.box(STAIR_X1, STAIR_Y0, GROUND_CEIL, STAIR_X1 + T, STAIR_Y1 + T, 0, M["wall"])
wl.box(STAIR_X0 - T, STAIR_Y0, GROUND_CEIL, STAIR_X0, STAIR_Y1, 0, M["wall"])
# bathroom wall tiles (to 1.2 m) and the dark tiled shower
wall(wl, TOIL_X1 + T, HALL_N + T, LIV_X0 - 0.05, HALL_N + T + 0.01, z1=1.2, mat=M["wall_tile"],
     holes=[(BATH_DOOR[0], BATH_DOOR[1], 0, 2.04)])                            # (not across the doorway)
wl.box(LIV_X0 - 0.06, HALL_N + T, 0, LIV_X0 - 0.05, BATH_Y1, 2.2, M["wall_tile"])
wl.box(BATH_X0, BATH_Y1 - 0.01, 0, LIV_X0 - 0.05, BATH_Y1, 1.2, M["wall_tile"])
wl.box(BATH_X0, 8.30, 0, BATH_X0 + 0.01, BATH_Y1, 2.2, M["dark_tile"])
wl.box(BATH_X0, BATH_Y1 - 0.012, 0, 3.60, BATH_Y1 - 0.01, 2.2, M["dark_tile"])
wl.finish()

# Trim: skirting boards, cove cornices, frames round the openings
tr = Piece("Flat_Trim", bevel=0.004)
skirting(tr, [
    (HALL_W, HALL_S, -0.60, 0, "+y"), (HALL_W, COR_N, -1.30, 0, "-y"), (-0.55, COR_N, WIDE_X, 0, "-y"),
    (HALL_W, HALL_S, 0, 4.15, "+x"), (HALL_W, 4.95, 0, COR_N, "+x"),
    (WIDE_X, COR_N, 0, HALL_N, "+x"), (WIDE_X, HALL_N, CLOSET[0] - 0.07, 0, "-y"),
    (CLOSET[1] + 0.07, HALL_N, TOILET_DOOR[0] - 0.07, 0, "-y"),
    (TOILET_DOOR[1] + 0.07, HALL_N, BATH_DOOR[0] - 0.07, 0, "-y"), (BATH_DOOR[1] + 0.07, HALL_N, LIV_X0 - 0.05, 0, "-y"),
    (0.36, HALL_S, STAIR_X0, 0, "+y"),
    (LIV_X0 + 0.05, LIV_Y0, LIV_X1, 0, "+y"), (LIV_X0 + 0.05, LIV_Y1, LIV_X1, 0, "-y"),
    (LIV_X0 + 0.05, HALL_N, 0, LIV_Y1, "+x"), (LIV_X1, LIV_Y0, 0, SLIDE_Y0 - 0.07, "-x"),
    (LIV_X1, SLIDE_Y1 + 0.07, 0, LIV_Y1, "-x"),
    (TOIL_X0, HALL_N + T, 0, TOIL_Y1, "+x"), (TOIL_X1, HALL_N + T, 0, TOIL_Y1, "-x"),
])
cornice(tr, [
    (HALL_W, HALL_S, -0.60, 0, "+y"), (HALL_W, COR_N, WIDE_X, 0, "-y"), (HALL_W, HALL_S, 0, COR_N, "+x"),
    (WIDE_X, COR_N, 0, HALL_N, "+x"), (WIDE_X, HALL_N, LIV_X0 - 0.05, 0, "-y"),
    (0.31, HALL_S, 3.05, 0, "+y"), (3.05, STAIR_Y0, LIV_X0, 0, "+y"),
    (LIV_X0 + 0.05, LIV_Y0, LIV_X1, 0, "+y"), (LIV_X0 + 0.05, LIV_Y1, LIV_X1, 0, "-y"),
    (LIV_X0 + 0.05, HALL_N, 0, LIV_Y1, "+x"), (LIV_X1, LIV_Y0, 0, LIV_Y1, "-x"),
])
frame(tr, True, HALL_N, HALL_N + T, TOILET_DOOR[0], TOILET_DOOR[1], 0, 2.04)
frame(tr, True, HALL_N, HALL_N + T, BATH_DOOR[0], BATH_DOOR[1], 0, 2.04)
frame(tr, True, HALL_N, HALL_N + T, CLOSET[0], CLOSET[1], 0, 2.10)
frame(tr, False, LIV_X1, LIV_X1 + T, SLIDE_Y0, SLIDE_Y1, 0, 2.15)
for (a0, a1) in ((5.85, 6.40), (8.55, 9.30)):
    frame(tr, True, LIV_Y0 - T, LIV_Y0, a0, a1, 0.95, 2.05)
    tr.box(a0 - 0.04, LIV_Y0, 0.93, a1 + 0.04, LIV_Y0 + 0.06, 0.95, M["trim"])   # sill
frame(tr, True, 3.56, STAIR_Y0, 4.25, 4.85, 1.2, 1.95)
tr.finish()

# Shut doors (rooms that weren't scanned) - solid
dr = Piece("Flat_Shut_Doors", solid=True)
closed_door(dr, False, HALL_W - T, HALL_W, 4.15, 4.95, handle_side=-1)       # end of the corridor
closed_door(dr, True, COR_N, COR_N + T, -1.30, -0.55, handle_side=-1)        # north side of the corridor
door_slab(dr, True, -1.62, -0.82, HALL_S + 0.02, 0, 2.03, handle_at=-1.53)   # cupboard next to the bedroom
frame(dr, True, 3.56, HALL_S + 0.02, -1.62, -0.82, 0, 2.04)
dr.finish()

# Doors you can open with E (main.gd DOOR_SWING): toilet, bathroom, the two closet doors
hinged_door("Door_Toilet", TOILET_DOOR[1] - 0.012, HALL_N + T / 2, "-x", TOILET_DOOR[1] - TOILET_DOOR[0] - 0.024)
hinged_door("Door_Bath", BATH_DOOR[0] + 0.012, HALL_N + T / 2, "+x", BATH_DOOR[1] - BATH_DOOR[0] - 0.024)
half = (CLOSET[1] - CLOSET[0]) / 2
for name, hx, along in (("Door_Closet_L", CLOSET[0] + 0.012, "+x"), ("Door_Closet_R", CLOSET[1] - 0.012, "-x")):
    # closet doors: a full-length mirror on the hall side
    p = Piece(name, origin=(hx, HALL_N + 0.025, 0), solid=True)
    sgn = 1 if along[0] == "+" else -1
    a0, a1 = hx + sgn * 0.004, hx + sgn * (half - 0.016)
    lo, hi = min(a0, a1), max(a0, a1)
    p.rbox(lo, HALL_N + 0.008, 0.01, hi, HALL_N + 0.042, 2.08, M["door"], r=0.008, seg=2)
    p.rbox(lo + 0.07, HALL_N + 0.002, 0.12, hi - 0.07, HALL_N + 0.008, 1.98, M["mirror"], r=0.004, seg=2)
    hx2 = a1 - sgn * 0.05
    p.tube((hx2, HALL_N - 0.035, 0.85), (hx2, HALL_N - 0.035, 1.25), 0.011, M["handle"])   # bar pull
    for z in (0.95, 1.15):
        p.tube((hx2, HALL_N + 0.008, z), (hx2, HALL_N - 0.035, z), 0.007, M["handle"])
    for z in (0.25, 1.0, 1.8):
        p.cyl(hx, HALL_N + 0.025, z, 0.01, 0.08, M["handle"], seg=10)
    p.finish()

# inside the closet: shelf, hanging rail, clothes, boxes
cl = Piece("Flat_Closet_Inside", bevel=0.006)
cl.box(CLOSET[0], CLOSET_BACK - 0.005, 0, TOIL_X0 - 0.10, CLOSET_BACK, H, M["closet_in"])
cl.box(CLOSET[0], HALL_N + T, 1.80, TOIL_X0 - 0.10, CLOSET_BACK, 1.83, M["white"])
cl.tube((CLOSET[0], (HALL_N + T + CLOSET_BACK) / 2, 1.70), (TOIL_X0 - 0.10, (HALL_N + T + CLOSET_BACK) / 2, 1.70),
        0.014, M["steel"])
x = CLOSET[0] + 0.08
k = 0
for (w, h, mat) in ((0.09, 0.95, M["shirt_a"]), (0.07, 0.75, M["shirt_b"]), (0.1, 1.1, M["shirt_d"]),
                    (0.08, 0.8, M["shirt_c"]), (0.06, 0.7, M["shirt_b"]), (0.09, 1.2, M["navy"]),
                    (0.08, 0.85, M["shirt_a"]), (0.07, 0.75, M["shirt_c"]), (0.1, 1.0, M["shirt_d"]),
                    (0.08, 0.9, M["linen"]), (0.07, 0.8, M["shirt_a"])):
    if x + w > TOIL_X0 - 0.15:
        break
    ym = (HALL_N + T + CLOSET_BACK) / 2
    cl.rbox(x, ym - 0.22, 1.66 - h, x + w, ym + 0.22, 1.66, mat, r=0.03, seg=2)
    cl.tube((x + w / 2, ym, 1.66), (x + w / 2, ym, 1.72), 0.004, M["steel"])
    x += w + 0.025
for (x0, w, h, mat) in ((CLOSET[0] + 0.05, 0.42, 0.28, M["box_card"]), (CLOSET[0] + 0.5, 0.36, 0.22, M["white"]),
                        (0.40, 0.45, 0.3, M["box_card"])):
    cl.rbox(x0, HALL_N + 0.2, 1.83, x0 + w, CLOSET_BACK - 0.05, 1.83 + h, mat, r=0.01, seg=2)
cl.rbox(CLOSET[0] + 0.1, HALL_N + 0.25, 0, CLOSET[0] + 0.45, CLOSET_BACK - 0.08, 0.12, M["black"], r=0.02)  # shoes box
cl.finish()

# ---------------------------------------------------------------- stairs (top at the living-room end)
# Floating stairs (as in the photos): thick timber treads, no risers, a black steel stringer on
# the open side, a glass balustrade with a timber handrail. The flight is 1.1 m wide against the
# south wall; the rest of the well (FLIGHT_Y1..STAIR_Y1) is an open void down to the ground floor.
FLIGHT_Y1 = STAIR_Y0 + 1.10
M.setdefault("tread", material("Flat_Stair_Tread", "#5a3220", 0.5))
M.setdefault("stringer", material("Flat_Stair_Stringer", "#1c1c1e", 0.45))
st = Piece("Flat_Stairs", bevel=0.006)
for i in range(STAIR_STEPS):
    x1 = STAIR_X1 - i * TREAD
    x0 = STAIR_X1 - (i + 1) * TREAD
    top = -(i + 1) * STAIR_RISE
    st.rbox(x0 - 0.02, STAIR_Y0, top - 0.09, x1, FLIGHT_Y1 - 0.02, top, M["tread"], r=0.008, seg=2)   # thick tread
st.finish()
sg = Piece("Flat_Stair_Stringer", solid=True)
bms = sg.bm
for (y0, y1) in ((FLIGHT_Y1 - 0.02, FLIGHT_Y1 + 0.01),):
    # a steel plate under the nosing line, 0.3 m deep, from the top to the ground floor
    a0, a1 = (STAIR_X1 + 0.05, 0.02), (RUN_X0 - 0.02, STAIR_BOTTOM)
    co = [(a0[0], y0, a0[1]), (a1[0], y0, a1[1]), (a1[0], y0, a1[1] + 0.0), (a0[0], y0, a0[1])]
    pts = [(a0[0], a0[1]), (a1[0], a1[1] + 0.02), (a1[0] + 0.32, a1[1]), (a0[0], a0[1] - 0.34)]
    vs = [bms.verts.new((x, yy, z)) for yy in (y0, y1) for (x, z) in pts]
    idx = sg._mi(M["stringer"])
    for f in ((0, 1, 2, 3), (7, 6, 5, 4), (0, 4, 5, 1), (1, 5, 6, 2), (2, 6, 7, 3), (3, 7, 4, 0)):
        bms.faces.new([vs[k] for k in f]).material_index = idx
sg.finish()
if RUN_X0 - STAIR_X0 > 0.05:                                                   # bottom landing (if any)
    ld = Piece("Flat_Stair_Landing", solid=True)
    ld.box(STAIR_X0, STAIR_Y0, STAIR_BOTTOM - 0.05, RUN_X0 + 0.01, FLIGHT_Y1, STAIR_BOTTOM, M["laminate"])
    ld.finish()
# Invisible ramp the player walks on (along the step nosings; main.gd hides it)
rp = Piece("Flat_Stair_Ramp", solid=True)
bmr = rp.bm
# flush with the floor at the top (no lip to catch on), down and out onto the ground floor
prof = [(STAIR_X1 + 0.15, 0.0), (STAIR_X1 - 0.05, 0.0), (RUN_X0, STAIR_BOTTOM - 0.008),
        (RUN_X0 - 0.3, STAIR_BOTTOM - 0.008)]
for (xa, za), (xb, zb) in zip(prof, prof[1:]):
    ys = (STAIR_Y0 + 0.01, FLIGHT_Y1 - 0.01)
    v = [bmr.verts.new(c) for c in ((xa, ys[0], za), (xb, ys[0], zb), (xb, ys[1], zb), (xa, ys[1], za),
                                     (xa, ys[0], za - 0.08), (xb, ys[0], zb - 0.08), (xb, ys[1], zb - 0.08),
                                     (xa, ys[1], za - 0.08))]
    idx = rp._mi(M["white"])
    for f in [(0, 1, 2, 3), (7, 6, 5, 4), (0, 4, 5, 1), (1, 5, 6, 2), (2, 6, 7, 3), (3, 7, 4, 0)]:
        bmr.faces.new([v[i] for i in f]).material_index = idx
rp.finish()

# Glass balustrades with a timber handrail: down the open side of the flight, and round the well
# at hall level upstairs (the bedroom end and the hall side; the top of the stairs stays open)
rail = Piece("Flat_Balustrade", solid=True)
GLASS_T = 0.012


def glass_run(x0, y0, z0, x1, y1, z1, h=0.95):
    """Glass panels from (x0,y0,z0) to (x1,y1,z1) (z = the floor / nosing line under them)."""
    L = math.hypot(x1 - x0, y1 - y0)
    n = max(1, int(L / 1.0 + 0.5))
    for k in range(n):
        t0, t1 = k / n + 0.004, (k + 1) / n - 0.004
        pa = (x0 + (x1 - x0) * t0, y0 + (y1 - y0) * t0, z0 + (z1 - z0) * t0)
        pb = (x0 + (x1 - x0) * t1, y0 + (y1 - y0) * t1, z0 + (z1 - z0) * t1)
        bm_ = rail.bm
        dx, dy = (y1 - y0) / L * GLASS_T, -(x1 - x0) / L * GLASS_T
        vs = [bm_.verts.new(c) for c in (
            (pa[0] - dx, pa[1] - dy, pa[2] + 0.05), (pb[0] - dx, pb[1] - dy, pb[2] + 0.05),
            (pb[0] - dx, pb[1] - dy, pb[2] + h - 0.03), (pa[0] - dx, pa[1] - dy, pa[2] + h - 0.03),
            (pa[0] + dx, pa[1] + dy, pa[2] + 0.05), (pb[0] + dx, pb[1] + dy, pb[2] + 0.05),
            (pb[0] + dx, pb[1] + dy, pb[2] + h - 0.03), (pa[0] + dx, pa[1] + dy, pa[2] + h - 0.03))]
        idx = rail._mi(M["glass"])
        for f in ((0, 1, 2, 3), (7, 6, 5, 4), (0, 4, 5, 1), (1, 5, 6, 2), (2, 6, 7, 3), (3, 7, 4, 0)):
            bm_.faces.new([vs[q] for q in f]).material_index = idx
        for p_ in (pa, pb):                                          # small steel clamps
            rail.cyl(p_[0], p_[1], p_[2] + 0.02, 0.012, 0.06, M["steel"], seg=8)
    rail.tube((x0, y0, z0 + h), (x1, y1, z1 + h), 0.03, M["wood_dark"], seg=14)


NEWEL_TOP = 5.0
glass_run(STAIR_X1 - 0.05, FLIGHT_Y1 + 0.02, 0.0, RUN_X0 + 0.05, FLIGHT_Y1 + 0.02, STAIR_BOTTOM)
glass_run(STAIR_X0 - 0.05, STAIR_Y0, 0.0, STAIR_X0 - 0.05, STAIR_Y1 + 0.05, 0.0)
# the hall side runs right to the top end, then turns to meet the flight's own glass, so the
# open void beside the top of the narrow flight is closed off
glass_run(STAIR_X0 - 0.05, STAIR_Y1 + 0.05, 0.0, STAIR_X1, STAIR_Y1 + 0.05, 0.0)
glass_run(STAIR_X1, STAIR_Y1 + 0.05, 0.0, STAIR_X1, FLIGHT_Y1 + 0.02, 0.0)
for (x, y) in ((STAIR_X0 - 0.05, STAIR_Y1 + 0.05), (STAIR_X1, STAIR_Y1 + 0.05), (STAIR_X1, FLIGHT_Y1 + 0.02)):
    rail.cyl(x, y, 0, 0.03, 0.98, M["steel"], seg=12)                          # end posts
rail.finish()
hr = Piece("Flat_Stair_Handrail")                                             # on the south wall
y = STAIR_Y0 + 0.07
hr.tube((STAIR_X1 + 0.05, y, 0.9), (RUN_X0, y, 0.9 + STAIR_BOTTOM), 0.022, M["wood_dark"], seg=14)
for k in range(4):
    t = (k + 0.5) / 4
    xx = STAIR_X1 - t * (STAIR_X1 - RUN_X0)
    zz = 0.9 + STAIR_BOTTOM * t - 0.05
    hr.tube((xx, STAIR_Y0, zz), (xx, y, zz), 0.008, M["steel"])
hr.finish()

# ---------------------------------------------------------------- windows (glass + outside view)
gl = Piece("Flat_Window_Glass")
for (a0, a1) in ((5.85, 6.40), (8.55, 9.30)):
    gl.box(a0, LIV_Y0 - 0.06, 0.95, a1, LIV_Y0 - 0.05, 2.05, M["glass"])
gl.box(4.25, 3.62, 1.2, 4.85, 3.63, 1.95, M["glass"])
gl.box(4.15, BATH_Y1 + 0.05, 1.3, 5.25, BATH_Y1 + 0.06, 2.05, M["glass"])
gl.finish()
wf = Piece("Flat_Window_Frames", bevel=0.004)
for (a0, a1) in ((5.85, 6.40), (8.55, 9.30)):
    mid = (a0 + a1) / 2
    wf.box(mid - 0.02, LIV_Y0 - 0.07, 0.95, mid + 0.02, LIV_Y0 - 0.04, 2.05, M["trim"])
# plantation shutters on the window above the wooden armchair
for k in range(14):
    z = 1.0 + k * 0.075
    wf.rbox(8.58, LIV_Y0 + 0.01, z, 9.27, LIV_Y0 + 0.07, z + 0.045, M["trim"], r=0.012, seg=2,
            tilt=-25, axis="X")
wf.box(8.55, LIV_Y0, 0.95, 8.59, LIV_Y0 + 0.08, 2.05, M["trim"])
wf.box(9.26, LIV_Y0, 0.95, 9.30, LIV_Y0 + 0.08, 2.05, M["trim"])
# dark roller blind over the bathroom window (pulled down most of the way)
wf.box(4.12, BATH_Y1 - 0.06, 1.55, 5.28, BATH_Y1 - 0.04, 2.05, M["blind"])
wf.cyl(4.10, BATH_Y1 - 0.05, 2.07, 0.025, 1.2, M["white"], axis="X")
wf.finish()

# sliding balcony door: one panel slid open behind the other, glass + white frames
sd = Piece("Flat_Sliding_Door", solid=True, bevel=0.005)
mid_y = (SLIDE_Y0 + SLIDE_Y1) / 2
for (y0, y1, x) in ((mid_y, SLIDE_Y1, LIV_X1 + 0.07), (mid_y + 0.05, SLIDE_Y1, LIV_X1 + 0.02)):
    sd.box(x - 0.005, y0 + 0.04, 0.05, x + 0.005, y1 - 0.04, 2.11, M["glass"])
    sd.box(x - 0.02, y0, 0.0, x + 0.02, y0 + 0.05, 2.15, M["white"])
    sd.box(x - 0.02, y1 - 0.05, 0.0, x + 0.02, y1, 2.15, M["white"])
    sd.box(x - 0.02, y0, 0.0, x + 0.02, y1, 0.05, M["white"])
    sd.box(x - 0.02, y0, 2.1, x + 0.02, y1, 2.15, M["white"])
sd.finish()

# outside: the lawn at ground-floor level (this flat is upstairs), trees, neighbours' houses, sky all round
lawn = Piece("Flat_Lawn", solid=True)                                          # solid: nobody falls forever
lawn.box(-20, -20, GROUND_Z - 0.3, 30, 30, GROUND_Z - 0.04, M["grass"])   # just under the ground floor
lawn.finish()
out = Piece("Flat_Outside")
for (x, y, s) in ((14.5, 2.0, 1.2), (16.0, 6.5, 1.5), (15.0, 11.0, 1.1), (8.0, 12.5, 1.3),
                  (3.0, 12.0, 1.0), (9.5, -0.5, 1.2), (5.5, -1.5, 1.0), (13.0, 14.0, 1.4)):
    out.cyl(x, y, -3.0, 0.18 * s, 3.2 * s, M["trunk"], seg=10, r_top=0.12 * s)
    out.sphere(x, y, -3.0 + 3.6 * s, 1.5 * s, M["leaves"], scale=(1, 1, 1.15), seg=14)
    out.sphere(x + 0.6 * s, y - 0.3 * s, -3.0 + 3.0 * s, 1.0 * s, M["leaves"], seg=12)
for (x0, y0, x1, y1) in ((17.5, 0.0, 22.0, 5.0), (18.0, 8.0, 23.0, 13.0), (-1.0, 15.0, 6.0, 20.0)):
    out.box(x0, y0, -3.0, x1, y1, 2.6, M["house"])
    out.box(x0 - 0.3, y0 - 0.3, 2.6, x1 + 0.3, y1 + 0.3, 3.0, M["roof"])
out.finish()
sky = Piece("Flat_Sky")
R = 32
for (x0, y0, x1, y1) in ((-R + 4, -R + 6, R + 4, -R + 6.1), (-R + 4, R + 6, R + 4, R + 6.1),
                         (-R + 4, -R + 6, -R + 4.1, R + 6), (R + 4, -R + 6, R + 4.1, R + 6)):
    sky.box(x0, y0, -4, x1, y1, 30, M["sky"])
sky.box(-R + 4, -R + 6, 30, R + 4, R + 6, 30.1, M["sky"])
sky.finish()

# balcony glass balustrade
bb = Piece("Flat_Balcony_Rail", solid=True)
for (x0, y0, x1, y1) in ((LIV_X1 + T, BALC_Y0, BALC_X1, BALC_Y0), (BALC_X1, BALC_Y0, BALC_X1, BALC_Y1),
                         (LIV_X1 + T, BALC_Y1, BALC_X1, BALC_Y1)):
    if x0 == x1:
        bb.box(x0 - 0.01, y0, 0.08, x0 + 0.01, y1, 0.95, M["glass"])
    else:
        bb.box(x0, y0 - 0.01, 0.08, x1, y0 + 0.01, 0.95, M["glass"])
    bb.tube((x0, y0, 0.98), (x1, y1, 0.98), 0.03, M["steel"], seg=14)
for (x, y) in ((LIV_X1 + T, BALC_Y0), (BALC_X1, BALC_Y0), (BALC_X1, BALC_Y1), (LIV_X1 + T, BALC_Y1),
               (BALC_X1, (BALC_Y0 + BALC_Y1) / 2)):
    bb.cyl(x, y, -0.03, 0.03, 1.01, M["steel"], seg=14)
bb.finish()

# ---------------------------------------------------------------- ceiling lights (+ markers)
LIGHTS = [(-1.9, 4.5), (0.5, 5.7), (2.2, 4.5), (4.3, 4.55), (4.4, 5.95), (1.9, 7.0), (4.0, 8.0),
          (7.0, 6.3), (9.0, 6.3)]
lamps = Piece("Flat_Ceiling_Lamps")
for i, (x, y) in enumerate(LIGHTS):
    lamps.sphere(x, y, H - 0.02, 0.16, M["diffuser"], scale=(1, 1, 0.35), seg=24)
    lamps.cyl(x, y, H - 0.012, 0.18, 0.012, M["white"], seg=28)
    marker(f"Flat_Light_{i}", x, y, H - 0.1)
lamps.finish()

# ---------------------------------------------------------------- hallway details
hd = Piece("Flat_Hall_Details", bevel=0.003)
# return-air vent (low on the corridor's north wall) and light switches
hd.box(-2.45, COR_N - 0.015, 0.18, -1.9, COR_N, 0.62, M["vent"])
for k in range(10):
    z = 0.21 + k * 0.04
    hd.box(-2.42, COR_N - 0.02, z, -1.93, COR_N - 0.015, z + 0.012, M["trim"])
for (x, y, side) in ((-0.68, COR_N, -1), (2.35, HALL_N, -1), (3.9, HALL_N, -1), (-3.3 + 0.002, 4.05, 0)):
    if side == 0:
        hd.rbox(x, y - 0.04, 1.15, x + 0.012, y + 0.04, 1.27, M["white"], r=0.004, seg=2)
    else:
        hd.rbox(x - 0.04, y - 0.012, 1.15, x + 0.04, y, 1.27, M["white"], r=0.004, seg=2)
hd.rbox(-1.2, COR_N - 0.02, 1.45, -1.08, COR_N, 1.55, M["white"], r=0.006, seg=2)   # thermostat
hd.finish()

# full-length mirror on the hall wall just outside the bedroom door (main.gd makes it reflect)
M.setdefault("hall_mirror", material("Flat_Hall_Mirror", "#c4d0d8", 0.05))
hm = Piece("Flat_Hall_Mirror", bevel=0.003)
hm.rbox(0.66, HALL_S, 0.10, 1.30, HALL_S + 0.03, 1.98, M["wood_dark"], r=0.008, seg=2)          # frame
hm.box(0.70, HALL_S + 0.03, 0.14, 1.26, HALL_S + 0.033, 1.94, M["hall_mirror"])
hm.finish()

# ---------------------------------------------------------------- toilet
tl = Piece("Flat_Toilet", solid=True)
tl.rbox(TOIL_X0, 6.92, 0.42, TOIL_X0 + 0.19, 7.32, 0.80, M["porcelain"], r=0.04)        # cistern
tl.rbox(TOIL_X0 + 0.04, 7.0, 0.0, TOIL_X0 + 0.3, 7.24, 0.36, M["porcelain"], r=0.06)    # pedestal
tl.sphere(TOIL_X0 + 0.38, 7.12, 0.32, 0.2, M["porcelain"], scale=(1.15, 0.95, 0.45), seg=24)   # bowl
tl.cyl(TOIL_X0 + 0.39, 7.12, 0.38, 0.19, 0.03, M["porcelain"], seg=28)                  # seat
tl.cyl(TOIL_X0 + 0.20, 7.12, 0.41, 0.035, 0.02, M["porcelain"], seg=12)
tl.cyl(TOIL_X0 + 0.095, 7.12, 0.80, 0.025, 0.006, M["steel"], seg=16)                   # flush button
tl.cyl(TOIL_X1 - 0.02, 7.35, 0.75, 0.05, 0.11, M["white"], axis="X", seg=16)            # paper roll
tl.finish()

# ---------------------------------------------------------------- bathroom
bt = Piece("Flat_Bathroom", solid=True)
# bath under the window
bt.rbox(3.95, 8.62, 0, LIV_X0 - 0.05, BATH_Y1 + 0.03, 0.55, M["porcelain"], r=0.05)
bt.rbox(4.07, 8.72, 0.22, LIV_X0 - 0.17, BATH_Y1 - 0.08, 0.56, M["white"], r=0.12, seg=4)
bt.tube((4.8, BATH_Y1 - 0.02, 0.62), (4.8, BATH_Y1 - 0.14, 0.62), 0.02, M["steel"])
# vanity: wall to wall along the east wall (bath -> the wall by the door), basin at the south (right) end
VAN_Y0, VAN_Y1 = HALL_N + T + 0.011, 8.615
SINK_Y = VAN_Y0 + 0.45
bt.rbox(LIV_X0 - 0.55, VAN_Y0 + 0.01, 0.15, LIV_X0 - 0.06, VAN_Y1 - 0.01, 0.82, M["white"], r=0.015)
bt.rbox(LIV_X0 - 0.56, VAN_Y0, 0.82, LIV_X0 - 0.06, VAN_Y1, 0.86, M["porcelain"], r=0.012)
bt.sphere(LIV_X0 - 0.31, SINK_Y, 0.91, 0.22, M["porcelain"], scale=(1, 1.15, 0.35), seg=24)   # basin
bt.tube((LIV_X0 - 0.11, SINK_Y, 0.86), (LIV_X0 - 0.11, SINK_Y, 1.1), 0.016, M["steel"])        # tap
bt.tube((LIV_X0 - 0.11, SINK_Y, 1.1), (LIV_X0 - 0.25, SINK_Y, 1.07), 0.013, M["steel"])
n_doors = 4
dw = (VAN_Y1 - VAN_Y0 - 0.06) / n_doors
for k in range(n_doors):
    y0 = VAN_Y0 + 0.03 + k * dw
    bt.rbox(LIV_X0 - 0.565, y0, 0.2, LIV_X0 - 0.55, y0 + dw - 0.02, 0.78, M["porcelain"], r=0.004, seg=2)
    hy = y0 + (dw - 0.02) / 2
    bt.tube((LIV_X0 - 0.58, hy - 0.05, 0.72), (LIV_X0 - 0.58, hy + 0.05, 0.72), 0.008, M["steel"])
# the mirror above it (thin steel edge round it)
MIR_Y0, MIR_Y1, MIR_Z0, MIR_Z1 = VAN_Y0 + 0.12, VAN_Y1 - 0.12, 0.93, 2.05   # low enough for 4 ft characters
bt.rbox(LIV_X0 - 0.072, MIR_Y0 - 0.012, MIR_Z0 - 0.012, LIV_X0 - 0.055, MIR_Y1 + 0.012, MIR_Z1 + 0.012, M["steel"], r=0.006, seg=2)
bt.box(LIV_X0 - 0.075, MIR_Y0, MIR_Z0, LIV_X0 - 0.072, MIR_Y1, MIR_Z1, M["bath_mirror"])
# glass shower (dark tiles) in the north-west corner
bt.box(BATH_X0, 8.30, 0, 3.60, BATH_Y1, 0.04, M["dark_tile"])
bt.box(3.58, 8.30, 0.04, 3.60, BATH_Y1, 2.05, M["glass"])
bt.box(BATH_X0, 8.29, 0.04, 2.95, 8.31, 2.05, M["glass"])           # fixed panel; walk-in gap 2.95..3.58
bt.cyl(2.95, 8.30, 0.04, 0.012, 2.01, M["steel"], seg=12)                    # edge trim
bt.cyl(3.59, 8.30, 0, 0.02, 2.05, M["steel"], seg=12)
bt.tube((BATH_X0 + 0.01, 8.85, 1.95), (BATH_X0 + 0.28, 8.85, 1.95), 0.012, M["steel"])
bt.cyl(BATH_X0 + 0.28, 8.85, 1.84, 0.12, 0.02, M["steel"], seg=24)
bt.tube((BATH_X0 + 0.02, 8.85, 0.9), (BATH_X0 + 0.02, 8.85, 1.9), 0.012, M["steel"])
bt.finish()
bp = Piece("Flat_Bathroom_Props")
for k in range(9):                                                             # slatted bath mat
    x = 4.47 + k * 0.06
    bp.rbox(x, 7.40, 0, x + 0.045, 8.30, 0.025, M["bathmat"], r=0.008, seg=2)
bp.cyl(4.10, 7.05, 0, 0.2, 0.42, M["basket"], r_top=0.23, seg=24)              # laundry basket
bp.tube((BATH_X0 + 0.04, 7.75, 1.25), (BATH_X0 + 0.04, 8.25, 1.25), 0.012, M["steel"])   # towel rail + towel
bp.rbox(BATH_X0 + 0.015, 7.78, 0.75, BATH_X0 + 0.065, 8.22, 1.27, M["towel"], r=0.02, seg=3)
bp.finish()


# ---------------------------------------------------------------- living room furniture
def lounge(prefix, x0, y0, x1, y1, cover, seats, arm_w=0.2, back_d=0.24, back_top=0.88,
           arm_top=0.62, legs=None, arm_r=0.08):
    """Sofa / armchair facing +Y (back along y0), soft and rounded. The seat cushions are
    their own objects "Chair_<prefix>_N" (origin = middle of the cushion, local +X = the
    way you face, rot 90) so E sits you on the cushion you look at."""
    seat_top = 0.47                         # avatar.gd SEAT_Y
    body = Piece("Flat_" + prefix, solid=True, bevel=0.01)
    body.rbox(x0 + 0.02, y0 + 0.03, 0.07, x1 - 0.02, y1 - 0.02, 0.31, cover, r=0.04)          # base
    body.rbox(x0, y0, 0.07, x0 + arm_w, y1, arm_top, cover, r=arm_r, seg=4)                   # arms
    body.rbox(x1 - arm_w, y0, 0.07, x1, y1, arm_top, cover, r=arm_r, seg=4)
    body.rbox(x0 + arm_w - 0.02, y0, 0.07, x1 - arm_w + 0.02, y0 + back_d, back_top - 0.12, cover, r=0.06, seg=4)
    inner0, inner1 = x0 + arm_w, x1 - arm_w
    w = (inner1 - inner0) / seats
    for i in range(seats):                  # back cushions, leaning back a little
        a, b = inner0 + i * w + 0.01, inner0 + (i + 1) * w - 0.01
        body.rbox(a, y0 + 0.10, 0.40, b, y0 + 0.34, back_top, cover, r=0.09, seg=4,
                  tilt=9, axis="X", pivot=((a + b) / 2, y0 + 0.2, 0.40))
    for (fx, fy) in ((x0 + 0.07, y0 + 0.07), (x1 - 0.07, y0 + 0.07), (x0 + 0.07, y1 - 0.07), (x1 - 0.07, y1 - 0.07)):
        body.cyl(fx, fy, 0, 0.025, 0.07, legs or M["black"], r_top=0.032, seg=12)
    seats_out = []
    for i in range(seats):
        a, b = inner0 + i * w + 0.008, inner0 + (i + 1) * w - 0.008
        cy0, cy1 = y0 + back_d + 0.02, y1 - 0.01
        name = "Chair_%s_%d" % (prefix, i + 1) if seats > 1 else "Chair_" + prefix
        seat = Piece(name, origin=((a + b) / 2, (cy0 + cy1) / 2, 0), solid=True, rot=90)
        seat.rbox(a, cy0, 0.29, b, cy1, seat_top, cover, r=0.06, seg=4)
        seats_out.append(seat)
    return body, seats_out


# dark leather sofa facing the TV (two seats), grey fabric armchair beside it
sofa, sofa_seats = lounge("Sofa", 7.35, 6.15, 9.05, 7.10, M["leather"], 2, arm_w=0.22)
sofa.rbox(7.60, 6.38, 0.47, 7.98, 6.52, 0.83, M["plush"], r=0.06, seg=3, tilt=-14, axis="Y")   # white cushion
sofa.finish()
for s in sofa_seats:
    s.finish()
arm, arm_seats = lounge("Armchair", 6.15, 6.20, 7.10, 7.10, M["fabric"], 1, arm_w=0.2, arm_r=0.07)
arm.sphere(6.25, 6.45, 0.74, 0.11, M["plush"], scale=(1, 0.85, 1.0), seg=16)    # white plush toy on the arm
arm.sphere(6.25, 6.45, 0.88, 0.075, M["plush"], seg=14)
arm.sphere(6.21, 6.43, 0.94, 0.025, M["plush"], seg=8)
arm.sphere(6.29, 6.43, 0.94, 0.025, M["plush"], seg=8)
arm.finish()
for s in arm_seats:
    s.finish()

# wooden armchair with navy cushions and a pink pillow (under the shuttered window)
pc = Piece("Flat_Wood_Armchair", solid=True, bevel=0.006)
for (fx, fy) in ((8.56, 4.00), (9.19, 4.00), (8.56, 4.62), (9.19, 4.62)):
    pc.tube((fx, fy, 0), (fx, fy + (0.0 if fy < 4.3 else 0.02), 0.62), 0.022, M["wood_lt"])
pc.rbox(8.53, 3.96, 0.30, 9.22, 4.66, 0.36, M["wood_lt"], r=0.012)
for xx in (8.53, 9.16):
    pc.rbox(xx, 3.98, 0.60, xx + 0.06, 4.70, 0.645, M["wood_lt"], r=0.02)          # arm rests
pc.rbox(8.55, 3.95, 0.36, 9.20, 4.04, 1.02, M["wood_lt"], r=0.02, tilt=8, axis="X", pivot=(8.9, 4.0, 0.36))
pc.rbox(8.60, 4.05, 0.40, 9.15, 4.16, 0.98, M["navy"], r=0.05, seg=4, tilt=8, axis="X", pivot=(8.9, 4.1, 0.40))
pc.rbox(8.72, 4.13, 0.48, 9.03, 4.27, 0.80, M["pink"], r=0.06, seg=4, tilt=12, axis="X", pivot=(8.9, 4.2, 0.48))
pc.finish()
wseat = Piece("Chair_Armchair_Wood", origin=(8.875, 4.42, 0), solid=True, rot=90)
wseat.rbox(8.60, 4.12, 0.36, 9.15, 4.68, 0.47, M["navy"], r=0.045, seg=4)
wseat.finish()

# desk with two monitors and an office chair with a blanket (south wall)
dk = Piece("Flat_Desk", solid=True, bevel=0.006)
dk.rbox(6.60, 3.85, 0.72, 8.15, 4.55, 0.76, M["white"], r=0.012)
for (fx, fy) in ((6.65, 3.9), (8.1, 3.9), (6.65, 4.5), (8.1, 4.5)):
    dk.cyl(fx, fy, 0, 0.02, 0.72, M["steel"], seg=12)
for k, mx in enumerate((6.95, 7.55)):
    dk.rbox(mx, 4.0, 0.76 + 0.02, mx + 0.55, 4.03, 1.14, M["black"], r=0.008, seg=2)       # monitor (faces +Y)
    dk.box(mx + 0.012, 4.031, 0.80, mx + 0.538, 4.034, 1.125, M["pc_screen"] if k == 0 else M["screen"])
    dk.rbox(mx + 0.25, 3.94, 0.80, mx + 0.30, 4.0, 0.98, M["black"], r=0.01)
    dk.rbox(mx + 0.18, 3.90, 0.76, mx + 0.37, 4.06, 0.775, M["black"], r=0.008)
dk.rbox(7.1, 4.2, 0.76, 7.55, 4.35, 0.78, M["black"], r=0.006)                         # keyboard
dk.rbox(7.65, 4.24, 0.76, 7.71, 4.33, 0.785, M["black"], r=0.012)                      # mouse
dk.cyl(6.75, 4.1, 0.76, 0.05, 0.16, M["black"], seg=16)                                # speaker
dk.finish()


def office_chair(name, cx, cy, facing_deg, blanket=None):
    """Office chair; origin at the seat, local +X = the way you face."""
    p = Piece(name, origin=(cx, cy, 0), solid=True, rot=facing_deg)
    for a in range(5):
        ang = math.radians(a * 72 + 18)
        ex, ey = cx + math.cos(ang) * 0.28, cy + math.sin(ang) * 0.28
        p.tube((cx, cy, 0.08), (ex, ey, 0.05), 0.022, M["black"])
        p.sphere(ex, ey, 0.03, 0.03, M["black"], seg=10)
    p.cyl(cx, cy, 0.08, 0.028, 0.34, M["steel"], seg=14)
    p.rbox(cx - 0.25, cy - 0.25, 0.42, cx + 0.25, cy + 0.25, 0.50, M["black"], r=0.04)
    # back on the side away from where you face
    fx, fy = math.cos(math.radians(facing_deg)), math.sin(math.radians(facing_deg))
    bx, by = cx - fx * 0.26, cy - fy * 0.26
    if abs(fx) > 0.5:
        p.rbox(bx - 0.04, cy - 0.23, 0.55, bx + 0.04, cy + 0.23, 1.05, M["black"], r=0.035)
        p.tube((bx, cy, 0.5), (bx, cy, 0.56), 0.02, M["black"])
        if blanket:
            p.rbox(bx - 0.06, cy - 0.27, 0.45, bx + 0.07, cy + 0.27, 1.08, blanket, r=0.04, seg=3)
    else:
        p.rbox(cx - 0.23, by - 0.04, 0.55, cx + 0.23, by + 0.04, 1.05, M["black"], r=0.035)
        p.tube((cx, by, 0.5), (cx, by, 0.56), 0.02, M["black"])
        if blanket:
            p.rbox(cx - 0.27, by - 0.06, 0.45, cx + 0.27, by + 0.07, 1.08, blanket, r=0.04, seg=3)
    return p.finish()


office_chair("Chair_Desk", 7.40, 4.95, -90, blanket=M["navy"])     # facing the desk (-Y)

# TV on a white TV unit, the toy shelf with a guitar, wardrobe, coffee table
tv = Piece("Flat_TV_Unit", solid=True, bevel=0.006)
tv.rbox(6.75, 8.62, 0.05, 9.10, LIV_Y1, 0.50, M["white"], r=0.015)
for k in range(4):
    x = 6.8 + k * 0.58
    tv.rbox(x, 8.612, 0.1, x + 0.54, 8.62, 0.45, M["porcelain"], r=0.004, seg=2)
    tv.tube((x + 0.22, 8.60, 0.42), (x + 0.32, 8.60, 0.42), 0.006, M["steel"])
tv.rbox(7.1, 8.85, 0.56, 8.75, 8.92, 1.45, M["black"], r=0.012, seg=2)                 # 70" TV
tv.box(7.12, 8.849, 0.58, 8.73, 8.851, 1.43, M["tv_screen"])                          # its screen
tv.rbox(7.85, 8.82, 0.5, 8.0, 8.94, 0.58, M["black"], r=0.01)                         # stand
tv.rbox(7.55, 8.74, 0.5, 8.30, 8.84, 0.52, M["black"], r=0.008)
for k, (x, w, h) in enumerate(((6.85, 0.18, 0.14), (9.0 - 0.3, 0.22, 0.2), (6.95 + 1.9, 0.12, 0.25))):
    tv.rbox(x, 8.7, 0.5, x + w, 8.86, 0.5 + h, TOYS[k], r=0.03)
tv.finish()
ac = Piece("Flat_AC", bevel=0.01)
ac.rbox(8.95, LIV_Y1 - 0.24, 2.0, 9.85, LIV_Y1, 2.28, M["white"], r=0.04)
ac.box(8.98, LIV_Y1 - 0.235, 2.02, 9.82, LIV_Y1 - 0.18, 2.05, M["vent"])
ac.finish()

sh = Piece("Flat_Toy_Shelf", solid=True, bevel=0.004)
sx0, sx1, sy0, sy1 = LIV_X0 + 0.07, LIV_X0 + 0.47, 7.55, 8.95
for (fx, fy) in ((sx0, sy0), (sx1, sy0), (sx0, sy1), (sx1, sy1)):
    sh.box(fx - 0.015, fy - 0.015, 0, fx + 0.015, fy + 0.015, 1.8, M["black"])
for k in range(5):
    z = 0.12 + k * 0.42
    sh.box(sx0, sy0, z, sx1, sy1, z + 0.02, M["black"])
    y = sy0 + 0.04
    while y < sy1 - 0.12 and z < 1.7:
        w = random.uniform(0.12, 0.3)
        h = random.uniform(0.12, 0.33)
        x1 = sx0 + random.uniform(0.2, 0.36)
        if random.random() < 0.35:   # some round toys / plushies
            rr = min(w, h, x1 - sx0) / 2
            sh.sphere(sx0 + 0.04 + rr, y + rr, z + 0.02 + rr, rr, random.choice(TOYS), seg=12)
        else:
            sh.rbox(sx0 + 0.04, y, z + 0.02, x1, min(y + w, sy1 - 0.03), z + 0.02 + h,
                    random.choice(TOYS), r=0.02, seg=2)
        y += w + 0.04
sh.finish()
gt = Piece("Flat_Guitar")                                                   # leaning on the shelf
gt.sphere(6.25, 8.85, 0.25, 0.2, M["wood_lt"], scale=(0.5, 1.0, 1.15), seg=18)
gt.sphere(6.25, 8.85, 0.52, 0.15, M["wood_lt"], scale=(0.5, 1.0, 1.1), seg=18)
gt.cyl(6.30, 8.85, 0.38, 0.05, 0.01, M["black"], seg=16, axis="X")
gt.tube((6.25, 8.85, 0.6), (6.25, 8.85, 1.15), 0.025, M["wood_dark"])
gt.rbox(6.21, 8.82, 1.12, 6.29, 8.88, 1.25, M["wood_dark"], r=0.015)
gt.finish(smooth=True)

wd = Piece("Flat_Wardrobe", solid=True, bevel=0.006)
wd.rbox(9.65, 8.55, 0, LIV_X1, LIV_Y1, 2.0, M["white"], r=0.012)
wd.box(10.098, 8.545, 0.05, 10.102, 8.56, 1.95, M["porcelain"])
for x in (10.03, 10.17):
    wd.tube((x, 8.52, 0.9), (x, 8.52, 1.2), 0.01, M["steel"])
wd.rbox(9.7, 8.6, 2.0, 10.05, 9.05, 2.3, M["black"], r=0.04, seg=3)                  # luggage on top
wd.rbox(10.08, 8.62, 2.0, 10.5, 9.05, 2.22, M["suitcase"], r=0.04, seg=3)
wd.finish()

ct = Piece("Flat_Coffee_Table", solid=True, bevel=0.006)
ct.rbox(6.95, 7.45, 0.38, 7.75, 8.25, 0.45, M["wood_dark"], r=0.025, seg=3)
ct.rbox(6.99, 7.49, 0.1, 7.71, 8.21, 0.13, M["wood_dark"], r=0.01)
for (fx, fy) in ((6.99, 7.49), (7.71, 7.49), (6.99, 8.21), (7.71, 8.21)):
    ct.cyl(fx, fy, 0, 0.025, 0.38, M["wood_dark"], seg=12)
ct.cyl(7.2, 7.7, 0.45, 0.035, 0.2, TOYS[5], seg=14, r_top=0.03)                         # bottles / stuff
ct.cyl(7.35, 7.95, 0.45, 0.045, 0.12, TOYS[3], seg=14)
ct.rbox(7.45, 7.6, 0.45, 7.65, 7.75, 0.5, TOYS[0], r=0.015)
ct.finish()

bk = Piece("Flat_Exercise_Bike", solid=True)                                # facing -X
bk.tube((9.53, 7.6, 0.03), (9.53, 8.2, 0.03), 0.03, M["black"])
bk.tube((10.18, 7.6, 0.03), (10.18, 8.2, 0.03), 0.03, M["black"])
bk.tube((9.53, 7.9, 0.04), (10.18, 7.9, 0.04), 0.03, M["black"])
bk.cyl(9.62, 7.84, 0.35, 0.22, 0.12, M["steel"], seg=28, axis="Y")         # flywheel
bk.rbox(9.60, 7.82, 0.15, 9.98, 7.98, 0.62, M["black"], r=0.06, seg=3)      # body
bk.tube((9.95, 7.9, 0.4), (9.88, 7.9, 0.92), 0.025, M["black"])             # seat post
bk.rbox(9.76, 7.8, 0.9, 10.02, 8.0, 0.97, M["black"], r=0.03, seg=3)        # saddle
bk.tube((9.6, 7.9, 0.4), (9.57, 7.9, 1.12), 0.025, M["black"])              # handlebar post
bk.tube((9.54, 7.65, 1.13), (9.54, 8.15, 1.13), 0.018, M["black"])
bk.finish()
sc = Piece("Flat_Suitcase", solid=True)
sc.rbox(9.15, 8.2, 0.03, 9.55, 8.45, 0.72, M["suitcase"], r=0.04, seg=3)
for (fx, fy) in ((9.19, 8.24), (9.51, 8.24), (9.19, 8.41), (9.51, 8.41)):
    sc.sphere(fx, fy, 0.025, 0.025, M["black"], seg=10)
for fx in (9.3, 9.4):
    sc.tube((fx, 8.33, 0.72), (fx, 8.33, 0.88), 0.008, M["steel"])
sc.tube((9.29, 8.33, 0.88), (9.41, 8.33, 0.88), 0.012, M["black"])
sc.finish()

# rugs, curtains, dartboard
rg = Piece("Flat_Rugs")
rg.rbox(9.3, 4.05, 0, 10.3, 5.0, 0.012, M["cowhide"], r=0.006, seg=2)
rg.sphere(9.8, 4.5, 0.008, 0.35, M["plush"], scale=(1.0, 0.7, 0.01), seg=16)
rg.finish()
cu = Piece("Flat_Curtains")
for (y0, y1) in ((SLIDE_Y0 - 0.38, SLIDE_Y0 + 0.06), (SLIDE_Y1 - 0.06, SLIDE_Y1 + 0.38)):
    n = 7
    for k in range(n):                                                    # soft pleats
        y = y0 + (y1 - y0) * (k + 0.5) / n
        cu.cyl(LIV_X1 - 0.11 - 0.02 * (k % 2), y, 0.02, (y1 - y0) / n * 0.62, 2.27, M["curtain"], seg=12)
cu.tube((LIV_X1 - 0.1, SLIDE_Y0 - 0.45, 2.32), (LIV_X1 - 0.1, SLIDE_Y1 + 0.45, 2.32), 0.015, M["steel"])
cu.finish()
db = Piece("Flat_Dartboard", bevel=0.004)
db.box(7.95, LIV_Y0, 1.1, 8.5, LIV_Y0 + 0.02, 1.95, M["board_cream"])
db.cyl(8.225, LIV_Y0 + 0.02, 1.62, 0.22, 0.03, M["board"], seg=32, axis="Y")
db.cyl(8.225, LIV_Y0 + 0.021, 1.62, 0.16, 0.03, M["board_red"], seg=32, axis="Y")
db.cyl(8.225, LIV_Y0 + 0.022, 1.62, 0.11, 0.03, M["board"], seg=32, axis="Y")
db.cyl(8.225, LIV_Y0 + 0.023, 1.62, 0.02, 0.03, M["board_red"], seg=16, axis="Y")
db.finish()

# ---------------------------------------------------------------------------
# Export
# ---------------------------------------------------------------------------
bpy.ops.object.select_all(action="DESELECT")
for o in ROOT.all_objects:
    o.select_set(True)
bpy.ops.export_scene.gltf(filepath=EXPORT_GLB, use_selection=True, export_format="GLB", export_apply=True)
print("Flat built:", len(ROOT.all_objects), "objects ->", EXPORT_GLB)
