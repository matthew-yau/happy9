"""
The ground floor (downstairs) - Blender build script (clean modelled version)
==============================================================================
Builds the ground floor - long hall, dining room + kitchen + island, wet kitchen, pantry,
laundry, bathroom, TV room, living room, study and the west room - as clean modelled shapes,
laid out 1:1 from the Scaniverse scan ground_scan.fbx (lined up with the flat by its stairs
- scans/ground.json, scans/register_ground.json; measured with the scan-to-room skill's
extract_layout.py -> scans/ground_layout.json and the plan tiles in scans/plan_ground4/).
Exports RoomGame/ground.glb.

Run headless:  blender -b --factory-startup --python build_ground.py
(it reads the shared helpers and materials from build_flat.py, so both floors look alike)

Coordinates are the bedroom's (metres): same X / Y as the flat. Everything is modelled with
this floor at Z = 0 and moved down to GROUND_Z (-2.76) at the end. Godot = (x, z, -y).
The stairs themselves are in flat.glb (build_flat.py): they land here at X 2.05, Y 3.75..5.35.

Names the game uses (same as build_flat.py):
  *-col            solid        Ground_Light_N   ceiling light spots (follow the top light)
  Chair_*          E sits you   Door_G_*         doors E opens (main.gd DOOR_SWING)
  Ceiling_Light_Diffuser  lamp shades that glow with the top light
"""
import os

PROJECT_DIR = r"C:\Users\thema\Downloads\newgame"
_src = open(os.path.join(PROJECT_DIR, "build_flat.py"), encoding="utf-8").read()
_src = _src[:_src.index("# Layout (measured from the scan")]
_src = (_src.replace('EXPORT_GLB = os.path.join(PROJECT_DIR, "RoomGame", "flat.glb")',
                     'EXPORT_GLB = os.path.join(PROJECT_DIR, "RoomGame", "ground.glb")')
            .replace('COLLECTION_NAME = "MyFlat"', 'COLLECTION_NAME = "MyGround"')
            .replace("H = 2.42          # ceiling height", "H = 2.68          # ceiling height (ground floor)"))
exec(compile(_src, "build_flat.py (helpers)", "exec"))          # Piece, wall, frame, doors, M, ...
# ... and its furniture helpers (sofas / armchairs, office chairs), defined further down in it
_full = open(os.path.join(PROJECT_DIR, "build_flat.py"), encoding="utf-8").read()
for _start, _end in (("def lounge(", "\n# dark leather sofa"), ("def office_chair(", '\noffice_chair("Chair_Desk"')):
    _a = _full.index(_start)
    exec(compile(_full[_a:_full.index(_end, _a)], "build_flat.py (" + _start[4:-1] + ")", "exec"))

GROUND_Z = -2.76      # this floor's level (the flat's floor is 0)

GROUND_Z = -2.76      # this floor's level (the flat's floor is 0)
T = 0.10

M.update({
    # (laid out / coloured from the scan and the user's reference photos, 2026-11-19)
    "wall":      material("Ground_Wall_Paint", "#d7dbdc", 0.9),         # pale grey walls downstairs
    "g_wood":    material("Ground_Floor_Wood", "#a8703f", 0.45),        # honey spotted-gum boards
    "g_deck":    material("Ground_Deck_Wood", "#6b3a26", 0.7),          # sunroom deck
    "g_tile":    material("Ground_Floor_Tile_Grey", "#8d8a86", 0.4),   # bathroom
    "g_tile_w":  material("Ground_Floor_Tile_White", "#d9d7d2", 0.35),  # laundry
    "g_subway":  material("Ground_Subway_Tile", "#f1f1ee", 0.25),
    "g_sofa":    material("Ground_Sofa_Grey", "#6c6b69", 0.95),        # living room sectional
    "g_sofa_dk": material("Ground_Sofa_Charcoal", "#45474d", 0.95),     # TV room
    "g_rug_red": material("Ground_Rug_Red", "#8e1f2a", 1.0),
    "g_rug_dk":  material("Ground_Rug_Dark", "#3a322c", 1.0),
    "g_rug_gr":  material("Ground_Rug_Grey", "#8f9194", 1.0),
    "g_mat":     material("Ground_Doormat", "#7d7a75", 1.0),
    "g_worktop": material("Ground_Worktop", "#eeede8", 0.25),
    "g_cab":     material("Ground_Cabinet_White", "#f3f2ee", 0.35),
    "g_hob":     material("Ground_Hob_Black", "#161618", 0.15),
    "g_tv":      material("Ground_TV_Screen", "#0c0c0f", 0.12),         # living-room TV  (main.gd: device tv_g)
    "g_tv2":     material("Ground_TV2_Screen", "#0c0c0f", 0.12),        # TV-room TV       (tv_g2)
    "g_pc":      material("Ground_PC_Screen", "#0c0c0f", 0.12),         # study monitor    (pc_g)
    "g_cushion": material("Ground_Cushion_Blue", "#2f4473", 0.95),
    "g_throw":   material("Ground_Throw_Cream", "#e2ddd3", 0.95),
    "g_stripe":  material("Ground_Cushion_Stripe", "#b9b1a2", 0.95),
    "g_bath":    material("Ground_Bath_Grey", "#5d5f63", 0.3),
    "g_placemat": material("Ground_Placemat", "#55595f", 0.9),
    "g_timber":  material("Ground_Dark_Timber", "#3f1f15", 0.45),       # front door, console, dining
    "g_feature": material("Ground_Feature_Wall", "#26272b", 0.6),       # black TV wall
    "g_rattan":  material("Ground_Rattan", "#3d3a37", 0.85),
    "g_stainless": material("Ground_Stainless", "#c4c7ca", 0.35, metallic=0.35),
    "g_tank":    material("Ground_Aquarium", "#2b3cff", 0.1, emission="#4a3cff", strength=2.5, alpha=0.55),
    "g_coral":   material("Ground_Coral", "#3fe0c0", 0.6, emission="#3fe0c0", strength=0.6),
    "g_curtain": material("Ground_Curtain_Grey", "#6c6e7c", 0.95),
    "g_noren":   material("Ground_Noren_Navy", "#1f2433", 0.95),
    "g_bulkhead": material("Ground_Bulkhead_Grey", "#9c9a96", 0.9),
    "g_plant":   material("Ground_Plant_Green", "#4f8a3a", 0.9),
    "g_night":   material("Ground_Painting_Night", "#1d3b8c", 0.8),
    "g_swirl":   material("Ground_Painting_Swirl", "#6f97d4", 0.8),
    "g_star":    material("Ground_Painting_Star", "#f2d64b", 0.6, emission="#f2d64b", strength=0.4),
    "g_cypress": material("Ground_Painting_Cypress", "#1b1d1a", 0.9),
})

# ---------------------------------------------------------------------------
# Layout (final X / Y; see the docstring)
# ---------------------------------------------------------------------------
XW, XE = -8.45, 10.55         # outside walls (inner faces): west, east (TV room: under the
                              #   flat's living-room wall - the scan had it 0.3 m further out)
YS, YN = 0.10, 9.20           # south, north
HALL_S_E = 3.75               # hall south wall, east part (beside / past the stairs)
HALL_N = 6.15                 # hall north wall (pantry, laundry, bathroom, TV room)
HALL_E = 9.15                 # east end of the hall (front door)
SUN_N = 4.45                  # the sunroom's north wall (sliding door into the dining room)
LIV_W, LIV_E = -5.0, 0.10     # living room west (sunroom sliding door) / east walls
STUDY_N = 3.44                # the study's north wall (door from the hall)
STUDY_E = 3.45
STAIR_X0, STAIR_X1, STAIR_Y0, STAIR_Y1 = 2.05, 5.50, 3.75, 5.35   # (stairs: flat.glb)
FLIGHT_Y1 = STAIR_Y0 + 1.10                                        # the flight is 1.1 m wide
KIT_E = -0.55                 # east end wall of the kitchen (scullery doorway + fridge recess)
SCUL_X1, SCUL_Y0 = 1.68, 7.55 # scullery (butler's pantry)
PAN_X0 = 0.40                 # walk-in pantry X 0.40..1.73, Y 6.25..7.45
LAUN_X0, LAUN_X1 = 1.73, 4.28
BATH_X1 = 6.12

STUDY_DOOR = (1.30, 2.10)
LAUN_DOOR = (2.60, 3.40)
BATH_DOOR = (5.10, 5.90)
TV_OPEN = (6.30, 7.30)
FRONT_DOOR = (3.88, 4.78)     # in the hall's east wall, with the sidelight beside it
SIDELIGHT = (4.90, 5.75)
GARAGE_DOOR = (6.10, 6.92)    # in the hall's south wall (dark timber + glass)
SCUL_DOOR = (7.65, 8.50)      # in the kitchen's end wall (noren curtain)
PANTRY_DOOR = (0.50, 1.08)    # from the scullery into the walk-in pantry
SUN_DOOR_N = (-7.40, -5.90)   # sliding door: sunroom | dining
SUN_DOOR_E = (1.70, 3.50)     # sliding door: sunroom | living room

# ---------------------------------------------------------------- floors + ceiling
fl = Piece("Ground_Floor", solid=True)
fl.box(XW - T, YS - T, -0.06, LIV_W, SUN_N, -0.025, M["g_deck"])                    # sunroom (deck below)
fl.box(LIV_W, YS - T, -0.06, STUDY_E + T, HALL_N + 0.05, 0, M["g_wood"])            # living, study, hall west
fl.box(XW - T, SUN_N, -0.06, LAUN_X0, YN + T, 0, M["g_wood"])                       # dining, kitchen, scullery, pantry
fl.box(STUDY_E, HALL_S_E - T, -0.06, HALL_E + T, HALL_N + 0.05, 0, M["g_wood"])     # hall east
fl.box(LAUN_X0, HALL_N, -0.06, LAUN_X1, YN + T, 0, M["g_tile_w"])                   # laundry
fl.box(LAUN_X1, HALL_N, -0.06, BATH_X1, YN + T, 0, M["g_tile"])                     # bathroom
fl.box(BATH_X1, HALL_N, -0.06, XE + T, YN + T, 0, M["g_wood"])                      # TV room
fl.finish()
dk_ = Piece("Ground_Sunroom_Deck", solid=True)                                       # deck boards
x = XW
while x < LIV_W - 0.01:
    dk_.box(x + 0.004, YS, -0.025, min(x + 0.135, LIV_W), SUN_N, 0.0, M["g_deck"])
    x += 0.14
