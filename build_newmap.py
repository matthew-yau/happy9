"""
The new map - Blender build script (clean modelled version)
============================================================
A separate flat (NOT joined to the house): bedroom, long living room, storage cupboard and a
wet room, laid out from the Scaniverse scan of the new area (scans/newmap.json, measured with the
scan-to-room skill's measure_scan.py / plan_render.py / extract_layout.py ->
scans/measure_new/, scans/plan_new/, scans/newmap_layout.json). Exports RoomGame/newmap.glb.

Run headless:  python3 build_newmap.py            (pip bpy)   or
               blender -b --factory-startup --python build_newmap.py

It reads the shared helpers and materials from build_flat.py (so every map looks alike).
Coordinates: metres, Blender (Z up), straightened so the walls run along X / Y; the west wall of
the bedroom is X 0, the living room's south wall is about Y 0.8..1.8. Floor at Z = 0.
main.gd puts the whole map at NEWMAP_OFFSET (far from the house), so these numbers stay as-is.
Godot = (x, z, -y).

Names the game uses (same as build_flat.py / build_ground.py):
  *-col            solid        NewMap_Light_N    ceiling light spots (follow the top light)
  Chair_N_*        E sits you   Door_N_*          doors E opens (main.gd DOOR_SWING)
  NewMap_TV_Screen / NewMap_PC_Screen   materials: the game shows the TV / computer picture there
  NewMap_Spawn     empty: where you appear when you pick this map
"""
import os
import math
import random

HERE = os.path.dirname(os.path.abspath(__file__))
_full = open(os.path.join(HERE, "build_flat.py"), encoding="utf-8").read()
_src = _full[:_full.index("# Layout (measured from the scan")]
_src = (_src.replace('PROJECT_DIR = r"C:\\Users\\thema\\Downloads\\newgame"', "PROJECT_DIR = %r" % HERE)
            .replace('COLLECTION_NAME = "MyFlat"', 'COLLECTION_NAME = "MyNewMap"')
            .replace('"flat.glb"', '"newmap.glb"')
            .replace("H = 2.42          # ceiling height", "H = 2.66          # ceiling height (new map)"))
exec(compile(_src, "build_flat.py (helpers)", "exec"))          # Piece, wall, frame, doors, M, ...
for _start, _end in (("def lounge(", "\n# dark leather sofa"), ("def office_chair(", '\noffice_chair("Chair_Desk"')):
    _a = _full.index(_start)
    exec(compile(_full[_a:_full.index(_end, _a)], "build_flat.py (" + _start[4:-1] + ")", "exec"))

random.seed(11)
T = 0.10

# --------------------------------------------------------------------------- extra materials
M.update({
    "oak":      material("NewMap_Floor_Oak", "#c9a679", 0.55),
    "olive":    material("NewMap_Fabric_Olive", "#5e6340", 0.95),
    "duvet":    material("NewMap_Duvet_Charcoal", "#33343a", 0.95),
    "beige":    material("NewMap_Fabric_Beige", "#b5a58f", 0.95),
    "grey_bag": material("NewMap_Beanbag_Teal", "#5f8a76", 1.0),
    "suit_pink": material("NewMap_Suitcase_Pink", "#d99aa8", 0.5),
    "tv_scr":   material("NewMap_TV_Screen", "#0c0c0f", 0.12),
    "pc_scr":   material("NewMap_PC_Screen", "#0c0c0f", 0.12),
    "led_blue": material("NewMap_LED_Blue", "#2f6bff", 0.3, emission="#2f6bff", strength=3.0),
    "bath_tile": material("NewMap_Wall_Tile", "#d8d6d0", 0.35),
})

# ---------------------------------------------------------------------------
# Layout (from the scan; final coordinates)
# ---------------------------------------------------------------------------
# bedroom            X 0.00..4.10   Y 4.70..7.30     door in its south wall (X 0.15..1.00)
# living room (L)    X 0.00..3.90   Y 1.77..4.60  +  X 3.85..8.10  Y 0.80..4.60
# storage cupboard   X 4.50..7.50   Y 4.70..5.50     opening in the living room's north wall
# wet room           X 8.20..9.72   Y 0.00..4.60     door in its west wall (Y 3.00..4.00)
BED_X0, BED_X1, BED_Y0, BED_Y1 = 0.0, 4.10, 4.70, 7.30
LIV_N = 4.60                       # living room's north wall (its south face is the room side)
CL_X0, CL_X1, CL_Y1 = 4.50, 7.50, 5.50
WET_X0, WET_X1 = 8.20, 9.72
LIV_S_W, LIV_S_E = 1.77, 0.80      # south wall lines (west part / east part)
LIV_X1 = 8.10                      # living room's east end = the wet room's west wall

