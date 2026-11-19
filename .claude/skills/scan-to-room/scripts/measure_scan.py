"""Measure a 3D room scan and work out how to straighten it.

Run with Blender (no window needed):
  blender -b --factory-startup --python measure_scan.py -- <scan file> <output folder> [--turn 0|90|180|270]

Reads .fbx / .obj / .glb / .gltf / .ply / .stl / .usd(z). Writes into <output folder>:
  measure.json  - unit scale, rotation, offset, room size, floor/ceiling height, wall peaks
  plan.png      - top-down view of the straightened scan (ceiling cut off), 0.5 m grid,
                  origin (0,0) marked red, +X right, +Y up
  slice.png     - outline of everything at 0.4 / 0.9 / 1.5 m height (furniture footprint)

The straightened room has: floor at Z=0, one corner at X=0,Y=0, walls along X and Y,
the room filling +X / +Y. Rotation/offset are applied as
    Translation(offset) @ RotationZ(rotation_deg) @ Scale(unit_scale)
(the same order build_room.py uses for SCAN_ROT_DEG / SCAN_OFFSET).
"""
import bpy, bmesh, sys, os, math, json
from mathutils import Matrix, Vector

argv = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
if len(argv) < 2:
    raise SystemExit("usage: blender -b --python measure_scan.py -- <scan> <out dir> [--turn deg]")
SCAN, OUT = argv[0], argv[1]
TURN = float(argv[argv.index("--turn") + 1]) if "--turn" in argv else 0.0
os.makedirs(OUT, exist_ok=True)


def import_any(path):
    ext = os.path.splitext(path)[1].lower()
    before = set(bpy.data.objects)
    if ext == ".fbx":
        bpy.ops.import_scene.fbx(filepath=path)
    elif ext == ".obj":
        bpy.ops.wm.obj_import(filepath=path)
    elif ext in (".glb", ".gltf"):
        bpy.ops.import_scene.gltf(filepath=path)
    elif ext == ".ply":
        bpy.ops.wm.ply_import(filepath=path)
    elif ext == ".stl":
        bpy.ops.wm.stl_import(filepath=path)
    elif ext in (".usd", ".usda", ".usdc", ".usdz"):
        bpy.ops.wm.usd_import(filepath=path)
    else:
        raise SystemExit("Unsupported scan format: " + ext)
    meshes = [o for o in bpy.data.objects if o not in before and o.type == "MESH"]
    if not meshes:
        raise SystemExit("The scan contains no mesh.")
    # bake every transform into the mesh data, then join into one object
    for o in meshes:
        o.parent = None
    bpy.context.view_layer.update()
    for o in meshes:
        o.data = o.data.copy()
        o.data.transform(o.matrix_world)
        o.matrix_world = Matrix.Identity(4)
    for o in [o for o in bpy.data.objects if o.type != "MESH"]:
        bpy.data.objects.remove(o, do_unlink=True)
    bpy.ops.object.select_all(action="DESELECT")
    for o in meshes:
        o.select_set(True)
    bpy.context.view_layer.objects.active = meshes[0]
    if len(meshes) > 1:
        bpy.ops.object.join()
    return bpy.context.view_layer.objects.active


def hist_peaks(values, weights, lo, hi, bin_size, smooth=1):
    n = max(1, int(math.ceil((hi - lo) / bin_size)))
    h = [0.0] * n
    for v, w in zip(values, weights):
        i = int((v - lo) / bin_size)
        if 0 <= i < n:
            h[i] += w
    if smooth:
        h = [sum(h[max(0, i - smooth):i + smooth + 1]) for i in range(n)]
    peaks = []
    for i in range(n):
        if h[i] > 0 and h[i] >= h[i - 1] if i > 0 else True:
            if i == n - 1 or h[i] > h[i + 1]:
                peaks.append((lo + (i + 0.5) * bin_size, h[i]))
    return h, peaks


bpy.ops.wm.read_factory_settings(use_empty=True)
obj = import_any(SCAN)
me = obj.data

# ---- units: a room is 2-10 m across
size = max(obj.dimensions)
unit = 0.01 if size > 50 else (0.001 if size > 500 else (100.0 if size < 0.5 else 1.0))
if size > 500:
    unit = 0.001
me.transform(Matrix.Scale(unit, 4))

# ---- which way is up? Scans are Z-up in Blender after import; check by comparing
#      how much area faces up/down vs sideways along each axis.
bm = bmesh.new()
bm.from_mesh(me)
bm.faces.ensure_lookup_table()
axis_area = [0.0, 0.0, 0.0]
for f in bm.faces:
    n = f.normal
    a = f.calc_area()
    for k in range(3):
        if abs(n[k]) > 0.9:
            axis_area[k] += a
up_axis = "Z"
if axis_area[1] > axis_area[2] * 1.3 and axis_area[1] > axis_area[0]:
    # Y-up scan: turn it Z-up
    me.transform(Matrix.Rotation(math.radians(90), 4, "X"))
    up_axis = "Y (rotated to Z)"
    bm.free()
    bm = bmesh.new()
    bm.from_mesh(me)
    bm.faces.ensure_lookup_table()

