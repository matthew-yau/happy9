"""Detailed, labelled top-down plans of a scan in final (game) coordinates - for modelling a
clean version of the level by hand (like build_flat.py / build_ground.py).

  blender -b --factory-startup --python plan_render.py -- <config.json> <out folder> [tile_m]

Uses the scan / rotation / offset / place of a scan_to_glb config (heights are relative to that
storey's floor). Splits the area into tiles (default 6 m square) and writes for each tile:
  tile_<i>_<j>_photo.png   textured, cut at 2.0 m (furniture, floor finishes, doors)
  tile_<i>_<j>_walls.png   black = scan surfaces between 0.9 and 1.7 m (walls, tall furniture)
                           red = between 0.2 and 0.6 m (low furniture, bed / sofa seats)
Each has a 0.5 m grid (1 m lines darker) labelled with final X / Y coordinates.
"""
import bpy, bmesh, sys, os, json, math
from mathutils import Matrix, Vector

argv = sys.argv[sys.argv.index("--") + 1:]
C = json.load(open(argv[0]))
OUT = argv[1]
TILE = float(argv[2]) if len(argv) > 2 else 6.0
os.makedirs(OUT, exist_ok=True)

bpy.ops.wm.read_factory_settings(use_empty=True)
bpy.ops.import_scene.fbx(filepath=C["scan"])
bpy.context.view_layer.update()
M = (Matrix.Translation(C.get("offset", (0, 0, 0)))
     @ Matrix.Rotation(math.radians(C.get("rotation_deg", 0)), 4, "Z")
     @ Matrix.Scale(C.get("unit_scale", 1.0), 4))
if "place" in C:
    po = list(C["place"]["offset"]); po[2] = 0.0
    M = Matrix.Translation(po) @ Matrix.Rotation(math.radians(C["place"]["rotation_deg"]), 4, "Z") @ M
meshes = [o for o in bpy.data.objects if o.type == "MESH"]
for o in meshes:
    o.parent = None
bpy.context.view_layer.update()
for o in meshes:
    o.data.transform(M @ o.matrix_world)
    o.matrix_world = Matrix.Identity(4)
for o in [o for o in bpy.data.objects if o.type != "MESH"]:
    bpy.data.objects.remove(o, do_unlink=True)
scan = meshes[0]
if len(meshes) > 1:
    bpy.ops.object.select_all(action="DESELECT")
    for o in meshes:
        o.select_set(True)
    bpy.context.view_layer.objects.active = scan
    bpy.ops.object.join()
pts = [v.co for v in scan.data.vertices]
x0, x1 = min(p.x for p in pts), max(p.x for p in pts)
y0, y1 = min(p.y for p in pts), max(p.y for p in pts)


def band(name, zlo, zhi, colour):
    o = scan.copy(); o.data = scan.data.copy(); o.name = name
    bpy.context.scene.collection.objects.link(o)
    bm = bmesh.new(); bm.from_mesh(o.data)
    bmesh.ops.delete(bm, geom=[f for f in bm.faces if not (zlo < f.calc_center_median().z < zhi)], context="FACES")
    bm.to_mesh(o.data); bm.free()
    m = bpy.data.materials.new(name); m.diffuse_color = colour
    o.data.materials.clear(); o.data.materials.append(m)
    o.location.z = 10 + zhi           # above everything, so it's drawn on top
    return o


walls = band("walls", 0.9, 1.7, (0.05, 0.05, 0.05, 1))
low = band("low", 0.2, 0.6, (0.85, 0.15, 0.1, 1))
low.location.z = 9.0

sc = bpy.context.scene
sc.render.engine = "BLENDER_WORKBENCH"
sc.display.shading.light = "FLAT"
sc.world = bpy.data.worlds.new("w")
sc.world.color = (1, 1, 1)
sc.render.resolution_x = sc.render.resolution_y = 1200
cam = bpy.data.objects.new("cam", bpy.data.cameras.new("cam"))
sc.collection.objects.link(cam); sc.camera = cam
cam.data.type = "ORTHO"; cam.data.ortho_scale = TILE

# grid + labels
gm = []
def colour_obj(o, c):
    m = bpy.data.materials.new("c"); m.diffuse_color = c
    o.data.materials.clear(); o.data.materials.append(m)
for k in range(math.floor(x0 * 2), math.ceil(x1 * 2) + 1):
    x = k / 2
    bpy.ops.mesh.primitive_cube_add(size=1, location=(x, (y0 + y1) / 2, 20))
    o = bpy.context.object; o.scale = (0.012 if k % 2 == 0 else 0.005, y1 - y0 + 2, 0.001)
    colour_obj(o, (0.1, 0.45, 0.9, 1) if k % 2 == 0 else (0.55, 0.75, 1, 1)); gm.append(o)
for k in range(math.floor(y0 * 2), math.ceil(y1 * 2) + 1):
    y = k / 2
    bpy.ops.mesh.primitive_cube_add(size=1, location=((x0 + x1) / 2, y, 20))
    o = bpy.context.object; o.scale = (x1 - x0 + 2, 0.012 if k % 2 == 0 else 0.005, 0.001)
    colour_obj(o, (0.1, 0.45, 0.9, 1) if k % 2 == 0 else (0.55, 0.75, 1, 1)); gm.append(o)
labels = []
for xi in range(math.floor(x0), math.ceil(x1) + 1):
    for yi in range(math.floor(y0), math.ceil(y1) + 1):
        bpy.ops.object.text_add(location=(xi + 0.03, yi + 0.03, 21))
        t = bpy.context.object; t.data.body = f"{xi},{yi}"; t.data.size = 0.13
        colour_obj(t, (0.0, 0.25, 0.75, 1)); labels.append(t)

nx = max(1, math.ceil((x1 - x0) / TILE)); ny = max(1, math.ceil((y1 - y0) / TILE))
for i in range(nx):
    for j in range(ny):
        cx = x0 + (i + 0.5) * TILE; cy = y0 + (j + 0.5) * TILE
        # photo: scan cut at 2.0 m, bands hidden
        cam.location = (cx, cy, 30); cam.rotation_euler = (0, 0, 0)
        cam.data.clip_start = 30 - 2.0; cam.data.clip_end = 40
        sc.display.shading.color_type = "TEXTURE"
        for o in (walls, low):
            o.hide_render = True
        for o in gm + labels:
            o.location.z = 2.0 - 0.01 if o in gm else 2.0 - 0.005
        scan.hide_render = False
        sc.render.filepath = os.path.join(OUT, f"tile_{i}_{j}_photo.png")
        bpy.ops.render.render(write_still=True)
        # walls: only the bands
        cam.location = (cx, cy, 40); cam.data.clip_start = 0.1; cam.data.clip_end = 100
        sc.display.shading.color_type = "MATERIAL"
        scan.hide_render = True
        for o in (walls, low):
            o.hide_render = False
        for o in gm:
            o.location.z = 25
        for o in labels:
            o.location.z = 26
        sc.render.filepath = os.path.join(OUT, f"tile_{i}_{j}_walls.png")
        bpy.ops.render.render(write_still=True)
        print("TILE", i, j, "x %.1f..%.1f y %.1f..%.1f" % (cx - TILE / 2, cx + TILE / 2, cy - TILE / 2, cy + TILE / 2))
print("PLAN done", OUT)