# ------------------------------------------------------------------ floors, ceiling, outside
fl = Piece("NewMap_Floors", solid=True)
fl.box(0.0, LIV_S_W, -0.05, 3.90, LIV_N, 0.0, M["oak"])
fl.box(3.85, LIV_S_E, -0.05, LIV_X1, LIV_N, 0.0, M["oak"])
fl.box(BED_X0, BED_Y0, -0.05, BED_X1 + T, BED_Y1, 0.0, M["carpet"])
fl.box(CL_X0, LIV_N, -0.05, CL_X1, CL_Y1, 0.0, M["oak"])
fl.box(LIV_X1, 0.0, -0.05, WET_X1, LIV_N, 0.0, M["tile"])
fl.finish()

# one flat ceiling slab over everything (one piece per room outline)
ce = Piece("NewMap_Ceiling", solid=True)
for (x0, y0, x1, y1) in ((0.0, LIV_S_W, 3.90, LIV_N), (3.85, LIV_S_E, LIV_X1, LIV_N),
                         (BED_X0, BED_Y0, BED_X1 + T, BED_Y1), (CL_X0, LIV_N, CL_X1, CL_Y1),
                         (LIV_X1, 0.0, WET_X1, LIV_N)):
    ce.box(x0 - T, y0 - T, H, x1 + T, y1 + T, H + 0.05, M["ceiling"])
ce.finish()

# outside: a lawn to stand on if you ever get out, and a sky shell so windows never show the void
lawn = Piece("NewMap_Lawn", solid=True)
lawn.box(-25, -25, -0.40, 35, 35, -0.05, M["grass"])
lawn.finish()
sky = Piece("NewMap_Sky")
sky.box(-25, -25, -0.4, 35, 35, 22, M["sky"])
sky.finish()

# ------------------------------------------------------------------ walls
wl = Piece("NewMap_Walls", solid=True)
# bedroom: west, north (window), east, south (door)
wall(wl, -T, BED_Y0 - T, 0.0, BED_Y1 + T)                                              # west (bedroom)
wall(wl, -T, BED_Y1, BED_X1 + T, BED_Y1 + T, holes=[(3.10, 3.60, 0.90, 2.10)])         # north + window
wall(wl, BED_X1, BED_Y0 - T, BED_X1 + T, BED_Y1)                                       # east
# the long wall between bedroom / cupboard and the living room (Y 4.60..4.70)
wall(wl, -T, LIV_N, 8.20, LIV_N + T,
     holes=[(0.15, 1.00, 0, 2.04), (6.00, 7.00, 0, 2.04)])                             # bedroom door, cupboard opening
# living room: west wall (with a glass door out to a balcony), south walls, the little jog
wall(wl, -T, LIV_S_W - T, 0.0, LIV_N, holes=[(1.85, 2.95, 0, 2.10)])
wall(wl, -T, LIV_S_W - T, 3.90, LIV_S_W)
wall(wl, 3.85, LIV_S_E - T, 3.95, LIV_S_W)
wall(wl, 3.85, LIV_S_E - T, LIV_X1 + T, LIV_S_E, holes=[(5.20, 6.10, 0, 2.04)])         # front door
# cupboard walls
wall(wl, CL_X0 - T, LIV_N, CL_X0, CL_Y1 + T)
wall(wl, CL_X0 - T, CL_Y1, CL_X1 + T, CL_Y1 + T)
wall(wl, CL_X1, LIV_N, CL_X1 + T, CL_Y1 + T)
# wet room: west wall (door Y 3.00..4.00), south, east, north
wall(wl, LIV_X1, -T, LIV_X1 + T, LIV_N + T, holes=[(3.00, 4.00, 0, 2.04)])
wall(wl, LIV_X1, -T, WET_X1 + T, 0.0)
wall(wl, WET_X1, -T, WET_X1 + T, LIV_N + T)
wall(wl, LIV_X1, LIV_N, WET_X1 + T, LIV_N + T)
# tiles in the shower corner (south end of the wet room)
wl.box(WET_X0, 0.0, 0.0, WET_X1, 0.02, 2.10, M["bath_tile"])
wl.box(WET_X1 - 0.02, 0.0, 0.0, WET_X1, 0.90, 2.10, M["bath_tile"])
wl.finish()

