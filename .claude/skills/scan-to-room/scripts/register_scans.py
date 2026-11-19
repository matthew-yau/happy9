"""Find how a new scan sits relative to an already-placed one, using geometry they share
(a staircase seen from both floors, a doorway both scans looked through, ...).

  blender -b --factory-startup --python register_scans.py -- <config.json>

config:
{
  "fixed":  {"scan": "...room2_scan.fbx", "rotation_deg": -88.69, "offset": [..],
             "place": {"rotation_deg": 180, "offset": [12.32, 9.31, 0]},
             "region": [x0, y0, z0, x1, y1, z1]},      # shared part, in final (game) coords
  "moving": {"scan": "...ground_scan.fbx", "rotation_deg": -13.64, "offset": [..],
             "region": [x0, y0, z0, x1, y1, z1]},      # shared part, in its straightened coords
  "z_range": [-3.4, -2.5],      # where the moving scan's floor can be relative to the fixed one
  "xy_search": 1.5              # +- metres around the centroid match
}
Tries the four 90-degree turns, then a fine search over x, y, z and a few degrees of turn,
scoring how many shared points land within 4 cm of the other scan's surface. Prints the best
"place" block (rotation + offset applied after straightening) for the moving scan.
"""
import bpy, sys, json, math, random
from mathutils import Matrix, Vector
from mathutils.kdtree import KDTree

C = json.load(open(sys.argv[sys.argv.index("--") + 1]))


def straighten(cfg):
    M = (Matrix.Translation(cfg.get("offset", (0, 0, 0)))
         @ Matrix.Rotation(math.radians(cfg.get("rotation_deg", 0)), 4, "Z")
         @ Matrix.Scale(cfg.get("unit_scale", 1.0), 4))
    if "place" in cfg:
        P = cfg["place"]
        M = (Matrix.Translation(P.get("offset", (0, 0, 0)))
             @ Matrix.Rotation(math.radians(P.get("rotation_deg", 0)), 4, "Z")) @ M
    return M


def points(cfg, limit):
    bpy.ops.wm.read_factory_settings(use_empty=True)
    bpy.ops.import_scene.fbx(filepath=cfg["scan"])
    bpy.context.view_layer.update()
    M = straighten(cfg)
    r = cfg["region"]
    pts = []
    for o in [o for o in bpy.data.objects if o.type == "MESH"]:
        mw = M @ o.matrix_world
        for v in o.data.vertices:
            p = mw @ v.co
            if r[0] <= p.x <= r[3] and r[1] <= p.y <= r[4] and r[2] <= p.z <= r[5]:
                pts.append(p)
    random.seed(1)
    random.shuffle(pts)
    return pts[:limit]


F = points(C["fixed"], 200000)
Gm = points(C["moving"], 1500)
print("REG points fixed", len(F), "moving", len(Gm))
kd = KDTree(len(F))
for i, p in enumerate(F):
    kd.insert(p, i)
kd.balance()
fc = sum(F, Vector()) / len(F)
gc = sum(Gm, Vector()) / len(Gm)
z0, z1 = C.get("z_range", [-3.5, -2.4])


def score(rot_deg, t, pts, tol=0.04):
    R = Matrix.Rotation(math.radians(rot_deg), 3, "Z")
    n = 0
    for p in pts:
        q = R @ p + t
        if kd.find(q)[2] < tol:
            n += 1
    return n


best = (-1, None)
sub = Gm[:250]
span = C.get("xy_search", 1.5)
for rot in (0, 90, 180, 270):
    R = Matrix.Rotation(math.radians(rot), 3, "Z")
    base = fc - R @ gc                                # centroids on top of each other (xy)
    for dz in [z0 + k * 0.05 for k in range(int((z1 - z0) / 0.05) + 1)]:
        for ix in range(-int(span / 0.1), int(span / 0.1) + 1):
            for iy in range(-int(span / 0.1), int(span / 0.1) + 1):
                t = Vector((base.x + ix * 0.1, base.y + iy * 0.1, dz))
                s = score(rot, t, sub, 0.08)
                if s > best[0]:
                    best = (s, (rot, t.copy()))
    print("REG turn", rot, "best so far", best[0], tuple(round(v, 2) for v in best[1][1]), best[1][0])

# refine: small steps in x, y, z and angle with the full point set
s0, (rot, t) = best
cur = (score(rot, t, Gm), rot, t)
for step, astep in ((0.04, 1.0), (0.02, 0.5), (0.01, 0.25)):
    improved = True
    while improved:
        improved = False
        for d in (Vector((step, 0, 0)), Vector((-step, 0, 0)), Vector((0, step, 0)),
                  Vector((0, -step, 0)), Vector((0, 0, step)), Vector((0, 0, -step))):
            s = score(cur[1], cur[2] + d, Gm)
            if s > cur[0]:
                cur = (s, cur[1], cur[2] + d); improved = True
        for da in (astep, -astep):
            # rotate about the moving centroid so the angle change doesn't shift it
            a = cur[1] + da
            Ra, Rc = Matrix.Rotation(math.radians(a), 3, "Z"), Matrix.Rotation(math.radians(cur[1]), 3, "Z")
            t2 = cur[2] + Rc @ gc - Ra @ gc
            s = score(a, t2, Gm)
            if s > cur[0]:
                cur = (s, a, t2); improved = True
print("REG RESULT matched %d/%d (%.0f%%)" % (cur[0], len(Gm), 100.0 * cur[0] / len(Gm)))
print("REG PLACE", json.dumps({"rotation_deg": round(cur[1], 2),
                               "offset": [round(cur[2].x, 3), round(cur[2].y, 3), round(cur[2].z, 3)]}))
