import bpy, bmesh, math, os, sys
from mathutils import Vector, Matrix
# Optional: blender -b --factory-startup --python convert_characters.py -- p3   (only that one)
ONLY = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
OUT = r"C:\Users\thema\Downloads\newgame\RoomGame\models"
os.makedirs(OUT, exist_ok=True)
H = 1.22  # 4 ft tall

ROT = Matrix.Rotation(math.pi, 4, 'Z')   # face +Y in Blender = -Z in Godot


def mesh_bounds(meshes):
    bpy.context.view_layer.update()
    dg = bpy.context.evaluated_depsgraph_get()
    pts = []
    for o in meshes:
        m = o.evaluated_get(dg).to_mesh()
        pts += [o.matrix_world @ v.co for v in m.vertices]
    mn = Vector([min(p[i] for p in pts) for i in range(3)])
    mx = Vector([max(p[i] for p in pts) for i in range(3)])
    return mn, mx


def fit(mn, mx):
    s = H / (mx.z - mn.z)
    c = Vector(((mn.x + mx.x) / 2, (mn.y + mx.y) / 2, mn.z))
    return ROT @ Matrix.Scale(s, 4) @ Matrix.Translation(-c)


# ---- p2 (rigged, Walk animation)
if not ONLY or "p2" in ONLY:
  bpy.ops.wm.read_factory_settings(use_empty=True)
  bpy.ops.import_scene.fbx(filepath=r"C:\Users\thema\Downloads\p2\source\model.fbx")
  scene_objs = set(bpy.context.scene.objects)
  for ob in list(bpy.data.objects):
      if ob not in scene_objs:
          bpy.data.objects.remove(ob)          # bone-shape icospheres etc.
  meshes = [o for o in bpy.context.scene.objects if o.type == 'MESH']
  roots = [o for o in bpy.context.scene.objects if o.parent is None]
  mn, mx = mesh_bounds(meshes)
  top = bpy.data.objects.new("P2", None)
  bpy.context.scene.collection.objects.link(top)
  for r in roots:
      r.parent = top
  top.matrix_world = fit(mn, mx)
  for a in bpy.data.actions:
      a.name = "Walk"
  bpy.ops.export_scene.gltf(filepath=os.path.join(OUT, "p2.glb"), export_format='GLB',
                            export_animations=True)
  print("P2 after", mesh_bounds(meshes))

# ---- p3 (STL statue, no UVs): decimate, split into "dress" and "white" materials,
# then cut into posable pieces: Body, ArmL/ArmR (pivot at the shoulder), LegL/LegR (pivot at
# the hip). avatar.gd turns them for hugs, holding Bob and sitting.
P3_SHOULDER = Vector((0.11, 0.0, 0.50))   # Blender coords (Z up, face +Y), right side
P3_HIP = Vector((0.09, 0.0, 0.23))


def p3_split(o):
    bpy.context.view_layer.objects.active = o
    bpy.ops.object.select_all(action='DESELECT')
    o.select_set(True)
    bpy.ops.object.mode_set(mode='EDIT')
    bpy.ops.mesh.select_all(action='SELECT')
    bpy.ops.mesh.separate(type='LOOSE')
    bpy.ops.object.mode_set(mode='OBJECT')
    groups = {"Body": [], "ArmL": [], "ArmR": [], "LegL": [], "LegR": []}
    for ob in [x for x in bpy.context.scene.objects if x.type == 'MESH']:
        vs = [ob.matrix_world @ v.co for v in ob.data.vertices]
        c = (Vector([min(v[i] for v in vs) for i in range(3)]) + Vector([max(v[i] for v in vs) for i in range(3)])) / 2
        side = "L" if c.x < 0 else "R"          # facing -Z in Godot, -X is the left hand
        if c.z < 0.2:
            groups["Leg" + side].append(ob)       # legs + feet
        elif abs(c.x) > 0.12 and c.z < 0.5:
            groups["Arm" + side].append(ob)       # sleeve, arm, cuff, hand
        else:
            groups["Body"].append(ob)
    top = bpy.data.objects.new("P3", None)
    bpy.context.scene.collection.objects.link(top)
    for name, obs in groups.items():
        bpy.ops.object.select_all(action='DESELECT')
        for ob in obs:
            ob.select_set(True)
        bpy.context.view_layer.objects.active = obs[0]
        if len(obs) > 1:
            bpy.ops.object.join()
        ob = bpy.context.view_layer.objects.active
        ob.name = name
        ob.data.name = name
        piv = Vector((0, 0, 0))
        if name != "Body":
            piv = (P3_SHOULDER if name.startswith("Arm") else P3_HIP).copy()
            if name.endswith("L"):
                piv.x = -piv.x
        bpy.context.scene.cursor.location = piv
        bpy.ops.object.origin_set(type='ORIGIN_CURSOR')
        ob.parent = top
        print("P3 piece", name, len(obs), "parts", len(ob.data.vertices), "verts")


if not ONLY or "p3" in ONLY:
  bpy.ops.wm.read_factory_settings(use_empty=True)
  bpy.ops.wm.stl_import(filepath=r"C:\Users\thema\Downloads\p3\source\player1.stl")
  o = bpy.data.objects[0]
  o.name = "P3"
  bpy.context.view_layer.objects.active = o
  o.select_set(True)
  mod = o.modifiers.new("dec", 'DECIMATE')
  mod.ratio = 0.2
  bpy.ops.object.modifier_apply(modifier="dec")
  mn, mx = mesh_bounds([o])
  o.matrix_world = fit(mn, mx)
  bpy.ops.object.transform_apply(location=True, rotation=True, scale=True)
  for n, col in [("white", (0.96, 0.95, 0.92, 1)), ("dress", (0.95, 0.5, 0.15, 1))]:
      m = bpy.data.materials.new(n)
      m.diffuse_color = col
      bsdf = m.node_tree.nodes.get("Principled BSDF")
      if bsdf:
          bsdf.inputs["Base Color"].default_value = col
          bsdf.inputs["Roughness"].default_value = 0.8
      o.data.materials.append(m)
  bm = bmesh.new()
  bm.from_mesh(o.data)
  k = H / 1.75   # dress limits were tuned at 1.75 m
  for f in bm.faces:
      c = f.calc_center_median()
      f.material_index = 1 if (0.16 * k < c.z < 0.78 * k and abs(c.x) < 0.33 * k) else 0
  bm.to_mesh(o.data)
  bm.free()
  bpy.ops.object.shade_smooth()
  print("P3 after", len(o.data.vertices), mesh_bounds([o]))
  p3_split(o)
  bpy.ops.export_scene.gltf(filepath=os.path.join(OUT, "p3.glb"), export_format='GLB')