# frames, window glass, the balcony glass door
tr = Piece("NewMap_Trim")
frame(tr, False, -T, 0.0, 1.85, 2.95, 0.0, 2.10)                      # glass door (west wall)
frame(tr, True, BED_Y1, BED_Y1 + T, 3.10, 3.60, 0.90, 2.10)           # bedroom window
frame(tr, True, LIV_N, LIV_N + T, 6.00, 7.00, 0.0, 2.04)              # cupboard opening
frame(tr, True, LIV_N, LIV_N + T, 0.15, 1.00, 0.0, 2.04)              # bedroom door
frame(tr, False, LIV_X1, LIV_X1 + T, 3.00, 4.00, 0.0, 2.04)           # wet room door
skirting(tr, [(0.0, LIV_S_W, 3.90, LIV_S_W, "+y"), (0.0, LIV_S_W, 0.0, LIV_N, "+x"),
              (4.0, LIV_S_E, LIV_X1, LIV_S_E, "+y"), (BED_X0, BED_Y0 + T, BED_X0, BED_Y1, "+x"),
              (BED_X0, BED_Y1, BED_X1, BED_Y1, "-y")])
tr.finish()
gl = Piece("NewMap_Glass")
gl.box(-0.04, 1.88, 0.02, -0.02, 2.92, 2.08, M["glass"])               # balcony door (sliding)
gl.box(-0.07, 1.88, 0.02, -0.05, 2.40, 2.08, M["glass"])
gl.box(3.12, BED_Y1 + 0.04, 0.92, 3.58, BED_Y1 + 0.06, 2.08, M["glass"])
gl.finish()
# a shut front door
fd = Piece("NewMap_Front_Door", solid=True)
closed_door(fd, True, LIV_S_E - T, LIV_S_E, 5.20, 6.10, handle_side=1)
fd.finish()
# doors that open with E: hinge on the post, leaf runs along the hole
hinged_door("Door_N_Bedroom", 1.00, LIV_N + T / 2, "-x", 0.85)         # opens into the bedroom
hinged_door("Door_N_Wet", LIV_X1 + T / 2, 4.00, "-y", 1.00)            # opens into the wet room

# ------------------------------------------------------------------ bedroom
bd = Piece("NewMap_Bed", solid=True, bevel=0.006)
bd.rbox(1.00, 4.98, 0.10, 2.80, 7.28, 0.32, M["wood_lt"], r=0.02)                      # frame
bd.rbox(1.00, 7.20, 0.10, 2.80, 7.28, 1.00, M["wood_lt"], r=0.02)                      # headboard
bd.rbox(1.04, 5.02, 0.32, 2.76, 7.20, 0.52, M["linen"], r=0.05, seg=3)                 # mattress
bd.rbox(1.02, 5.02, 0.50, 2.78, 6.55, 0.64, M["duvet"], r=0.07, seg=4)                 # duvet
for (xa, xb) in ((1.12, 1.88), (1.92, 2.68)):
    bd.rbox(xa, 6.72, 0.52, xb, 7.17, 0.68, M["plush"], r=0.07, seg=4)                 # pillows
bd.finish()
db = Piece("NewMap_Daybed", solid=True, bevel=0.006)
db.rbox(2.85, 5.00, 0.10, 3.98, 7.20, 0.36, M["wood_lt"], r=0.02)
db.rbox(2.88, 5.03, 0.36, 3.95, 7.17, 0.48, M["beige"], r=0.05, seg=3)
db.rbox(2.95, 6.55, 0.48, 3.75, 7.12, 0.62, M["plush"], r=0.07, seg=4)
db.finish()
bs = Piece("NewMap_Bedside", solid=True, bevel=0.006)
bs.rbox(0.10, 6.75, 0.0, 0.55, 7.25, 0.52, M["wood_dark"], r=0.015)
bs.cyl(0.32, 7.0, 0.52, 0.06, 0.03, M["black"], seg=14)
bs.cyl(0.32, 7.0, 0.55, 0.012, 0.28, M["black"], seg=8)
bs.cyl(0.32, 7.0, 0.83, 0.10, 0.16, M["plush"], r_top=0.07, seg=18)
bs.finish()
rg = Piece("NewMap_Rug")
rg.rbox(0.9, 4.85, 0.0, 2.9, 5.05, 0.012, M["rug_blue"], r=0.003, seg=1)
rg.finish()
# built-in wardrobe on the bedroom's south wall, east of the door
wd = Piece("NewMap_Wardrobe", solid=True, bevel=0.004)
wd.rbox(1.20, BED_Y0, 0.0, 2.80, BED_Y0 + 0.02, 2.30, M["white"], r=0.003, seg=1)
wd.finish()
wr = Piece("NewMap_Shelf", solid=True, bevel=0.004)
for z in (0.0, 0.45, 0.90, 1.35):
    wr.box(0.05, 5.15, z, 0.42, 5.95, z + 0.025, M["white"])