dk_.finish()

ce = Piece("Ground_Ceiling", solid=True)
# one slab with the stair well left open (the flight comes down through it)
for (x0, y0, x1, y1) in ((XW - T, YS - T, STAIR_X0, YN + T), (STAIR_X1 + T, YS - T, XE + T, YN + T),
                         (STAIR_X0, YS - T, STAIR_X1 + T, STAIR_Y0), (STAIR_X0, STAIR_Y1 + T, STAIR_X1 + T, YN + T)):
    ce.box(x0, y0, H, x1, y1, H + 0.02, M["ceiling"])
ce.finish()
# the sunroom's grey bulkhead round its glass walls
bh = Piece("Ground_Sunroom_Bulkhead")
bh.box(XW, YS, H - 0.42, LIV_W, YS + 0.28, H, M["g_bulkhead"])
bh.box(XW, YS, H - 0.42, XW + 0.28, SUN_N, H, M["g_bulkhead"])
bh.finish()

# ---------------------------------------------------------------- walls
wl = Piece("Ground_Walls", solid=True)
WIN = 0.9, 2.1                # window sill / head
DIN_WIN = (5.55, 8.05)        # big shuttered window in the dining room's west wall
LIV_WIN = (-2.95, -1.70)      # shuttered window behind the living-room TV
KIT_WIN = (-4.40, -1.60)      # long low strip window over the kitchen bench
SCUL_WIN = (-0.35, 0.75)      # over the scullery hob
TV_WINS = [(7.03 - 0.21, 7.03 + 0.21), (7.67 - 0.21, 7.67 + 0.21), (8.31 - 0.21, 8.31 + 0.21)]
# outside
wall(wl, XW - T, YS - T, STUDY_E + T, YS,
     holes=[(XW + 0.30, LIV_W - 0.05, 0.05, H - 0.42), (LIV_WIN[0], LIV_WIN[1], *WIN)])      # south (sunroom all glass)
wall(wl, XW - T, YS - T, XW, YN + T,
     holes=[(YS + 0.30, SUN_N - 0.05, 0.05, H - 0.42), (DIN_WIN[0], DIN_WIN[1], 0.85, 2.15)])  # west
wall(wl, XW - T, YN, XE + T, YN + T, holes=[(KIT_WIN[0], KIT_WIN[1], 1.0, 1.45), (SCUL_WIN[0], SCUL_WIN[1], 1.0, 1.45)])
wall(wl, STUDY_E, YS - T, STUDY_E + T, HALL_S_E)                                             # study east
wall(wl, STUDY_E, HALL_S_E - T, HALL_E + T, HALL_S_E, holes=[(GARAGE_DOOR[0], GARAGE_DOOR[1], 0, 2.04)])  # hall south
wall(wl, HALL_E, HALL_S_E - T, HALL_E + T, HALL_N,
     holes=[(FRONT_DOOR[0], FRONT_DOOR[1], 0, 2.1), (SIDELIGHT[0], SIDELIGHT[1], 0.05, 2.1)])  # hall east
wall(wl, XE, HALL_N, XE + T, YN + T, holes=[(a, b, 0.08, 2.2) for (a, b) in TV_WINS])        # TV room east
wall(wl, HALL_E, HALL_N - T, XE + T, HALL_N)                                                 # TV room south (outside)
# inside
wall(wl, XW, SUN_N, LIV_W + T, SUN_N + T, holes=[(SUN_DOOR_N[0], SUN_DOOR_N[1], 0, 2.15)])   # sunroom | dining
wall(wl, LIV_W, YS, LIV_W + T, SUN_N, holes=[(SUN_DOOR_E[0], SUN_DOOR_E[1], 0, 2.15)])       # sunroom | living
wall(wl, LIV_E - T, YS, LIV_E, 4.60)                                                         # living | wardrobe/study
wall(wl, LIV_E, STUDY_N, STUDY_E, STUDY_N + T, holes=[(STUDY_DOOR[0], STUDY_DOOR[1], 0, 2.04)])
wall(wl, KIT_E, HALL_N, 1.85, HALL_N + T)                                                    # fridge recess / pantry | hall
wall(wl, 1.85, HALL_N, BATH_X1 + T, HALL_N + T,
     holes=[(LAUN_DOOR[0], LAUN_DOOR[1], 0, 2.04), (BATH_DOOR[0], BATH_DOOR[1], 0, 2.04)])    # hall north
wall(wl, BATH_X1 + T, HALL_N, HALL_E, HALL_N + T, holes=[(TV_OPEN[0], TV_OPEN[1], 0, 2.15)])
wall(wl, KIT_E - T, 7.45, KIT_E, YN, holes=[(SCUL_DOOR[0], SCUL_DOOR[1], 0, 2.04)])         # kitchen end wall
wall(wl, KIT_E, 7.45, 0.40, 7.55)                                                            # top of the fridge recess
wall(wl, 0.30, HALL_N + T, PAN_X0, 7.55)                                                     # fridge recess | pantry
wall(wl, PAN_X0, 7.45, 1.73, SCUL_Y0, holes=[(PANTRY_DOOR[0], PANTRY_DOOR[1], 0, 2.04)])    # pantry | scullery
wl.box(KIT_E, 6.25, 2.05, 0.30, 7.45, H, M["wall"])                                          # over the fridge
wall(wl, SCUL_X1, SCUL_Y0, LAUN_X0, YN)                                                      # scullery | laundry
wall(wl, 1.73, HALL_N, 1.85, SCUL_Y0)                                                        # pantry | laundry
wall(wl, LAUN_X1 - 0.05, HALL_N + T, LAUN_X1 + 0.05, YN)                                     # laundry | bathroom
wall(wl, BATH_X1, HALL_N + T, BATH_X1 + T, YN)                                               # bathroom | TV room
# the bathroom: tiles to 1.2 m
for (x0, y0, x1, y1) in ((LAUN_X1 + 0.05, YN - 0.01, BATH_X1, YN), (LAUN_X1 + 0.05, HALL_N + T, LAUN_X1 + 0.06, YN),
                         (BATH_X1 - 0.01, HALL_N + T, BATH_X1, YN)):
    wl.box(x0, y0, 0, x1, y1, 1.2, M["wall_tile"])
wl.box(LAUN_X1 + 0.05, HALL_N + T, 0, BATH_DOOR[0] - 0.07, HALL_N + T + 0.01, 1.2, M["wall_tile"])
wl.box(BATH_DOOR[1] + 0.07, HALL_N + T, 0, BATH_X1, HALL_N + T + 0.01, 1.2, M["wall_tile"])
wl.box(BATH_X1 + T, HALL_N + T, 0, XE, HALL_N + T + 0.03, H, M["g_feature"])                 # TV room black wall
for k in range(1, 5):                                                                        # its panel joints
    xx = BATH_X1 + T + k * (XE - BATH_X1 - T) / 5
    wl.box(xx - 0.003, HALL_N + T + 0.03, 0, xx + 0.003, HALL_N + T + 0.034, H, M["black"])
# scullery splashback: white subway tiles
wl.box(KIT_E, YN - 0.012, 0.9, SCUL_X1, YN, 1.55, M["g_subway"])
wl.box(SCUL_X1 - 0.012, SCUL_Y0, 0.9, SCUL_X1, YN, 1.55, M["g_subway"])
wl.finish()

# trim: skirting, frames
tr = Piece("Ground_Trim", bevel=0.004)
skirting(tr, [
    (LIV_W + T, YS, LIV_E - T, 0, "+y"), (XW, SUN_N + T, SUN_DOOR_N[0] - 0.07, 0, "+y"),
    (SUN_DOOR_N[1] + 0.07, SUN_N + T, LIV_W, 0, "+y"), (XW, SUN_N + T, 0, YN, "+x"), (XW, YN, -4.6, 0, "-y"),
    (LIV_W + T, YS, 0, SUN_DOOR_E[0] - 0.07, "+x"), (LIV_W + T, SUN_DOOR_E[1] + 0.07, 0, SUN_N, "+x"),
    (LIV_E - T, YS, 0, 4.6, "-x"), (STUDY_E, HALL_S_E, GARAGE_DOOR[0] - 0.07, 0, "+y"),
    (GARAGE_DOOR[1] + 0.07, HALL_S_E, HALL_E, 0, "+y"),
    (HALL_E, HALL_S_E, 0, FRONT_DOOR[0] - 0.07, "-x"), (HALL_E, SIDELIGHT[1] + 0.07, 0, HALL_N, "-x"),
    (KIT_E, HALL_N, 1.85, 0, "-y"),
    (BATH_X1 + T, HALL_N, TV_OPEN[0] - 0.07, 0, "-y"), (TV_OPEN[1] + 0.07, HALL_N, HALL_E, 0, "-y"),
    (BATH_X1 + T, YN, XE, 0, "-y"), (BATH_X1 + T, HALL_N + T, 0, YN, "+x"),
])
cornice(tr, [
    (LIV_W + T, YS, LIV_E - T, 0, "+y"), (XW, SUN_N + T, KIT_E, 0, "+y"), (STUDY_E, HALL_S_E, HALL_E, 0, "+y"),
    (KIT_E, HALL_N, BATH_X1, 0, "-y"), (BATH_X1 + T, HALL_N, HALL_E, 0, "-y"),
    (BATH_X1 + T, HALL_N + T, XE, 0, "+y"), (BATH_X1 + T, YN, XE, 0, "-y"),
])
frame(tr, True, STUDY_N, STUDY_N + T, STUDY_DOOR[0], STUDY_DOOR[1], 0, 2.04)
frame(tr, True, HALL_N, HALL_N + T, LAUN_DOOR[0], LAUN_DOOR[1], 0, 2.04)
frame(tr, True, HALL_N, HALL_N + T, BATH_DOOR[0], BATH_DOOR[1], 0, 2.04)
frame(tr, True, HALL_N, HALL_N + T, TV_OPEN[0], TV_OPEN[1], 0, 2.15)
frame(tr, False, KIT_E - T, KIT_E, SCUL_DOOR[0], SCUL_DOOR[1], 0, 2.04)
frame(tr, True, 7.45, SCUL_Y0, PANTRY_DOOR[0], PANTRY_DOOR[1], 0, 2.04)
frame(tr, False, XW - T, XW, DIN_WIN[0], DIN_WIN[1], 0.85, 2.15)
frame(tr, True, YS - T, YS, LIV_WIN[0], LIV_WIN[1], *WIN)
frame(tr, False, HALL_E, HALL_E + T, SIDELIGHT[0], SIDELIGHT[1], 0.05, 2.1)
for (a, b) in TV_WINS:
    frame(tr, False, XE, XE + T, a, b, 0.08, 2.2)