# ---- wall direction: area-weighted histogram of horizontal normal angles, folded to 0..90
angles, w = [], []
for f in bm.faces:
    n = f.normal
    if abs(n.z) < 0.25 and n.length > 0.5:
        angles.append(math.degrees(math.atan2(n.y, n.x)) % 90.0)
        w.append(f.calc_area())
h, _ = hist_peaks(angles, w, 0.0, 90.0, 0.5, smooth=0)
# circular smoothing (89.9 deg and 0.1 deg are the same direction)
n = len(h)
hs = [sum(h[(i + k) % n] for k in range(-2, 3)) for i in range(n)]
best = max(range(n), key=lambda i: hs[i])
# refine with a weighted mean around the peak
num = den = 0.0
for k in range(-3, 4):
    i = (best + k) % n
    a = (best + k + 0.5) * 0.5
    num += h[i] * a
    den += h[i]
wall_angle = num / den if den else 0.0
wall_strength = hs[best] / max(1e-9, sum(h)) * 5   # rough "how clear is it" (0..1)
rotation = -wall_angle + TURN
if rotation <= -180:
    rotation += 360
if rotation > 180:
    rotation -= 360

R = Matrix.Rotation(math.radians(rotation), 4, "Z")
bmesh.ops.transform(bm, matrix=R, verts=bm.verts)
bm.normal_update()

# ---- floor / ceiling from horizontal faces
zs_up, w_up, zs_dn, w_dn = [], [], [], []
for f in bm.faces:
    c = f.calc_center_median()
    if f.normal.z > 0.9:
        zs_up.append(c.z); w_up.append(f.calc_area())
    elif f.normal.z < -0.9:
        zs_dn.append(c.z); w_dn.append(f.calc_area())
allz = [v.co.z for v in bm.verts]
zmin, zmax = min(allz), max(allz)
h_up, peaks_up = hist_peaks(zs_up, w_up, zmin - 0.05, zmax + 0.05, 0.02)
big_up = max(h_up) if h_up else 0
floor_z = min((p for p in peaks_up if p[1] >= 0.3 * big_up), key=lambda p: p[0])[0] if peaks_up else zmin
ceiling_z, ceiling_found = zmax, False
if zs_dn:
    h_dn, peaks_dn = hist_peaks(zs_dn, w_dn, zmin - 0.05, zmax + 0.05, 0.02)
    cands = [p for p in peaks_dn if p[1] >= 0.3 * max(h_dn) and p[0] > floor_z + 1.8]
    if cands:
        ceiling_z, ceiling_found = max(cands, key=lambda p: p[0])[0], True

# ---- walls: vertical faces facing +-X / +-Y, between knee and head height
def wall_peaks(axis):
    vals, ww = [], []
    for f in bm.faces:
        if abs(f.normal[axis]) > 0.9:
            c = f.calc_center_median()
            if floor_z + 0.3 < c.z < min(ceiling_z, floor_z + 2.6) - 0.2:
                vals.append(c[axis]); ww.append(f.calc_area())
    co = [v.co[axis] for v in bm.verts]
    hh, pk = hist_peaks(vals, ww, min(co) - 0.05, max(co) + 0.05, 0.02)
    top = max(hh) if hh else 1
    strong = sorted([(round(p, 3), round(s / top, 2)) for p, s in pk if s >= 0.15 * top])
    return strong, min(co), max(co)


wx, xmin, xmax = wall_peaks(0)
wy, ymin, ymax = wall_peaks(1)
# outermost strong walls = the room's walls (alcoves / furniture show up as inner peaks)
def outer(strong, lo, hi):
    if not strong:
        return lo, hi
    good = [p for p, s in strong if s >= 0.3] or [p for p, s in strong]
    return min(good), max(good)
x0, x1 = outer(wx, xmin, xmax)
y0, y1 = outer(wy, ymin, ymax)
offset = (-x0, -y0, -floor_z)
T = Matrix.Translation(offset)
bmesh.ops.transform(bm, matrix=T, verts=bm.verts)
bm.to_mesh(me)
bm.free()
me.update()