wr.box(0.05, 5.15, 0.0, 0.07, 5.95, 1.40, M["white"])
wr.box(0.40, 5.15, 0.0, 0.42, 5.95, 1.40, M["white"])
wr.finish()

# ------------------------------------------------------------------ living room
def turn(objs, cx, cy, deg):
    R = Matrix.Translation((cx, cy, 0)) @ Matrix.Rotation(math.radians(deg), 4, "Z") @ Matrix.Translation((-cx, -cy, 0))
    for o in objs:
        o.matrix_basis = R @ o.matrix_basis


def sofa(prefix, cx, cy, width, depth, facing, cover, seats):
    x0, x1, y0, y1 = cx - width / 2, cx + width / 2, cy - depth / 2, cy + depth / 2
    body, seats_ = lounge(prefix, x0, y0, x1, y1, cover, seats, arm_w=0.2)
    objs = [body.finish()] + [s.finish() for s in seats_]
    turn(objs, cx, cy, {"+y": 0, "-y": 180, "+x": -90, "-x": 90}[facing])
    return objs


def table(name, x0, y0, x1, y1, top=0.75, mat=None, leg=0.03, th=0.04):
    p = Piece(name, solid=True, bevel=0.006)
    p.rbox(x0, y0, top - th, x1, y1, top, mat or M["wood_lt"], r=0.012)
    for (fx, fy) in ((x0 + 0.05, y0 + 0.05), (x1 - 0.05, y0 + 0.05), (x0 + 0.05, y1 - 0.05), (x1 - 0.05, y1 - 0.05)):
        p.cyl(fx, fy, 0, leg / 2, top - th, M["steel"], seg=10)
    return p.finish()


# olive sofa against the north wall (facing the TV), dark armchair at its west end
sofa("N_Sofa", 2.65, 4.07, 2.50, 0.95, "-y", M["olive"], 3)
sofa("N_Armchair", 0.62, 3.35, 0.95, 0.90, "+x", M["leather"], 1)
table("NewMap_Coffee_Table", 2.05, 2.55, 3.45, 3.20, top=0.42, mat=M["wood_dark"])
cr = Piece("NewMap_Living_Rug")
cr.rbox(1.6, 2.35, 0.0, 3.9, 3.5, 0.012, M["rug_blue"], r=0.004, seg=1)
cr.finish()

# Wooden sideboard along the south wall (the real place uses a projector, not a TV)
tu = Piece("NewMap_TV_Unit", solid=True, bevel=0.006)
tu.rbox(0.35, LIV_S_W + 0.02, 0.0, 3.80, LIV_S_W + 0.50, 0.46, M["white"], r=0.012)
tu.cyl(3.0, LIV_S_W + 0.25, 0.46, 0.03, 0.05, M["led_blue"], seg=10)                       # blue LED strip
tu.finish()
# Dark roller blind pulled down over the south wall — acts as the projection screen
rb = Piece("NewMap_Roller_Blind")
rb.box(0.55, LIV_S_W - 0.005, 0.50, 2.90, LIV_S_W + 0.0005, 2.0, M["duvet"])
rb.finish()
# Projector screen quad: the game places the TV browser overlay here (material NewMap_TV_Screen)
prj_scr = Piece("NewMap_Projector_Screen")
prj_scr.box(0.65, LIV_S_W + 0.001, 0.58, 2.80, LIV_S_W + 0.004, 1.72, M["tv_scr"])
prj_scr.finish()
# Small projector body sitting on the coffee table, aimed at the blind
prj = Piece("NewMap_Projector", solid=True, bevel=0.005)
prj.rbox(2.62, 2.75, 0.42, 2.82, 2.95, 0.50, M["black"], r=0.015)
prj.finish()