tr.finish()


# ---------------------------------------------------------------- windows: glass, white plantation shutters
gl = Piece("Ground_Window_Glass")
sh = Piece("Ground_Shutters", bevel=0.002)


def shutters(along_x, line, a0, a1, z0, z1, side, panels):
    """White plantation shutters filling a window (side: +1 / -1 = which way the room is)."""
    w = (a1 - a0) / panels
    f = line + side * 0.03
    for k in range(panels):
        b0, b1 = a0 + k * w + 0.005, a0 + (k + 1) * w - 0.005
        for (c0, c1) in ((z0, z0 + 0.03), (z1 - 0.03, z1)):                         # rails
            if along_x:
                sh.box(b0, f - 0.015, c0, b1, f + 0.015, c1, M["trim"])
            else:
                sh.box(f - 0.015, b0, c0, f + 0.015, b1, c1, M["trim"])
        for (c0, c1) in ((b0, b0 + 0.035), (b1 - 0.035, b1)):                       # stiles
            if along_x:
                sh.box(c0, f - 0.015, z0, c1, f + 0.015, z1, M["trim"])
            else:
                sh.box(f - 0.015, c0, z0, f + 0.015, c1, z1, M["trim"])
        n = int((z1 - z0 - 0.06) / 0.075)
        for j in range(n):                                                           # tilted louvres
            z = z0 + 0.05 + j * 0.075
            if along_x:
                sh.rbox(b0 + 0.035, f - 0.03, z, b1 - 0.035, f + 0.03, z + 0.012, M["trim"], r=0.004, seg=1,
                        tilt=-25 * side, axis="X")
            else:
                sh.rbox(f - 0.03, b0 + 0.035, z, f + 0.03, b1 - 0.035, z + 0.012, M["trim"], r=0.004, seg=1,
                        tilt=25 * side, axis="Y")


gl.box(XW - 0.06, DIN_WIN[0], 0.85, XW - 0.05, DIN_WIN[1], 2.15, M["glass"])
shutters(False, XW, DIN_WIN[0], DIN_WIN[1], 0.85, 2.15, 1, 4)
gl.box(LIV_WIN[0], YS - 0.06, WIN[0], LIV_WIN[1], YS - 0.05, WIN[1], M["glass"])
shutters(True, YS, LIV_WIN[0], LIV_WIN[1], WIN[0], WIN[1], 1, 2)
gl.box(HALL_E + 0.05, SIDELIGHT[0], 0.05, HALL_E + 0.06, SIDELIGHT[1], 2.1, M["glass"])
shutters(False, HALL_E, SIDELIGHT[0], SIDELIGHT[1], 0.05, 2.1, -1, 1)
for (a, b) in TV_WINS:
    gl.box(XE + 0.05, a, 0.08, XE + 0.06, b, 2.2, M["glass"])
    shutters(False, XE, a, b, 0.08, 2.2, -1, 1)
gl.box(KIT_WIN[0], YN + 0.05, 1.0, KIT_WIN[1], YN + 0.06, 1.45, M["glass"])
gl.box(SCUL_WIN[0], YN + 0.05, 1.0, SCUL_WIN[1], YN + 0.06, 1.45, M["glass"])
# the sunroom: glass all along its south and west walls (white frames every ~0.8 m)
gl.box(XW + 0.30, YS - 0.06, 0.05, LIV_W - 0.05, YS - 0.05, H - 0.42, M["glass"])
gl.box(XW - 0.06, YS + 0.30, 0.05, XW - 0.05, SUN_N - 0.05, H - 0.42, M["glass"])
gl.finish()
sh.finish()
sf = Piece("Ground_Sunroom_Frames", solid=True)
for (along_x, line, a0, a1) in ((True, YS, XW + 0.30, LIV_W - 0.05), (False, XW, YS + 0.30, SUN_N - 0.05)):
    n = max(1, int((a1 - a0) / 0.8 + 0.5))
    for k in range(n + 1):
        a = a0 + k * (a1 - a0) / n
        if along_x:
            sf.box(a - 0.025, line - 0.08, 0.0, a + 0.025, line, H - 0.42, M["trim"])
        else:
            sf.box(line - 0.08, a - 0.025, 0.0, line, a + 0.025, H - 0.42, M["trim"])
    if along_x:
        sf.box(a0, line - 0.08, 0.0, a1, line, 0.05, M["trim"])
        sf.box(a0, line - 0.08, H - 0.47, a1, line, H - 0.42, M["trim"])
    else:
        sf.box(line - 0.08, a0, 0.0, line, a1, 0.05, M["trim"])
        sf.box(line - 0.08, a0, H - 0.47, line, a1, H - 0.42, M["trim"])
for k in range(4):                                                                  # bifold door handles (west)
    yy = YS + 0.7 + k * 0.85
    sf.box(XW - 0.02, yy - 0.01, 0.95, XW - 0.005, yy + 0.01, 1.15, M["black"])
sf.finish()


# sliding glass doors into the sunroom: one panel shut, the other slid behind it (open)
def slider(name, along_x, line, a0, a1):
    p = Piece(name, solid=True)
    mid = (a0 + a1) / 2
    for (b0, b1, off) in ((a0, mid + 0.03, -0.025), (a0 + 0.04, mid + 0.07, 0.025)):
        for (c0, c1, z0, z1) in ((b0, b0 + 0.05, 0, 2.12), (b1 - 0.05, b1, 0, 2.12), (b0, b1, 0, 0.05), (b0, b1, 2.07, 2.12)):
            if along_x:
                p.box(c0, line + off - 0.02, z0, c1, line + off + 0.02, z1, M["trim"])
            else:
                p.box(line + off - 0.02, c0, z0, line + off + 0.02, c1, z1, M["trim"])
        if along_x:
            p.box(b0 + 0.05, line + off - 0.005, 0.05, b1 - 0.05, line + off + 0.005, 2.07, M["glass"])
        else:
            p.box(line + off - 0.005, b0 + 0.05, 0.05, line + off + 0.005, b1 - 0.05, 2.07, M["glass"])
    hb = mid + 0.0
    if along_x:
        p.box(hb, line - 0.06, 0.8, hb + 0.02, line - 0.045, 1.4, M["black"])
    else:
        p.box(line + 0.045, hb, 0.8, line + 0.06, hb + 0.02, 1.4, M["black"])
    p.finish()


slider("Ground_Slider_Dining", True, SUN_N + T / 2, SUN_DOOR_N[0], SUN_DOOR_N[1])
slider("Ground_Slider_Living", False, LIV_W + T / 2, SUN_DOOR_E[0], SUN_DOOR_E[1])
cu = Piece("Ground_Curtains")                                                       # living-room side
for (y0, y1) in ((SUN_DOOR_E[0] - 0.42, SUN_DOOR_E[0] + 0.05), (SUN_DOOR_E[1] - 0.05, SUN_DOOR_E[1] + 0.42)):
    for k in range(7):
        y = y0 + (y1 - y0) * (k + 0.5) / 7
        cu.cyl(LIV_W + T + 0.1 + 0.02 * (k % 2), y, 0.02, (y1 - y0) / 7 * 0.62, 2.3, M["g_curtain"], seg=12)
cu.tube((LIV_W + T + 0.1, SUN_DOOR_E[0] - 0.5, 2.36), (LIV_W + T + 0.1, SUN_DOOR_E[1] + 0.5, 2.36), 0.015, M["steel"])
cu.finish()

# doors: front door + garage door (shut, dark timber), three that open with E
dr = Piece("Ground_Front_Door", solid=True)
door_slab(dr, False, FRONT_DOOR[0] + 0.005, FRONT_DOOR[1] - 0.005, HALL_E + T / 2, 0, 2.09,
          handle_at=FRONT_DOOR[0] + 0.07, face_mat=M["g_timber"])
dr.rbox(HALL_E + T / 2 - 0.021, FRONT_DOOR[0] + 0.005, 0, HALL_E + T / 2 + 0.021, FRONT_DOOR[1] - 0.005, 2.09,
        M["g_timber"], r=0.006, seg=2)
for k in range(4):                                                                  # four raised panels
    z = 0.12 + k * 0.48
    dr.rbox(HALL_E - 0.002, FRONT_DOOR[0] + 0.1, z, HALL_E + 0.0, FRONT_DOOR[1] - 0.1, z + 0.4, M["g_timber"], r=0.004, seg=1)