result = {
    "scan": os.path.abspath(SCAN),
    "up_axis": up_axis,
    "unit_scale": unit,
    "rotation_deg": round(rotation, 2),
    "offset": [round(v, 3) for v in offset],
    "wall_direction_clarity": round(min(1.0, wall_strength), 2),
    "room_width_x": round(x1 - x0, 3),
    "room_depth_y": round(y1 - y0, 3),
    "ceiling_height": round(ceiling_z - floor_z, 3),
    "ceiling_found": ceiling_found,
    "scan_extent_after_align": {
        "x": [round(xmin - x0, 3), round(xmax - x0, 3)],
        "y": [round(ymin - y0, 3), round(ymax - y0, 3)],
        "z": [round(zmin - floor_z, 3), round(zmax - floor_z, 3)],
    },
    # every strong vertical surface: position (after align) and strength (1 = biggest)
    "x_wall_peaks": [(round(p - x0, 3), s) for p, s in wx],
    "y_wall_peaks": [(round(p - y0, 3), s) for p, s in wy],
    "triangles": sum(len(p.vertices) - 2 for p in me.polygons),
    "has_uv_texture": bool(me.uv_layers) and any(
        n.type == "TEX_IMAGE" for m in me.materials if m and m.node_tree for n in m.node_tree.nodes),
    "has_vertex_colors": bool(me.color_attributes),
    "transform_order": "Translation(offset) @ RotationZ(rotation_deg) @ Scale(unit_scale)",
}
with open(os.path.join(OUT, "measure.json"), "w") as fh:
    json.dump(result, fh, indent=2)
print("MEASURE", json.dumps(result))

# ---- pictures --------------------------------------------------------------
sc = bpy.context.scene
sc.render.engine = "BLENDER_WORKBENCH"
sc.display.shading.light = "FLAT"
sc.display.shading.color_type = "TEXTURE" if result["has_uv_texture"] else (
    "VERTEX" if result["has_vertex_colors"] else "MATERIAL")
sc.render.film_transparent = False
sc.world = bpy.data.worlds.new("w")
sc.world.color = (0.08, 0.08, 0.1)
W, D = result["room_width_x"], result["room_depth_y"]
ex = result["scan_extent_after_align"]
span = max(ex["x"][1] - ex["x"][0], ex["y"][1] - ex["y"][0]) + 0.6
cx, cy = (ex["x"][0] + ex["x"][1]) / 2, (ex["y"][0] + ex["y"][1]) / 2
sc.render.resolution_x = sc.render.resolution_y = 1000


def grid_and_origin(height):
    objs = []
    gm = bpy.data.materials.new("grid")
    gm.diffuse_color = (0.35, 0.8, 1.0, 1)
    om = bpy.data.materials.new("origin")
    om.diffuse_color = (1, 0.1, 0.1, 1)
    step = 0.5
    k = math.floor((cx - span / 2) / step)
    while k * step < cx + span / 2:
        bpy.ops.mesh.primitive_cube_add(size=1, location=(k * step, cy, height))
        o = bpy.context.object; o.scale = (0.006 if k % 2 else 0.012, span, 0.001); o.data.materials.append(gm); objs.append(o)
        k += 1
    k = math.floor((cy - span / 2) / step)
    while k * step < cy + span / 2:
        bpy.ops.mesh.primitive_cube_add(size=1, location=(cx, k * step, height))
        o = bpy.context.object; o.scale = (span, 0.006 if k % 2 else 0.012, 0.001); o.data.materials.append(gm); objs.append(o)
        k += 1
    bpy.ops.mesh.primitive_cylinder_add(radius=0.05, depth=0.002, location=(0, 0, height + 0.001))
    bpy.context.object.data.materials.append(om); objs.append(bpy.context.object)
    return objs


cam = bpy.data.objects.new("cam", bpy.data.cameras.new("cam"))
sc.collection.objects.link(cam)
sc.camera = cam
cam.data.type = "ORTHO"
cam.data.ortho_scale = span
top = result["ceiling_height"]
cam.location = (cx, cy, top + 5)
cam.rotation_euler = (0, 0, 0)
cam.data.clip_start = 5 + 0.25         # cut the ceiling (and anything in the top 25 cm) away
cam.data.clip_end = 100
helpers = grid_and_origin(-0.002)
sc.render.filepath = os.path.join(OUT, "plan.png")
bpy.ops.render.render(write_still=True)

# slice: thin bands of the scan at 3 heights, coloured, seen from above
for o in helpers:
    o.location.z = -0.5
src = obj
for zc, col in [(0.4, (1.0, 0.85, 0.2, 1)), (0.9, (0.3, 1.0, 0.4, 1)), (1.5, (1.0, 0.35, 0.8, 1))]:
    sl = src.copy(); sl.data = src.data.copy(); sc.collection.objects.link(sl)
    bm = bmesh.new(); bm.from_mesh(sl.data)
    kill = [f for f in bm.faces if not (zc - 0.04 < f.calc_center_median().z < zc + 0.04)]
    bmesh.ops.delete(bm, geom=kill, context="FACES")
    bm.to_mesh(sl.data); bm.free()
    m = bpy.data.materials.new("slice"); m.diffuse_color = col
    sl.data.materials.clear(); sl.data.materials.append(m)
    sl.location.z = 3 + zc                     # lift above the scan so it's drawn on top
src.hide_render = True
sc.display.shading.color_type = "MATERIAL"
cam.data.clip_start = 0.1
sc.render.filepath = os.path.join(OUT, "slice.png")
bpy.ops.render.render(write_still=True)
print("Wrote", OUT)