# desk with a laptop + monitor in the south-east corner, white chair
ds = Piece("NewMap_Desk", solid=True, bevel=0.006)
ds.rbox(3.95, 0.85, 0.71, 5.25, 1.55, 0.75, M["wood_lt"], r=0.012)
for (fx, fy) in ((4.0, 0.9), (5.2, 0.9), (4.0, 1.5), (5.2, 1.5)):
    ds.cyl(fx, fy, 0, 0.02, 0.71, M["steel"], seg=12)
ds.rbox(4.45, 1.45, 0.75, 4.95, 1.48, 1.10, M["black"], r=0.008, seg=2)                    # monitor (faces +Y)
ds.box(4.47, 1.481, 0.78, 4.93, 1.484, 1.08, M["pc_scr"])
ds.rbox(4.66, 1.38, 0.75, 4.72, 1.45, 0.92, M["black"], r=0.01)
ds.rbox(4.45, 1.00, 0.75, 4.95, 1.18, 0.765, M["black"], r=0.006)                          # keyboard
ds.finish()
office_chair("Chair_N_Desk", 4.60, 2.10, -90, blanket=None)

# bean bag + round stool
bb = Piece("NewMap_Beanbag", solid=True)
bb.sphere(4.85, 3.05, 0.34, 0.52, M["grey_bag"], scale=(1, 1, 0.68), seg=20)
bb.finish()
bbs = Piece("Chair_N_Beanbag", origin=(4.85, 3.05, 0), solid=True, rot=90)
bbs.sphere(4.85, 3.05, 0.32, 0.30, M["grey_bag"], scale=(1, 1, 0.5), seg=14)
bbs.finish()

# brown cupboard + low white shelf + luggage along the east side of the living room
cb = Piece("NewMap_Cupboard", solid=True, bevel=0.006)
cb.rbox(5.62, 1.55, 0.0, 6.15, 2.30, 0.95, M["cowhide"], r=0.012)
cb.rbox(5.62, 2.45, 0.0, 6.00, 3.40, 0.55, M["white"], r=0.01)
cb.finish()
lg = Piece("NewMap_Luggage", solid=True, bevel=0.008)
lg.rbox(5.75, 0.85, 0.0, 6.35, 1.15, 0.62, M["suit_pink"], r=0.04, seg=3)
lg.rbox(6.45, 0.88, 0.0, 6.95, 1.20, 0.50, M["black"], r=0.04, seg=3)
lg.rbox(6.5, 1.30, 0.0, 7.2, 1.62, 0.34, M["suitcase"], r=0.03, seg=3)
lg.finish()

# dining table in the U-shaped corner, four chairs
table("NewMap_Dining_Table", 6.40, 2.30, 7.60, 3.20, top=0.74, mat=M["white"])
for k, (cx, cy, rot) in enumerate(((6.7, 2.05, 90), (7.3, 2.05, 90), (6.7, 3.45, -90), (7.3, 3.45, -90))):
    ch = Piece("Chair_N_Dining_%d" % (k + 1), origin=(cx, cy, 0), solid=True, rot=rot, bevel=0.005)
    ch.rbox(cx - 0.21, cy - 0.21, 0.42, cx + 0.21, cy + 0.21, 0.46, M["wood_lt"], r=0.012)
    ch.rbox(cx - 0.21, cy - 0.21, 0.46, cx - 0.17, cy + 0.21, 0.92, M["wood_lt"], r=0.012)
    for (lx, ly) in ((-0.18, -0.18), (0.18, -0.18), (-0.18, 0.18), (0.18, 0.18)):
        ch.cyl(cx + lx, cy + ly, 0, 0.018, 0.42, M["wood_lt"], seg=8)
    ch.finish()

# AC unit on the north wall of the living room (visible in the reference photos, top-right)
ac = Piece("NewMap_AC", solid=True, bevel=0.008)
ac.rbox(2.5, LIV_N - 0.015, 1.75, 3.1, LIV_N, 2.05, M["white"], r=0.025)
ac.finish()