dr.box(HALL_E - 0.03, FRONT_DOOR[0] + 0.04, 0.95, HALL_E - 0.005, FRONT_DOOR[0] + 0.08, 1.25, M["black"])   # lock
dr.rbox(HALL_E - 0.03, FRONT_DOOR[1] - 0.4, 1.95, HALL_E - 0.005, FRONT_DOOR[1] - 0.15, 2.0, M["steel"], r=0.008)  # closer
frame(dr, False, HALL_E, HALL_E + T, FRONT_DOOR[0], FRONT_DOOR[1], 0, 2.1)
# garage door: dark timber with a big dark glass panel
gd = (GARAGE_DOOR[0] + 0.005, GARAGE_DOOR[1] - 0.005)
dr.rbox(gd[0], HALL_S_E - T / 2 - 0.02, 0, gd[1], HALL_S_E - T / 2 + 0.02, 2.03, M["g_timber"], r=0.006, seg=2)
dr.box(gd[0] + 0.12, HALL_S_E - T / 2 + 0.019, 0.35, gd[1] - 0.12, HALL_S_E - T / 2 + 0.024, 1.9, M["screen"])
dr.cyl(gd[0] + 0.07, HALL_S_E - T / 2 + 0.04, 0.98, 0.03, 0.03, M["steel"], seg=14, axis="Y")
frame(dr, True, HALL_S_E - T, HALL_S_E, GARAGE_DOOR[0], GARAGE_DOOR[1], 0, 2.04)
dr.finish()
hinged_door("Door_G_Study", STUDY_DOOR[0] + 0.012, STUDY_N + T / 2, "+x", STUDY_DOOR[1] - STUDY_DOOR[0] - 0.024)
hinged_door("Door_G_Laundry", LAUN_DOOR[1] - 0.012, HALL_N + T / 2, "-x", LAUN_DOOR[1] - LAUN_DOOR[0] - 0.024)
hinged_door("Door_G_Bath", BATH_DOOR[0] + 0.012, HALL_N + T / 2, "+x", BATH_DOOR[1] - BATH_DOOR[0] - 0.024)
nr = Piece("Ground_Noren")                                                          # curtain in the scullery doorway
for (a, b) in ((SCUL_DOOR[0] + 0.02, (SCUL_DOOR[0] + SCUL_DOOR[1]) / 2 - 0.01),
               ((SCUL_DOOR[0] + SCUL_DOOR[1]) / 2 + 0.01, SCUL_DOOR[1] - 0.02)):
    nr.box(KIT_E - T / 2 - 0.005, a, 1.35, KIT_E - T / 2 + 0.005, b, 2.02, M["g_noren"])
nr.tube((KIT_E - T / 2, SCUL_DOOR[0], 2.03), (KIT_E - T / 2, SCUL_DOOR[1], 2.03), 0.01, M["steel"])
nr.finish()

# ---------------------------------------------------------------- recessed downlights (+ light markers)
LIGHTS = [(-6.8, 2.3), (-6.7, 6.6), (-3.0, 7.9), (-2.4, 2.0), (-1.2, 5.2), (0.6, 8.3), (2.3, 1.8),
          (3.0, 7.7), (5.2, 7.7), (6.6, 4.9), (8.5, 7.6), (1.0, 5.2)]
DOWNLIGHTS = LIGHTS + [(-4.2, 1.2), (-0.8, 1.2), (-4.0, 3.4), (-1.0, 3.4), (-4.5, 7.9), (-1.6, 7.9),
                       (-7.6, 5.5), (-5.8, 5.5), (-7.6, 7.8), (7.4, 7.0), (9.6, 7.0), (9.6, 8.3),
                       (7.8, 4.6), (8.6, 5.3), (3.9, 5.7), (-6.0, 1.2), (-7.6, 3.6)]
lamps = Piece("Ground_Downlights")
for (x, y) in DOWNLIGHTS:
    lamps.cyl(x, y, H - 0.006, 0.055, 0.006, M["diffuser"], seg=20)
    lamps.cyl(x, y, H - 0.004, 0.068, 0.004, M["white"], seg=20)
for i, (x, y) in enumerate(LIGHTS):
    marker(f"Ground_Light_{i}", x, y, H - 0.1)
for (x, y, w, d) in ((-3.0, 2.0, 0.45, 0.25), (-2.2, 2.0, 0.3, 0.25), (-1.8, 6.3, 0.6, 0.35), (-3.2, 5.4, 0.3, 0.25)):
    lamps.box(x - w / 2, y - d / 2, H - 0.01, x + w / 2, y + d / 2, H, M["white"])         # AC vents
    for k in range(5):
        xx = x - w / 2 + 0.03 + k * (w - 0.06) / 4
        lamps.box(xx - 0.004, y - d / 2 + 0.02, H - 0.012, xx + 0.004, y + d / 2 - 0.02, H - 0.01, M["vent"])
lamps.finish()


# ---------------------------------------------------------------- furniture helpers
def turn(objs, cx, cy, deg):
    """Turn finished objects about the point (cx, cy)."""
    R = Matrix.Translation((cx, cy, 0)) @ Matrix.Rotation(math.radians(deg), 4, "Z") @ Matrix.Translation((-cx, -cy, 0))
    for o in objs:          # matrix_basis: matrix_world is stale until the scene updates
        o.matrix_basis = R @ o.matrix_basis


def sofa(prefix, cx, cy, width, depth, facing, cover, seats, extra=None):
    """lounge() from build_flat.py, but facing any way: '+y', '-y', '+x', '-x'.
    (cx, cy) = middle of the sofa; width along its back, depth front to back."""
    x0, x1 = cx - width / 2, cx + width / 2
    y0, y1 = cy - depth / 2, cy + depth / 2
    body, seats_ = lounge(prefix, x0, y0, x1, y1, cover, seats, arm_w=0.2)
    if extra:
        extra(body, x0, y0, x1, y1)
    objs = [body.finish()] + [s.finish() for s in seats_]
    turn(objs, cx, cy, {"+y": 0, "-y": 180, "+x": -90, "-x": 90}[facing])
    return objs


def table(name, x0, y0, x1, y1, top=0.75, mat=None, leg=0.025):
    p = Piece(name, solid=True, bevel=0.006)
    mat = mat or M["wood_dark"]
    p.rbox(x0, y0, top - 0.04, x1, y1, top, mat, r=0.015, seg=2)
    for (fx, fy) in ((x0 + 0.06, y0 + 0.06), (x1 - 0.06, y0 + 0.06), (x0 + 0.06, y1 - 0.06), (x1 - 0.06, y1 - 0.06)):
        p.cyl(fx, fy, 0, leg, top - 0.04, mat, seg=12)
    return p


def dining_chair(name, cx, cy, facing_deg, mat):
    """Simple chair; E sits you (origin at the seat, local +X = the way you face)."""
    p = Piece(name, origin=(cx, cy, 0), solid=True, rot=facing_deg)
    p.rbox(cx - 0.21, cy - 0.21, 0.43, cx + 0.21, cy + 0.21, 0.47, mat, r=0.02)
    for (fx, fy) in ((cx - 0.17, cy - 0.17), (cx + 0.17, cy - 0.17), (cx - 0.17, cy + 0.17), (cx + 0.17, cy + 0.17)):
        p.cyl(fx, fy, 0, 0.016, 0.43, M["wood_dark"], seg=10)
    fx, fy = math.cos(math.radians(facing_deg)), math.sin(math.radians(facing_deg))
    bx, by = cx - fx * 0.2, cy - fy * 0.2
    if abs(fx) > 0.5:
        p.rbox(bx - 0.02, cy - 0.2, 0.47, bx + 0.02, cy + 0.2, 0.92, mat, r=0.015)
    else:
        p.rbox(cx - 0.2, by - 0.02, 0.47, cx + 0.2, by + 0.02, 0.92, mat, r=0.015)
    return p.finish()


def counter(p, x0, y0, x1, y1, front, top=0.9, doors=True):
    """Base cabinets + worktop. front = the side you stand at: '+y', '-y', '+x', '-x'."""
    p.rbox(x0, y0, 0.1, x1, y1, top - 0.04, M["g_cab"], r=0.008, seg=2)
    p.box(x0 + 0.03, y0 + 0.03, 0, x1 - 0.03, y1 - 0.03, 0.1, M["black"])                # kick plate
    p.rbox(x0 - 0.01, y0 - 0.01, top - 0.04, x1 + 0.01, y1 + 0.01, top, M["g_worktop"], r=0.006, seg=2)
    if not doors:
        return
    along_x = front in ("+y", "-y")
    lo, hi = (x0, x1) if along_x else (y0, y1)
    n = max(1, int(round((hi - lo) / 0.6)))
    w = (hi - lo) / n
    for k in range(n):
        a = lo + k * w
        if along_x:
            f = y1 if front == "+y" else y0
            s = 1 if front == "+y" else -1
            p.box(a + w - 0.003, f, 0.12, a + w + 0.003, f + s * 0.004, top - 0.06, M["vent"])   # door gaps
            p.tube((a + w / 2 - 0.08, f + s * 0.03, top - 0.12), (a + w / 2 + 0.08, f + s * 0.03, top - 0.12), 0.008, M["steel"])
        else:
            f = x1 if front == "+x" else x0
            s = 1 if front == "+x" else -1
            p.box(f, a + w - 0.003, 0.12, f + s * 0.004, a + w + 0.003, top - 0.06, M["vent"])
            p.tube((f + s * 0.03, a + w / 2 - 0.08, top - 0.12), (f + s * 0.03, a + w / 2 + 0.08, top - 0.12), 0.008, M["steel"])


def hob(p, x0, y0, x1, y1, z, burners):
    p.rbox(x0, y0, z, x1, y1, z + 0.012, M["g_hob"], r=0.004, seg=2)
    for (bx, by) in burners:
        p.cyl(bx, by, z + 0.012, 0.075, 0.012, M["steel"], seg=20)
        p.cyl(bx, by, z + 0.024, 0.04, 0.012, M["black"], seg=16)


