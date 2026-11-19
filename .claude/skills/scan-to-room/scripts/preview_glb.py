"""Render pictures of one or more game .glb files so you can check them without opening the game.

  blender -b --factory-startup --python preview_glb.py -- <out folder> <a.glb> [b.glb ...]
        [--eye x,y,z,yaw_deg ...]     (extra first-person views, Blender room coords, yaw 0 = +Y)

Writes top.png (cut-away plan, 1 m grid, origin red) and view_N.png for each --eye.
"""
import bpy, sys, os, math
from mathutils import Vector

argv = sys.argv[sys.argv.index("--") + 1:]
OUT = argv[0]
files, eyes = [], []
i = 1
while i < len(argv):
    if argv[i] == "--eye":
        eyes.append([float(v) for v in argv[i + 1].split(",")]); i += 2
    else:
        files.append(argv[i]); i += 1
os.makedirs(OUT, exist_ok=True)
bpy.ops.wm.read_factory_settings(use_empty=True)
for f in files:
    bpy.ops.import_scene.gltf(filepath=f)
sc = bpy.context.scene
meshes = [o for o in sc.objects if o.type == "MESH"]
pts = [o.matrix_world @ Vector(c) for o in meshes for c in o.bound_box]
mn = Vector([min(p[k] for p in pts) for k in range(3)])
mx = Vector([max(p[k] for p in pts) for k in range(3)])
sc.render.engine = "BLENDER_WORKBENCH"
sc.display.shading.light = "STUDIO"
sc.display.shading.color_type = "VERTEX"
sc.world = bpy.data.worlds.new("w")
sc.world.color = (0.05, 0.05, 0.07)
# objects with textures/material colours (the modelled room) still show: use material colour for them
for o in meshes:
    if not o.data.color_attributes:
        o.data.color_attributes.new("Col", "FLOAT_COLOR", "POINT")
        c = o.active_material.diffuse_color if o.active_material else (0.8, 0.8, 0.8, 1)
        bsdf = o.active_material.node_tree.nodes.get("Principled BSDF") if o.active_material else None
        if bsdf:
            c = bsdf.inputs["Base Color"].default_value
        for d in o.data.color_attributes["Col"].data:
            d.color = c
cam = bpy.data.objects.new("cam", bpy.data.cameras.new("cam"))
sc.collection.objects.link(cam)
sc.camera = cam

# grid (1 m) + origin
gm = bpy.data.materials.new("g")
for x in range(math.floor(mn.x), math.ceil(mx.x) + 1):
    bpy.ops.mesh.primitive_cube_add(size=1, location=(x, (mn.y + mx.y) / 2, -0.02))
    o = bpy.context.object; o.scale = (0.02, mx.y - mn.y + 1, 0.001)
for y in range(math.floor(mn.y), math.ceil(mx.y) + 1):
    bpy.ops.mesh.primitive_cube_add(size=1, location=((mn.x + mx.x) / 2, y, -0.02))
    o = bpy.context.object; o.scale = (mx.x - mn.x + 1, 0.02, 0.001)
for o in sc.objects:
    if o.type == "MESH" and o.name.startswith("Cube"):
        a = o.data.color_attributes.new("Col", "FLOAT_COLOR", "POINT")
        for d in a.data:
            d.color = (0.2, 0.6, 0.9, 1)
bpy.ops.mesh.primitive_cylinder_add(radius=0.12, depth=0.01, location=(0, 0, 3.0))
a = bpy.context.object.data.color_attributes.new("Col", "FLOAT_COLOR", "POINT")
for d in a.data:
    d.color = (1, 0.1, 0.1, 1)

span = max(mx.x - mn.x, mx.y - mn.y) + 1
cam.data.type = "ORTHO"
cam.data.ortho_scale = span
cam.location = ((mn.x + mx.x) / 2, (mn.y + mx.y) / 2, 20)
cam.rotation_euler = (0, 0, 0)
cam.data.clip_start = 20 - 2.2       # cut away everything above 2.2 m
cam.data.clip_end = 40
aspect = (mx.x - mn.x + 1) / (mx.y - mn.y + 1)
sc.render.resolution_x = 1600 if aspect >= 1 else int(1600 * aspect)
sc.render.resolution_y = int(1600 / aspect) if aspect >= 1 else 1600
sc.render.filepath = os.path.join(OUT, "top.png")
bpy.ops.render.render(write_still=True)

cam.data.type = "PERSP"
cam.data.lens = 16
cam.data.clip_start = 0.05
sc.render.resolution_x, sc.render.resolution_y = 1280, 720
for k, (x, y, z, yaw) in enumerate(eyes):
    cam.location = (x, y, z)
    cam.rotation_euler = (math.radians(88), 0, math.radians(yaw))
    sc.render.filepath = os.path.join(OUT, f"view_{k + 1}.png")
    bpy.ops.render.render(write_still=True)
print("PREVIEW done", OUT)