# ------------------------------------------------------------------ storage cupboard
sh = Piece("NewMap_Cupboard_Shelves", solid=True, bevel=0.004)
for z in (0.0, 0.40, 0.80, 1.20, 1.60, 2.0):
    sh.box(CL_X0 + 0.02, CL_Y1 - 0.40, z, CL_X1 - 0.02, CL_Y1 - 0.02, z + 0.03, M["wood_lt"])
for k in range(5):
    sh.rbox(CL_X0 + 0.15 + k * 0.58, CL_Y1 - 0.36, 0.40, CL_X0 + 0.55 + k * 0.58, CL_Y1 - 0.05, 0.80 + 0.2 * (k % 2),
            random.choice([M["box_card"], M["shirt_b"], M["shirt_a"]]), r=0.02)
sh.finish()

# ------------------------------------------------------------------ wet room
wt = Piece("NewMap_Wet_Room", solid=True, bevel=0.005)
wt.rbox(9.38, 2.00, 0.0, WET_X1, 3.00, 0.84, M["white"], r=0.012)                          # vanity
wt.rbox(9.45, 2.25, 0.84, 9.68, 2.75, 0.89, M["porcelain"], r=0.03, seg=3)                  # basin
wt.cyl(9.62, 2.50, 0.89, 0.012, 0.22, M["steel"], seg=8)                                   # tap
wt.rbox(9.60, 1.18, 0.0, WET_X1, 1.52, 0.78, M["porcelain"], r=0.04, seg=3)                  # cistern
wt.rbox(9.18, 1.22, 0.0, 9.60, 1.48, 0.42, M["porcelain"], r=0.06, seg=3)                  # toilet bowl
wt.rbox(9.20, 1.20, 0.42, 9.60, 1.50, 0.46, M["white"], r=0.012)                           # seat
wt.rbox(WET_X0, 0.0, 0.0, WET_X1, 0.86, 0.06, M["dark_tile"], r=0.004, seg=1)              # shower tray
wt.box(WET_X0, 0.86, 0.0, WET_X1, 0.88, 2.0, M["glass"])                                   # glass screen
wt.tube((WET_X1 - 0.06, 0.2, 1.2), (WET_X1 - 0.06, 0.2, 2.0), 0.012, M["steel"])           # shower pipe
wt.finish()
bm = Piece("NewMap_Bath_Mat")
bm.rbox(8.30, 1.00, 0.0, 8.95, 1.70, 0.015, M["bathmat"], r=0.004, seg=1)
bm.finish()
sr = Piece("NewMap_Shoe_Rack", solid=True, bevel=0.004)
for z in (0.0, 0.30, 0.60):
    sr.box(9.0, 3.28, z, 9.68, 3.62, z + 0.02, M["steel"])
for (x, y) in ((9.0, 3.28), (9.68, 3.28), (9.0, 3.62), (9.68, 3.62)):
    sr.cyl(x, y, 0, 0.01, 0.62, M["steel"], seg=8)
for k in range(6):
    sr.rbox(9.04 + k * 0.1, 3.32, 0.30, 9.12 + k * 0.1, 3.58, 0.38, random.choice([M["box_card"], M["black"], M["shirt_b"]]), r=0.02)
sr.finish()

# ------------------------------------------------------------------ ceiling lights (+ markers)
LIGHTS = [(2.1, 6.0), (1.6, 3.2), (4.7, 2.5), (6.5, 3.3), (6.0, 5.1), (9.0, 2.2)]
lamps = Piece("NewMap_Ceiling_Lamps")
for i, (x, y) in enumerate(LIGHTS):
    lamps.sphere(x, y, H - 0.02, 0.16, M["diffuser"], scale=(1, 1, 0.35), seg=24)
    lamps.cyl(x, y, H - 0.012, 0.18, 0.012, M["white"], seg=28)
    marker("NewMap_Light_%d" % i, x, y, H - 0.1)
lamps.finish()

# where you appear: in the living room, looking at the TV wall
marker("NewMap_Spawn", 3.0, 3.9, 0.05)

# ------------------------------------------------------------------ export
bpy.ops.object.select_all(action="DESELECT")
for o in ROOT.all_objects:
    o.select_set(True)
bpy.ops.export_scene.gltf(filepath=EXPORT_GLB, use_selection=True, export_format="GLB", export_apply=True)
print("New map built:", len(ROOT.all_objects), "objects ->", EXPORT_GLB)