def sink(p, x0, y0, x1, y1, z):
    p.box(x0, y0, z - 0.002, x1, y1, z + 0.004, M["steel"])
    p.box(x0 + 0.03, y0 + 0.03, z - 0.18, x1 - 0.03, y1 - 0.03, z + 0.005, M["steel"])



# ---------------------------------------------------------------- living room
# Grey L-shaped sectional (west piece faces east, north piece faces south toward the TV), the third
# sofa on the east side, red rug, dark timber coffee table and TV unit, TV in front of the window.
sofa("G_Sofa_West", -3.72, 2.28, 2.35, 0.95, "+x", M["g_sofa"], 3,
     extra=lambda b, x0, y0, x1, y1: (b.rbox(x0 + 0.25, y0 + 0.28, 0.45, x0 + 0.65, y0 + 0.42, 0.85, M["g_cushion"], r=0.06, seg=3, tilt=-12, axis="X"),
                                      b.rbox(x1 - 0.65, y0 + 0.28, 0.45, x1 - 0.25, y0 + 0.42, 0.85, M["pink"], r=0.06, seg=3, tilt=-12, axis="X")))
sofa("G_Sofa_North", -2.17, 3.15, 2.1, 0.88, "-y", M["g_sofa"], 2,
     extra=lambda b, x0, y0, x1, y1: (b.rbox(x0 + 0.3, y0 + 0.0, 0.62, x1 - 0.4, y0 + 0.28, 0.9, M["g_cushion"], r=0.05, seg=3),
                                      b.rbox(x0 + 0.5, y0 + 0.02, 0.86, x1 - 0.6, y0 + 0.2, 0.9, M["g_throw"], r=0.02, seg=2)))
sofa("G_Sofa_East", -0.62, 1.9, 2.2, 0.9, "-x", M["g_sofa"], 2)
rugs = Piece("Ground_Rugs")
rugs.rbox(-3.10, 1.07, 0, -1.10, 2.62, 0.012, M["g_rug_red"], r=0.006, seg=2)
rugs.rbox(7.45, 4.10, 0, 8.25, 4.65, 0.015, M["g_rug_dk"], r=0.006, seg=2)          # front doormat
rugs.rbox(6.10, 3.80, 0, 6.92, 4.30, 0.015, M["g_mat"], r=0.006, seg=2)             # mat at the garage door
rugs.rbox(-5.15, 5.75, 0, -4.7, 6.15, 0.008, M["g_rug_gr"], r=0.004, seg=2)          # pet mat
rugs.cyl(-5.05, 5.95, 0.008, 0.08, 0.06, M["porcelain"], seg=16)                      # pet bowls
rugs.cyl(-4.82, 5.95, 0.008, 0.08, 0.06, M["porcelain"], seg=16)
rugs.finish()
ct = Piece("Ground_Coffee_Table", solid=True, bevel=0.006)
ct.rbox(-2.70, 1.50, 0.36, -1.40, 2.08, 0.42, M["g_timber"], r=0.012)
ct.rbox(-2.66, 1.54, 0.05, -1.44, 2.04, 0.08, M["g_timber"], r=0.01)
for (fx, fy) in ((-2.64, 1.56), (-1.46, 1.56), (-2.64, 2.02), (-1.46, 2.02)):
    ct.box(fx - 0.03, fy - 0.03, 0, fx + 0.03, fy + 0.03, 0.36, M["g_timber"])
ct.rbox(-2.4, 1.65, 0.42, -2.1, 1.9, 0.5, TOYS[3], r=0.02)                            # stuff on it
ct.cyl(-1.75, 1.8, 0.42, 0.04, 0.16, TOYS[7], seg=12)
ct.finish()
tvu = Piece("Ground_TV_Unit", solid=True, bevel=0.006)
tvu.rbox(-3.60, YS + 0.02, 0.05, -1.20, 0.55, 0.50, M["g_timber"], r=0.012)
for k in range(4):
    x = -3.55 + k * 0.6
    tvu.rbox(x, 0.548, 0.1, x + 0.55, 0.556, 0.45, M["g_timber"], r=0.004, seg=2)
tvu.rbox(-3.35, 0.24, 0.55, -1.85, 0.29, 1.42, M["black"], r=0.01, seg=2)            # 65" TV (faces +Y)
tvu.box(-3.33, 0.291, 0.57, -1.87, 0.293, 1.40, M["g_tv"])
tvu.rbox(-2.70, 0.18, 0.50, -2.50, 0.36, 0.55, M["black"], r=0.01)
tvu.rbox(-3.1, 0.35, 0.5, -2.2, 0.45, 0.56, M["black"], r=0.02)                     # sound bar
tvu.finish()
ot = Piece("Ground_Ottoman", solid=True)
ot.cyl(-4.3, 0.55, 0, 0.21, 0.42, M["navy"], seg=24)
ot.finish()

# ---------------------------------------------------------------- study (south, between the living room and the stairs)
wd = Piece("Ground_Study_Wardrobe", solid=True, bevel=0.006)
wd.rbox(LIV_E + 0.01, YS + 0.02, 0, 0.95, STUDY_N - 0.02, 2.3, M["g_cab"], r=0.01)
n = 5
for k in range(1, n):
    y = YS + k * (STUDY_N - YS) / n
    wd.box(0.95, y - 0.003, 0.05, 0.955, y + 0.003, 2.25, M["vent"])
for k in range(n):
    y = YS + (k + 0.5) * (STUDY_N - YS) / n
    wd.tube((0.98, y - 0.15, 1.0), (0.98, y + 0.15, 1.0), 0.009, M["steel"])
wd.finish()
dk = table("Ground_Study_Desk", 2.75, 1.2, 3.40, 2.6, top=0.75, mat=M["white"])
dk.rbox(3.20, 1.6, 0.76, 3.24, 2.2, 1.12, M["black"], r=0.008, seg=2)               # monitor (faces -X)
dk.box(3.199, 1.62, 0.79, 3.2, 2.18, 1.10, M["g_pc"])
dk.rbox(2.95, 1.7, 0.75, 3.1, 2.1, 0.77, M["black"], r=0.006)
dk.finish()
office_chair("Chair_G_Study", 2.45, 1.9, 0)                                        # facing the desk (+X)
st = Piece("Ground_Study_Shelves", solid=True, bevel=0.004)
for (x0, y0, x1, y1, h) in ((2.95, 2.75, 3.40, 3.38, 1.2), (2.95, 0.2, 3.40, 1.05, 1.3)):
    st.rbox(x0, y0, 0, x1, y1, h, M["white"], r=0.008)
    for z in (0.4, 0.8):
        st.box(x0 - 0.002, y0 + 0.03, z, x0, y1 - 0.03, z + 0.01, M["vent"])
    for k in range(4):
        yy = y0 + 0.05 + k * (y1 - y0 - 0.1) / 4
        st.rbox(x0 + 0.06, yy, h, x0 + 0.3, yy + 0.12, h + random.uniform(0.1, 0.25), random.choice(TOYS), r=0.02)
st.finish()



# ---------------------------------------------------------------- sunroom (glass walls, deck floor)
tb = Piece("Ground_Patio_Table", solid=True, bevel=0.006)
tb.rbox(-7.25, 1.50, 0.70, -6.15, 3.25, 0.74, M["g_rattan"], r=0.02)
tb.box(-7.18, 1.57, 0.74, -6.22, 3.18, 0.75, M["glass"])
for (fx, fy) in ((-7.18, 1.57), (-6.22, 1.57), (-7.18, 3.18), (-6.22, 3.18)):
    tb.box(fx - 0.04, fy - 0.04, 0, fx + 0.04, fy + 0.04, 0.70, M["g_rattan"])
tb.finish()


def wicker_chair(name, cx, cy, facing_deg):
    p = Piece(name, origin=(cx, cy, 0), solid=True, rot=facing_deg)
    p.rbox(cx - 0.27, cy - 0.27, 0.0, cx + 0.27, cy + 0.27, 0.43, M["g_rattan"], r=0.04, seg=2)
    p.rbox(cx - 0.24, cy - 0.24, 0.43, cx + 0.24, cy + 0.24, 0.47, M["fabric"], r=0.03, seg=2)
    fx, fy = math.cos(math.radians(facing_deg)), math.sin(math.radians(facing_deg))
    bx, by = cx - fx * 0.24, cy - fy * 0.24
    if abs(fx) > 0.5:
        p.rbox(bx - 0.04, cy - 0.27, 0.43, bx + 0.04, cy + 0.27, 1.0, M["g_rattan"], r=0.03)
        for s in (-1, 1):
            p.rbox(cx - 0.27, cy + s * 0.25 - 0.03, 0.43, cx + 0.27, cy + s * 0.25 + 0.03, 0.66, M["g_rattan"], r=0.02)
    else:
        p.rbox(cx - 0.27, by - 0.04, 0.43, cx + 0.27, by + 0.04, 1.0, M["g_rattan"], r=0.03)
        for s in (-1, 1):
            p.rbox(cx + s * 0.25 - 0.03, cy - 0.27, 0.43, cx + s * 0.25 + 0.03, cy + 0.27, 0.66, M["g_rattan"], r=0.02)
    return p.finish()


for i, (x, y, f) in enumerate(((-7.62, 1.95, 0), (-7.62, 2.80, 0), (-5.78, 1.95, 180), (-5.78, 2.80, 180),
                               (-6.70, 1.10, 90), (-6.70, 3.65, -90))):
    wicker_chair(f"Chair_G_Patio_{i + 1}", x, y, f)
sp = Piece("Ground_Sunroom_Props", bevel=0.004)
sp.rbox(-5.65, YS + 0.05, 0, -5.10, 1.20, 0.92, M["black"], r=0.01)                 # dark cabinet
sp.rbox(-5.6, 0.3, 0.92, -5.2, 0.6, 1.1, M["basket"], r=0.02)
sp.cyl(-5.4, 0.9, 0.92, 0.07, 0.12, M["glass"], seg=16)
sp.tube((-8.15, 0.45, 2.1), (-5.35, 3.95, 2.1), 0.02, M["wood_lt"])                  # pole with hanging plants
for t in (0.25, 0.38, 0.5, 0.62):
    px, py = -8.15 + 2.8 * t, 0.45 + 3.5 * t
    sp.tube((px, py, 2.1), (px, py, 1.75), 0.003, M["black"])
    sp.sphere(px, py, 1.7, 0.09, M["g_plant"], seg=12)
    sp.cyl(px, py, 1.25, 0.04, 0.45, M["g_plant"], r_top=0.07, seg=10)
sp.cyl(-8.1, 4.1, 0, 0.16, 0.38, M["navy"], seg=20)                                  # buckets
sp.cyl(-8.1, 4.1, 0.38, 0.16, 0.34, M["black"], seg=20)
sp.cyl(-7.75, 4.15, 0, 0.12, 0.3, M["towel"], seg=16)
for (x, y) in ((-8.2, 1.4), (-8.15, 2.6)):                                            # pot plants by the glass
    sp.cyl(x, y, 0, 0.13, 0.28, M["wood_lt"], r_top=0.15, seg=16)
    sp.sphere(x, y, 0.45, 0.2, M["g_plant"], seg=12)
sp.finish()

# ---------------------------------------------------------------- dining room
dt = Piece("Ground_Dining_Table", solid=True, bevel=0.006)
dt.rbox(-7.27, 5.45, 0.72, -6.20, 7.60, 0.77, M["g_timber"], r=0.01)
for (fx, fy) in ((-7.2, 5.52), (-6.27, 5.52), (-7.2, 7.53), (-6.27, 7.53)):
    dt.box(fx - 0.04, fy - 0.04, 0, fx + 0.04, fy + 0.04, 0.72, M["g_timber"])
dt.box(-7.29, 5.43, 0.77, -6.18, 7.62, 0.772, M["glass"])                             # clear table cover
dt.finish()
pm = Piece("Ground_Table_Settings")
for (x, y) in ((-6.73, 5.9), (-6.73, 6.55), (-6.73, 7.2)):
    pm.rbox(x - 0.4, y - 0.15, 0.772, x + 0.4, y + 0.15, 0.776, M["g_placemat"], r=0.01, seg=2)
pm.cyl(-6.95, 5.9, 0.776, 0.17, 0.02, M["wood_lt"], seg=24)                            # woven trivets
pm.cyl(-6.55, 6.6, 0.776, 0.17, 0.02, M["wood_lt"], seg=24)
pm.rbox(-6.95, 6.95, 0.776, -6.65, 7.15, 0.86, M["box_card"], r=0.01)                  # tissue box
pm.cyl(-6.45, 7.3, 0.776, 0.03, 0.22, M["glass"], seg=12)                              # vase
pm.sphere(-6.45, 7.3, 1.02, 0.06, M["pink"], seg=10)
pm.finish()
for i, (x, y, f, mat) in enumerate(((-7.6, 5.95, 0, M["g_timber"]), (-7.6, 6.85, 0, M["wood_lt"]),
                                    (-5.88, 5.95, 180, M["g_timber"]), (-5.88, 6.85, 180, M["g_timber"]),
                                    (-6.73, 7.95, -90, M["g_timber"]))):
    dining_chair(f"Chair_G_Dining_{i + 1}", x, y, f, mat)
pd = Piece("Ground_Dining_Pendant")                                                   # glass box pendant
for (x, y) in ((-6.73, 6.1), (-6.73, 7.0)):
    pd.tube((x, y, H), (x, y, 2.02), 0.006, M["black"])
x0, x1, y0, y1, z0, z1 = -6.93, -6.53, 5.85, 7.25, 1.72, 2.02
for (a, b) in (((x0, y0), (x1, y0)), ((x0, y1), (x1, y1)), ((x0, y0), (x0, y1)), ((x1, y0), (x1, y1))):
    for z in (z0, z1):
        pd.tube((a[0], a[1], z), (b[0], b[1], z), 0.008, M["black"])
for (x, y) in ((x0, y0), (x1, y0), (x0, y1), (x1, y1)):
    pd.tube((x, y, z0), (x, y, z1), 0.008, M["black"])
pd.box(x0, y0, z0, x1, y1, z0 + 0.002, M["glass"])
for k in range(5):
    pd.sphere(-6.73, 6.0 + k * 0.27, 1.82, 0.045, M["diffuser"], scale=(1, 1, 1.3), seg=12)
pd.finish()
aq = Piece("Ground_Aquarium", solid=True, bevel=0.004)                                # aquarium, fridge, tall cupboard
aq.rbox(-7.75, YN - 0.5, 0, -6.55, YN - 0.02, 0.82, M["g_cab"], r=0.01)
aq.box(-7.72, YN - 0.47, 0.82, -6.58, YN - 0.05, 1.32, M["g_tank"])
aq.box(-7.74, YN - 0.49, 1.32, -6.56, YN - 0.03, 1.36, M["black"])
for (x, y, r) in ((-7.4, YN - 0.25, 0.08), (-7.1, YN - 0.3, 0.06), (-6.85, YN - 0.22, 0.07)):
    aq.sphere(x, y, 0.9, r, M["g_coral"], seg=10)
aq.rbox(-6.40, YN - 0.72, 0, -5.62, YN - 0.04, 1.75, M["g_stainless"], r=0.015)        # stainless fridge
aq.box(-6.39, YN - 0.725, 1.2, -5.63, YN - 0.72, 1.21, M["black"])
for (z0, z1) in ((0.4, 1.0), (1.3, 1.6)):
    aq.tube((-6.33, YN - 0.75, z0), (-6.33, YN - 0.75, z1), 0.01, M["steel"])
for k, (x, y) in enumerate(((-6.2, 1.6), (-6.0, 1.45), (-5.85, 1.55), (-5.95, 1.35))):  # fridge magnets
    aq.box(x - 0.04, YN - 0.725, y - 0.03, x + 0.04, YN - 0.722, y + 0.03, TOYS[k])
aq.rbox(-5.52, YN - 0.6, 0, -4.70, YN - 0.02, 2.4, M["g_cab"], r=0.01)                 # tall white cupboard
aq.box(-5.111, YN - 0.605, 0.05, -5.109, YN - 0.6, 2.35, M["vent"])
aq.finish()
pl = Piece("Ground_Plant")                                                            # lucky bamboo by the kitchen
pl.cyl(-4.85, 7.75, 0.92, 0.07, 0.3, M["glass"], seg=14)
for k in range(5):
    a = k * 1.3
    pl.tube((-4.85, 7.75, 1.0), (-4.85 + 0.3 * math.cos(a), 7.75 + 0.3 * math.sin(a), 1.7 + 0.1 * k), 0.012, M["g_plant"])
    pl.sphere(-4.85 + 0.3 * math.cos(a), 7.75 + 0.3 * math.sin(a), 1.7 + 0.1 * k, 0.09, M["g_plant"], scale=(1.6, 0.5, 0.3), seg=8)
pl.finish()

# ---------------------------------------------------------------- kitchen: galley along the north wall + island
kc = Piece("Ground_Kitchen", solid=True, bevel=0.004)
counter(kc, -4.60, 8.60, KIT_E, YN, "-y")
hob(kc, -3.05, 8.68, -2.15, 9.12, 0.9, [(-2.9, 8.8), (-2.9, 9.0), (-2.6, 8.9), (-2.3, 8.8), (-2.3, 9.0)])
kc.box(-3.0, 8.595, 0.15, -2.2, 8.6, 0.8, M["black"])                                 # oven door
kc.tube((-2.95, 8.56, 0.74), (-2.25, 8.56, 0.74), 0.01, M["steel"])
for x0, x1 in ((-4.55, -3.15), (-2.05, KIT_E - 0.02)):                                 # wall cupboards over the window
    kc.rbox(x0, YN - 0.35, 1.52, x1, YN - 0.01, 2.3, M["g_cab"], r=0.008, seg=2)
kc.rbox(-3.10, YN - 0.5, 1.6, -2.10, YN - 0.02, 1.72, M["g_stainless"], r=0.01, seg=2)  # chimney range hood
kc.box(-2.82, YN - 0.3, 1.72, -2.38, YN - 0.02, H, M["g_stainless"])
counter(kc, -4.60, 6.47, -1.47, 7.40, "+y", top=0.92)                                   # island (doors on the kitchen side)
sink(kc, -2.75, 6.75, -1.95, 7.15, 0.92)                                                # its double sink
kc.box(-2.36, 6.75, 0.74, -2.34, 7.15, 0.92, M["steel"])
kc.tube((-2.35, 7.27, 0.92), (-2.35, 7.27, 1.22), 0.014, M["steel"])
kc.tube((-2.35, 7.27, 1.22), (-2.35, 7.08, 1.16), 0.012, M["steel"])
# double-door fridge in the recess at the end, facing the kitchen (-X)
kc.rbox(KIT_E + 0.02, 6.32, 0, 0.28, 7.38, 1.8, M["g_stainless"], r=0.015)
kc.box(KIT_E + 0.015, 6.849, 0.05, KIT_E + 0.02, 6.851, 1.78, M["black"])
for y in (6.8, 6.9):
    kc.tube((KIT_E - 0.01, y, 0.7), (KIT_E - 0.01, y, 1.4), 0.012, M["steel"])
kc.box(KIT_E + 0.016, 7.0, 0.95, KIT_E + 0.02, 7.25, 1.25, M["black"])                 # water dispenser
kc.finish()
for i, x in enumerate((-4.2, -3.5, -2.8)):
    p = Piece(f"Chair_G_Stool_{i + 1}", origin=(x, 6.15, 0), solid=True, rot=90)
    p.cyl(x, 6.15, 0.62, 0.17, 0.05, M["black"], seg=20)
    p.cyl(x, 6.15, 0, 0.02, 0.62, M["steel"], seg=10)
    p.cyl(x, 6.15, 0, 0.16, 0.02, M["steel"], seg=20)
    p.finish()
kp = Piece("Ground_Kitchen_Props")
kp.rbox(-4.5, 8.68, 0.9, -4.3, 8.98, 1.05, M["g_coral"], r=0.04, seg=3)                # kettle
kp.cyl(-3.9, 8.95, 0.9, 0.06, 0.25, TOYS[2], seg=12)                                   # paper towel / jars
kp.cyl(-3.65, 8.95, 0.9, 0.07, 0.18, TOYS[3], seg=12)
kp.cyl(-3.42, 8.95, 0.9, 0.08, 0.1, TOYS[6], seg=12)
kp.rbox(-1.9, 8.75, 0.9, -1.55, 9.05, 1.1, M["white"], r=0.04, seg=3)                  # rice cooker
kp.rbox(-1.4, 8.85, 0.9, -1.1, 9.1, 1.2, M["black"], r=0.03, seg=3)                    # air fryer
kp.rbox(-3.6, 6.9, 0.92, -3.2, 7.2, 0.97, M["basket"], r=0.02)                         # fruit on the island
kp.sphere(-3.48, 7.05, 1.0, 0.05, TOYS[0], seg=10)
kp.sphere(-3.33, 7.04, 1.0, 0.05, TOYS[3], seg=10)
kp.box(-1.47, 7.0, 0.5, -1.465, 7.25, 0.85, M["g_rug_red"])                            # tea towels on the island
kp.finish()

# scullery: L of counters, hob under the window, round sink + coffee machine on the far wall
wk = Piece("Ground_Scullery", solid=True, bevel=0.004)
counter(wk, KIT_E, 8.60, SCUL_X1, YN, "-y")
counter(wk, 1.13, SCUL_Y0 + 0.01, SCUL_X1, 8.60, "-x")
hob(wk, -0.10, 8.70, 0.55, 9.12, 0.9, [(0.05, 8.82), (0.38, 8.82), (0.05, 9.0), (0.38, 9.0)])
wk.box(-0.20, YN - 0.55, 1.5, 0.65, YN - 0.02, 1.53, M["glass"])                        # glass canopy hood
wk.rbox(0.05, YN - 0.35, 1.53, 0.40, YN - 0.02, H, M["g_stainless"], r=0.01, seg=2)
wk.cyl(1.43, 8.05, 0.86, 0.17, 0.045, M["steel"], seg=24)                               # round sink
wk.tube((1.66, 8.05, 0.9), (1.66, 8.05, 1.15), 0.012, M["steel"])
wk.tube((1.66, 8.05, 1.15), (1.5, 8.05, 1.1), 0.01, M["steel"])
wk.rbox(0.85, YN - 0.38, 1.55, SCUL_X1 - 0.01, YN - 0.01, 2.35, M["g_cab"], r=0.008, seg=2)   # upper cupboards
wk.rbox(SCUL_X1 - 0.36, 7.6, 1.55, SCUL_X1 - 0.01, YN - 0.01, 2.35, M["g_cab"], r=0.008, seg=2)
wk.rbox(1.25, 8.70, 0.9, 1.55, 9.05, 1.3, M["steel"], r=0.02)                           # coffee machine
wk.rbox(0.85, 8.85, 0.9, 1.1, 9.1, 1.08, TOYS[0], r=0.02)                               # toaster
wk.cyl(0.7, 8.95, 0.9, 0.08, 0.28, M["white"], seg=14)                                  # hot water pot
wk.finish()
pn = Piece("Ground_Pantry", solid=True, bevel=0.004)                                    # walk-in pantry, L of shelves
for z in (0.45, 0.85, 1.25, 1.65, 2.0):
    pn.box(PAN_X0 + 0.02, HALL_N + T, z, 1.72, HALL_N + T + 0.38, z + 0.02, M["g_cab"])     # along the south wall
    pn.box(1.34, HALL_N + T + 0.38, z, 1.72, 7.43, z + 0.02, M["g_cab"])                    # along the east wall
    x = PAN_X0 + 0.06
    while x < 1.6:
        w = random.uniform(0.08, 0.18)
        pn.rbox(x, HALL_N + T + 0.05, z + 0.02, x + w, HALL_N + T + 0.3, z + 0.02 + random.uniform(0.1, 0.3),
                random.choice(TOYS + [M["glass"], M["box_card"], M["white"]]), r=0.015)
        x += w + 0.04
pn.rbox(0.75, 7.0, 0, 1.05, 7.25, 0.25, M["white"], r=0.03)                              # step stool
pn.rbox(1.6, 7.25, 0.3, 1.7, 7.42, 0.9, M["towel"], r=0.02)                              # bag holder
pn.finish()

# ---------------------------------------------------------------- laundry
la = Piece("Ground_Laundry", solid=True, bevel=0.006)
for (x0, top) in ((2.45, 0.85), (3.05, 0.85)):                                          # washer, dryer
    la.rbox(x0, YN - 0.62, 0, x0 + 0.58, YN - 0.02, top, M["porcelain"], r=0.02)
    la.cyl(x0 + 0.29, YN - 0.63, 0.42, 0.19, 0.012, M["steel"], seg=28, axis="Y")
    la.cyl(x0 + 0.29, YN - 0.645, 0.42, 0.15, 0.012, M["glass"], seg=28, axis="Y")
    la.box(x0 + 0.05, YN - 0.63, 0.72, x0 + 0.53, YN - 0.62, 0.8, M["vent"])
la.rbox(LAUN_X0 + 0.03, YN - 0.65, 0, 2.38, YN - 0.02, 1.9, M["porcelain"], r=0.02)       # tall freezer
la.rbox(3.72, 7.90, 0, LAUN_X1 - 0.07, YN - 0.02, 0.9, M["g_cab"], r=0.01)              # sink cabinet
sink(la, 3.80, 8.2, 4.12, 8.8, 0.9)
la.rbox(3.72, 7.90, 1.45, LAUN_X1 - 0.07, YN - 0.02, 2.2, M["g_cab"], r=0.01)
la.finish()
lb = Piece("Ground_Laundry_Props")
lb.cyl(2.0, 6.7, 0, 0.2, 0.45, M["basket"], r_top=0.23, seg=24)
lb.tube((2.45, YN - 0.2, 1.8), (3.6, YN - 0.2, 1.8), 0.012, M["steel"])                  # drying rail
for k in range(6):
    x = 2.55 + k * 0.18
    lb.rbox(x, YN - 0.24, 1.25, x + 0.12, YN - 0.16, 1.8, random.choice([M["towel"], M["shirt_a"], M["shirt_b"]]), r=0.02)
lb.finish()

# ---------------------------------------------------------------- bathroom
bt = Piece("Ground_Bathroom", solid=True)
bt.rbox(LAUN_X1 + 0.06, 8.10, 0, BATH_X1 - 0.01, YN - 0.01, 0.55, M["g_bath"], r=0.05)        # bath (dark grey)
bt.rbox(LAUN_X1 + 0.18, 8.22, 0.22, BATH_X1 - 0.13, YN - 0.12, 0.56, M["porcelain"], r=0.12, seg=4)
bt.tube((5.2, YN - 0.02, 0.62), (5.2, YN - 0.14, 0.62), 0.02, M["steel"])
# toilet against the east wall (facing west)
tx = BATH_X1 - 0.01
bt.rbox(tx - 0.19, 7.40, 0.42, tx, 7.80, 0.80, M["porcelain"], r=0.04)
bt.rbox(tx - 0.3, 7.48, 0.0, tx - 0.04, 7.72, 0.36, M["porcelain"], r=0.06)
bt.sphere(tx - 0.38, 7.60, 0.32, 0.2, M["porcelain"], scale=(1.15, 0.95, 0.45), seg=24)
bt.cyl(tx - 0.39, 7.60, 0.38, 0.19, 0.03, M["porcelain"], seg=28)
# basin on a white vanity by the door (west wall)
bt.rbox(LAUN_X1 + 0.06, 6.55, 0.15, LAUN_X1 + 0.55, 7.45, 0.82, M["white"], r=0.015)
bt.rbox(LAUN_X1 + 0.05, 6.54, 0.82, LAUN_X1 + 0.56, 7.46, 0.86, M["porcelain"], r=0.012)
bt.sphere(LAUN_X1 + 0.31, 7.0, 0.91, 0.2, M["porcelain"], scale=(1, 1.15, 0.35), seg=24)
bt.tube((LAUN_X1 + 0.11, 7.0, 0.86), (LAUN_X1 + 0.11, 7.0, 1.1), 0.016, M["steel"])
bt.box(LAUN_X1 + 0.055, 6.65, 0.95, LAUN_X1 + 0.058, 7.35, 1.95, M["mirror"])
bt.finish()
bp = Piece("Ground_Bath_Props")
bp.rbox(4.9, 7.55, 0, 5.55, 8.0, 0.015, M["g_rug_gr"], r=0.01, seg=2)
bp.tube((BATH_X1 - 0.03, 6.6, 1.25), (BATH_X1 - 0.03, 7.1, 1.25), 0.012, M["steel"])
bp.rbox(BATH_X1 - 0.06, 6.63, 0.75, BATH_X1 - 0.01, 7.07, 1.27, M["towel"], r=0.02, seg=3)
bp.finish()



# ---------------------------------------------------------------- TV room
# charcoal sofa + armchair along the north wall, three tall shuttered windows at the east end,
# black feature wall with a huge TV over a dark open-shelf unit, white C-shaped side table
sofa("G_TV_Sofa", 9.17, 8.70, 2.55, 0.95, "-y", M["g_sofa_dk"], 3,
     extra=lambda b, x0, y0, x1, y1: (b.rbox(x1 - 0.65, y1 - 0.42, 0.45, x1 - 0.25, y1 - 0.28, 0.85, M["g_stripe"], r=0.05, seg=3, tilt=12, axis="X"),
                                      b.rbox(x0 + 0.6, y0 + 0.25, 0.47, x0 + 1.3, y1 - 0.15, 0.55, M["g_throw"], r=0.05, seg=3)))
sofa("G_TV_Armchair", 7.38, 8.70, 0.98, 0.95, "-y", M["g_sofa_dk"], 1)
kb = Piece("Ground_Keyboard", solid=True, bevel=0.004)                                    # keyboard on a stand, west wall
for y in (6.65, 7.25):
    kb.tube((6.25, y, 0), (6.6, y, 0.72), 0.015, M["black"])
    kb.tube((6.6, y, 0), (6.25, y, 0.72), 0.015, M["black"])
kb.rbox(6.2, 6.5, 0.72, 6.62, 7.4, 0.82, M["black"], r=0.02)
for k in range(36):                                                                       # white keys
    y = 6.58 + k * 0.022
    kb.box(6.48, y, 0.82, 6.6, y + 0.019, 0.835, M["porcelain"])
kb.finish()
office_chair("Chair_G_Keyboard", 7.0, 6.95, 180)                                          # stool facing the keyboard (-X)
ctab = Piece("Ground_TV_Side_Table", solid=True, bevel=0.004)                             # white C-shaped laptop table
ctab.sphere(8.75, 7.55, 0.74, 0.32, M["white"], scale=(1.0, 0.75, 0.05), seg=24)
ctab.tube((9.0, 7.55, 0.05), (9.0, 7.55, 0.72), 0.022, M["white"])
for a in (0, 2.1, 4.2):
    ctab.tube((9.0, 7.55, 0.03), (9.0 + 0.28 * math.cos(a), 7.55 + 0.28 * math.sin(a), 0.03), 0.02, M["white"])
ctab.rbox(8.6, 7.48, 0.76, 8.75, 7.58, 0.8, M["white"], r=0.02)                            # game controller + remotes
ctab.rbox(8.8, 7.5, 0.76, 8.84, 7.66, 0.775, M["black"], r=0.01)
ctab.finish()
tvr = Piece("Ground_TV_Room_Unit", solid=True, bevel=0.006)
F = HALL_N + T + 0.03                                                                     # front of the black wall
tvr.rbox(7.30, F, 0, 10.35, F + 0.42, 0.55, M["g_timber"], r=0.01)                        # dark open-shelf unit
for k in range(5):
    x = 7.38 + k * 0.6
    tvr.box(x, F + 0.42, 0.06, x + 0.52, F + 0.425, 0.25, M["black"])                     # open cubbies
    tvr.box(x, F + 0.42, 0.30, x + 0.52, F + 0.425, 0.49, M["black"])
tvr.rbox(7.95, F, 0.75, 9.90, F + 0.06, 1.86, M["black"], r=0.008, seg=2)                 # 85" TV on the wall (faces +Y)
tvr.box(7.97, F + 0.061, 0.77, 9.88, F + 0.063, 1.84, M["g_tv2"])
tvr.rbox(7.4, F + 0.05, 0, 7.75, F + 0.4, 0.42, M["black"], r=0.02)                      # subwoofer
tvr.rbox(8.4, F + 0.2, 0.55, 9.4, F + 0.32, 0.62, M["black"], r=0.02)                     # sound bar
tvr.cyl(10.25, 6.6, 0, 0.12, 1.55, M["plush"], seg=18)                                     # tall white lamp
tvr.box(10.0, F + 0.02, 0, 10.45, F + 0.06, 0.95, M["g_plant"])                            # picture leaning
for x in (10.05, 10.15):                                                                   # twin-tower model
    tvr.cyl(x, F + 0.25, 0.55, 0.035, 0.45, M["steel"], r_top=0.008, seg=8)
tvr.finish()

# ---------------------------------------------------------------- hall, entry and under the stairs
hd = Piece("Ground_Hall", solid=True, bevel=0.004)
hd.rbox(7.55, HALL_S_E + 0.01, 0.74, 8.75, HALL_S_E + 0.42, 0.80, M["g_timber"], r=0.008)  # console table
for (x0, x1) in ((7.55, 7.68), (8.62, 8.75)):
    hd.box(x0, HALL_S_E + 0.02, 0, x1, HALL_S_E + 0.41, 0.74, M["g_timber"])
for (x0, x1) in ((7.75, 8.12), (8.18, 8.55)):                                                # drawers
    hd.box(x0, HALL_S_E + 0.42, 0.6, x1, HALL_S_E + 0.425, 0.72, M["g_timber"])
    hd.tube(((x0 + x1) / 2 - 0.07, HALL_S_E + 0.44, 0.66), ((x0 + x1) / 2 + 0.07, HALL_S_E + 0.44, 0.66), 0.006, M["steel"])
hd.box(7.75, HALL_S_E + 0.05, 0.80, 8.6, HALL_S_E + 0.35, 0.802, M["g_throw"])              # runner
for k, (x, r) in enumerate(((7.85, 0.06), (8.02, 0.07), (8.2, 0.08), (8.38, 0.07), (8.55, 0.09))):  # plush toys
    hd.sphere(x, HALL_S_E + 0.2, 0.8 + r, r, TOYS[(k * 3) % len(TOYS)], seg=12)
    hd.sphere(x, HALL_S_E + 0.2, 0.8 + 2.2 * r, r * 0.7, TOYS[(k * 3) % len(TOYS)], seg=10)
hd.rbox(8.85, HALL_S_E, 1.62, 9.12, HALL_S_E + 0.03, 1.66, M["black"], r=0.006)            # coat rail + coats
for k, x in enumerate((8.9, 9.0, 9.08)):
    hd.rbox(x - 0.06, HALL_S_E + 0.03, 0.85, x + 0.06, HALL_S_E + 0.2, 1.63,
            [M["shirt_d"], M["g_throw"], M["navy"]][k], r=0.04, seg=3)
hd.rbox(8.45, 5.70, 0, 9.12, 6.12, 0.45, M["wood_lt"], r=0.01)                              # slatted bench
for k in range(6):
    hd.box(8.47 + k * 0.11, 5.72, 0.45, 8.55 + k * 0.11, 6.10, 0.47, M["wood_lt"])
hd.rbox(7.50, 5.65, 0, 8.40, 6.12, 0.62, M["black"], r=0.01)                                # black shoe cabinet
hd.rbox(7.6, 5.75, 0.62, 7.9, 6.0, 0.72, M["shirt_d"], r=0.04, seg=3)                      # bags on it
# white built-in open shelves on the south wall by the garage door
for z in (0.0, 0.42, 0.84, 1.26, 1.68, 2.1):
    hd.box(5.58, HALL_S_E, z, 6.02, HALL_S_E + 0.32, z + 0.03, M["white"])
for x in (5.58, 6.0):
    hd.box(x, HALL_S_E, 0, x + 0.02, HALL_S_E + 0.32, 2.13, M["white"])
for z in (0.45, 0.87, 1.29, 1.71):
    hd.rbox(5.65, HALL_S_E + 0.05, z, 5.85, HALL_S_E + 0.25, z + random.uniform(0.12, 0.3), random.choice(TOYS), r=0.02)
# under the stairs: black shoe rack, coat stand, shoe boxes (all under the flight's underside)
for k in range(5):
    z = 0.12 + k * 0.2
    hd.box(3.95, STAIR_Y0 + 0.05, z, 5.15, STAIR_Y0 + 0.42, z + 0.015, M["black"])
    x = 4.0
    while x < 5.05:
        hd.rbox(x, STAIR_Y0 + 0.1, z + 0.015, x + 0.12, STAIR_Y0 + 0.38, z + 0.1,
                random.choice([M["black"], M["shirt_b"], M["box_card"], M["white"]]), r=0.03, seg=2)
        x += 0.16
for (x, y) in ((3.95, STAIR_Y0 + 0.05), (5.15, STAIR_Y0 + 0.05), (3.95, STAIR_Y0 + 0.42), (5.15, STAIR_Y0 + 0.42)):
    hd.cyl(x, y, 0, 0.008, 1.05, M["black"], seg=8)
for (x0, z0) in ((3.4, 0.0), (3.4, 0.17), (3.6, 0.0)):
    hd.rbox(x0, STAIR_Y0 + 0.1, z0, x0 + 0.33, STAIR_Y0 + 0.32, z0 + 0.16, M["box_card"], r=0.005)
hd.finish()
cs = Piece("Ground_Coat_Stand")
cs.cyl(5.35, 4.45, 0, 0.2, 0.02, M["wood_lt"], seg=24)
cs.cyl(5.35, 4.45, 0.02, 0.02, 1.7, M["wood_lt"], seg=10)
cs.rbox(5.2, 4.3, 0.7, 5.5, 4.6, 1.65, M["shirt_d"], r=0.08, seg=3)                          # puffer coat
cs.sphere(5.35, 4.45, 1.72, 0.1, M["shirt_d"], scale=(1, 1, 0.6), seg=12)
cs.finish()

# Down to the ground floor's level, then export
# ---------------------------------------------------------------------------
for o in ROOT.all_objects:
    if o.parent is None:
        o.location.z += GROUND_Z
bpy.ops.object.select_all(action="DESELECT")
for o in ROOT.all_objects:
    o.select_set(True)
bpy.ops.export_scene.gltf(filepath=EXPORT_GLB, use_selection=True, export_format="GLB", export_apply=True)
print("Ground built:", len(ROOT.all_objects), "objects ->", EXPORT_GLB)
