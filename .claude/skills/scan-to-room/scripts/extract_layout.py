"""Pull a clean, modelable layout out of a room scan: straight walls (with door / window gaps),
floor finishes, and furniture footprints. The output drives a hand-written build script
(build_ground.py style) - it is a measuring tool, not a model.

  blender -b --factory-startup --python extract_layout.py -- <config.json> <out.json> [debug.png]

<config.json> is a scan_to_glb config (scan, rotation, offset, place, remove_boxes, ceiling_height).
All coordinates in the output are final (game) X / Y, heights relative to this storey's floor.

layout.json:
  walls:     [{"axis": "x"|"y", "at": 3.62, "from": 0.2, "to": 4.7, "thick": 0.1,
               "gaps": [{"from": 1.1, "to": 1.9, "kind": "door"|"opening"|"window",
                         "sill": 0.9, "head": 2.05}]}]
             axis "x": the wall runs along X at Y = at;  axis "y": runs along Y at X = at
  floors:    [{"material": 0, "colour": "#a0623a", "rects": [[x0, y0, x1, y1], ...]}]
  furniture: [{"x0":..,"y0":..,"x1":..,"y1":.., "top": 0.78, "seat": 0.45 or null,
               "colour": "#..", "area": 1.2}]
"""
import bpy, bmesh, sys, os, json, math
from collections import deque, defaultdict
from mathutils import Matrix, Vector

argv = sys.argv[sys.argv.index("--") + 1:]
C = json.load(open(argv[0]))
OUT = argv[1]
DBG = argv[2] if len(argv) > 2 else None
CEIL = C.get("ceiling_height", 2.5)
S = 0.05                               # raster cell (m)

# ---------------------------------------------------------------- load + place (floor at Z=0)
bpy.ops.wm.read_factory_settings(use_empty=True)
bpy.ops.import_scene.fbx(filepath=C["scan"])
bpy.context.view_layer.update()
M = (Matrix.Translation(C.get("offset", (0, 0, 0)))
     @ Matrix.Rotation(math.radians(C.get("rotation_deg", 0)), 4, "Z")
     @ Matrix.Scale(C.get("unit_scale", 1.0), 4))
if "place" in C:
    po = list(C["place"]["offset"]); po[2] = 0.0
    M = Matrix.Translation(po) @ Matrix.Rotation(math.radians(C["place"]["rotation_deg"]), 4, "Z") @ M
boxes = C.get("remove_boxes", [])
faces = []                              # (centre, normal, area, colour)
for o in [o for o in bpy.data.objects if o.type == "MESH"]:
    me = o.data
    mw = M @ o.matrix_world
    nm = mw.to_3x3()
    img = None
    for m in me.materials:
        if m and m.node_tree:
            for n in m.node_tree.nodes:
                if n.type == "TEX_IMAGE" and n.image:
                    img = n.image
    W = H = 0
    px = None
    if img:
        W, H = img.size
        px = img.pixels[:]
    uv = me.uv_layers.active.data if me.uv_layers else None
    for p in me.polygons:
        c = mw @ p.center
        if any(b[0] <= c.x <= b[3] and b[1] <= c.y <= b[4] and b[2] <= c.z <= b[5] for b in boxes):
            continue
        col = (0.6, 0.6, 0.6)
        if px and uv:
            u = sum(uv[i].uv.x for i in p.loop_indices) / p.loop_total
            v = sum(uv[i].uv.y for i in p.loop_indices) / p.loop_total
            x = min(W - 1, max(0, int((u % 1) * W))); y = min(H - 1, max(0, int((v % 1) * H)))
            k = (y * W + x) * 4
            col = (px[k], px[k + 1], px[k + 2])
        faces.append((c, (nm @ p.normal).normalized(), p.area, col))
print("LAYOUT faces", len(faces))


def cell(v):
    return (math.floor(v.x / S), math.floor(v.y / S))


# ---------------------------------------------------------------- walls
def wall_lines(axis):
    """axis 'y' = walls running along Y (normal +-X), 'x' = along X (normal +-Y)."""
    k_n = 0 if axis == "y" else 1        # normal component that must dominate
    k_pos = 0 if axis == "y" else 1      # coordinate that says where the wall is
    k_run = 1 - k_pos                    # coordinate along the wall
    bins = defaultdict(lambda: defaultdict(float))     # pos bin -> run bin -> area
    hi_bins = defaultdict(lambda: defaultdict(float))  # same, but 2.1 m .. ceiling (lintels)
    lo_bins = defaultdict(lambda: defaultdict(float))  # 0.15 .. 0.8 m (below windows)
    for c, n, a, _ in faces:
        if abs(n[k_n]) < 0.85:
            continue
        pb = round(c[k_pos] / S); rb = math.floor(c[k_run] / S)
        if 0.9 < c.z < 1.7:
            bins[pb][rb] += a
        elif 2.1 < c.z < CEIL - 0.05:
            hi_bins[pb][rb] += a
        elif 0.15 < c.z < 0.8:
            lo_bins[pb][rb] += a
    runs = []
    for pb, rbs in bins.items():
        occ = sorted(r for r, a in rbs.items() if a > 0.0005)
        if not occ:
            continue
        start = prev = occ[0]
        for r in occ[1:] + [None]:
            if r is not None and r - prev <= 3:           # bridge gaps up to 15 cm
                prev = r
                continue
            if (prev - start + 1) * S >= 0.45:
                area = sum(rbs.get(q, 0) for q in range(start, prev + 1))
                runs.append([pb * S, start * S, (prev + 1) * S, area])
            if r is not None:
                start = prev = r
    # merge runs on (nearly) the same line: both faces of one wall, scan wobble
    runs.sort(key=lambda r: r[0])
    lines = []
    for r in runs:
        for L in lines:
            if abs(L["at"] - r[0]) <= 0.16 and r[1] <= L["to"] + 0.2 and r[2] >= L["from"] - 0.2:
                L["parts"].append(r)
                L["from"] = min(L["from"], r[1]); L["to"] = max(L["to"], r[2])
                L["at"] = sum(p[0] * p[3] for p in L["parts"]) / sum(p[3] for p in L["parts"])
                break
        else:
            lines.append({"axis": "x" if axis == "x" else "y", "at": r[0], "from": r[1], "to": r[2],
                          "parts": [r]})
    out = []
    for L in lines:
        if L["to"] - L["from"] < 0.6:
            continue
        ats = [p[0] for p in L["parts"]]
        thick = max(0.08, min(0.3, max(ats) - min(ats) + S))
        # gaps along the line (where no part covers it)
        cover = sorted((p[1], p[2]) for p in L["parts"])
        gaps, cur = [], cover[0][1]
        for a, b in cover[1:]:
            if a > cur + 0.3:
                gaps.append([cur, a])
            cur = max(cur, b)
        gl = []
        pb_lo, pb_hi = round((L["at"] - 0.15) / S), round((L["at"] + 0.15) / S)
        for g0, g1 in gaps:
            rb0, rb1 = math.floor(g0 / S) + 1, math.floor(g1 / S) - 1
            def has(binset):
                return sum(binset[pb].get(rb, 0) for pb in range(pb_lo, pb_hi + 1)
                           for rb in range(rb0, rb1 + 1)) > 0.01
            above, below = has(hi_bins), has(lo_bins)
            w = g1 - g0
            kind = "window" if (below and w > 0.4) else ("door" if (above and w < 1.3) else "opening")
            gl.append({"from": round(g0, 2), "to": round(g1, 2), "kind": kind})
        out.append({"axis": L["axis"], "at": round(L["at"], 2), "from": round(L["from"], 2),
                    "to": round(L["to"], 2), "thick": round(thick, 2), "gaps": gl,
                    "strength": round(sum(p[3] for p in L["parts"]), 2)})
    return out


walls = wall_lines("y") + wall_lines("x")
walls.sort(key=lambda w: -w["strength"])
print("LAYOUT walls", len(walls))

# ---------------------------------------------------------------- floors (finish clusters)
G = 0.1
fcol = defaultdict(lambda: [0, 0, 0, 0])
for c, n, a, col in faces:
    if n.z > 0.85 and abs(c.z) < 0.06:
        k = (math.floor(c.x / G), math.floor(c.y / G))
        f = fcol[k]
        f[0] += col[0] * a; f[1] += col[1] * a; f[2] += col[2] * a; f[3] += a
cells = {k: (v[0] / v[3], v[1] / v[3], v[2] / v[3]) for k, v in fcol.items() if v[3] > 0}
# k-means (4 finishes) on the cell colours
import random
random.seed(3)
cents = random.sample(list(cells.values()), min(4, len(cells)))
for _ in range(15):
    groups = defaultdict(list)
    for k, c in cells.items():
        j = min(range(len(cents)), key=lambda j: sum((c[t] - cents[j][t]) ** 2 for t in range(3)))
        groups[j].append(k)
    cents = [tuple(sum(cells[k][t] for k in groups[j]) / len(groups[j]) for t in range(3)) if groups[j] else cents[j]
             for j in range(len(cents))]
lab = {}
for j, ks in groups.items():
    for k in ks:
        lab[k] = j
# majority filter (removes speckle), twice
for _ in range(2):
    new = {}
    for k in lab:
        cnt = defaultdict(int)
        for di in (-2, -1, 0, 1, 2):
            for dj in (-2, -1, 0, 1, 2):
                q = (k[0] + di, k[1] + dj)
                if q in lab:
                    cnt[lab[q]] += 1
        new[k] = max(cnt, key=cnt.get)
    lab = new


def rects(cellset):
    """Greedy merge of grid cells into rectangles."""
    left = set(cellset); out = []
    while left:
        i, j = min(left)
        j1 = j
        while (i, j1 + 1) in left:
            j1 += 1
        i1 = i
        while all((i1 + 1, q) in left for q in range(j, j1 + 1)):
            i1 += 1
        for a in range(i, i1 + 1):
            for b in range(j, j1 + 1):
                left.discard((a, b))
        out.append([round(i * G, 2), round(j * G, 2), round((i1 + 1) * G, 2), round((j1 + 1) * G, 2)])
    return out


def hexc(c):
    return "#%02x%02x%02x" % tuple(int(max(0, min(1, v)) ** (1 / 2.2) * 255) for v in c)


floors = []
for j in range(len(cents)):
    cs = [k for k, v in lab.items() if v == j]
    if len(cs) * G * G < 0.5:
        continue
    floors.append({"material": j, "colour": hexc(cents[j]), "area": round(len(cs) * G * G, 1),
                   "rects": [r for r in rects(cs) if (r[2] - r[0]) * (r[3] - r[1]) >= 0.04]})
print("LAYOUT floors", [(f["colour"], f["area"]) for f in floors])

# ---------------------------------------------------------------- furniture
occ = defaultdict(list)         # 5 cm cell -> [(z, colour, area)] of stuff 0.1 .. 2.0 m up
for c, n, a, col in faces:
    if 0.1 < c.z < 2.1:
        occ[cell(c)].append((c.z, col, a, n.z))
wall_cells = set()
for w in walls:
    for t in range(int(w["from"] / S), int(w["to"] / S) + 1):
        for d in range(-3, 4):
            if w["axis"] == "y":
                wall_cells.add((round(w["at"] / S) + d, t))
            else:
                wall_cells.add((t, round(w["at"] / S) + d))
fc = {k for k, v in occ.items() if k not in wall_cells and sum(x[2] for x in v) > 0.0004}
seen = set(); furniture = []
for k in fc:
    if k in seen:
        continue
    q = deque([k]); comp = []; seen.add(k)
    while q:
        a = q.popleft(); comp.append(a)
        for di in (-1, 0, 1):
            for dj in (-1, 0, 1):
                b = (a[0] + di, a[1] + dj)
                if b in fc and b not in seen:
                    seen.add(b); q.append(b)
    area = len(comp) * S * S
    if area < 0.08:
        continue
    zs = sorted(z for c_ in comp for z, _, _, _ in occ[c_])
    tops = sorted(z for c_ in comp for z, _, _, nz in occ[c_] if nz > 0.8)
    cols = [col for c_ in comp for _, col, _, _ in occ[c_]]
    mc = tuple(sorted(c[t] for c in cols)[len(cols) // 2] for t in range(3))
    xs = [c_[0] for c_ in comp]; ys = [c_[1] for c_ in comp]
    top = zs[int(len(zs) * 0.97) - 1] if zs else 0
    seat = None
    if tops:
        hist = defaultdict(int)
        for z in tops:
            hist[round(z / 0.05)] += 1
        best = max(hist, key=hist.get) * 0.05
        if best < top - 0.15:
            seat = round(best, 2)          # a big flat surface well below the top: seat / bed / desk
    furniture.append({"x0": round(min(xs) * S, 2), "y0": round(min(ys) * S, 2),
                      "x1": round((max(xs) + 1) * S, 2), "y1": round((max(ys) + 1) * S, 2),
                      "top": round(top, 2), "seat": seat, "colour": hexc(mc), "area": round(area, 2)})
furniture.sort(key=lambda f: -f["area"])
print("LAYOUT furniture", len(furniture))
json.dump({"walls": walls, "floors": floors, "furniture": furniture,
           "ceiling_height": CEIL}, open(OUT, "w"), indent=1)

# ---------------------------------------------------------------- debug picture
if DBG:
    bpy.ops.wm.read_factory_settings(use_empty=True)
    sc = bpy.context.scene
    def box(x0, y0, x1, y1, z, h, col):
        bpy.ops.mesh.primitive_cube_add(size=1, location=((x0 + x1) / 2, (y0 + y1) / 2, z + h / 2))
        o = bpy.context.object; o.scale = (max(0.01, x1 - x0), max(0.01, y1 - y0), h)
        m = bpy.data.materials.new("m"); m.diffuse_color = col; o.data.materials.append(m)
    def rgb(h):
        return tuple(int(h[i:i + 2], 16) / 255 for i in (1, 3, 5)) + (1,)
    for f in floors:
        for r in f["rects"]:
            box(r[0], r[1], r[2], r[3], 0, 0.01, rgb(f["colour"]))
    for f in furniture:
        box(f["x0"], f["y0"], f["x1"], f["y1"], 0.02, 0.05, (1, 0.3, 0.2, 1))
    for w in walls:
        t = w["thick"] / 2
        segs, cur = [], w["from"]
        for g in w["gaps"]:
            segs.append((cur, g["from"])); cur = g["to"]
            gc = {"door": (0, 0.8, 0, 1), "window": (0, 0.6, 1, 1), "opening": (1, 0.8, 0, 1)}[g["kind"]]
            if w["axis"] == "y":
                box(w["at"] - t, g["from"], w["at"] + t, g["to"], 0.1, 0.05, gc)
            else:
                box(g["from"], w["at"] - t, g["to"], w["at"] + t, 0.1, 0.05, gc)
        segs.append((cur, w["to"]))
        for a, b in segs:
            if w["axis"] == "y":
                box(w["at"] - t, a, w["at"] + t, b, 0.1, 0.06, (0, 0, 0, 1))
            else:
                box(a, w["at"] - t, b, w["at"] + t, 0.1, 0.06, (0, 0, 0, 1))
    for x in range(-20, 30):
        box(x - 0.01, -20, x + 0.01, 30, 0.2, 0.001, (0.3, 0.5, 1, 1))
        box(-20, x - 0.01, 30, x + 0.01, 0.2, 0.001, (0.3, 0.5, 1, 1))
    allx = [w["from"] for w in walls if w["axis"] == "x"] + [w["at"] for w in walls if w["axis"] == "y"]
    ally = [w["from"] for w in walls if w["axis"] == "y"] + [w["at"] for w in walls if w["axis"] == "x"]
    x0, x1 = min(allx), max(allx + [w["to"] for w in walls if w["axis"] == "x"])
    y0, y1 = min(ally), max(ally + [w["to"] for w in walls if w["axis"] == "y"])
    for xi in range(math.floor(x0), math.ceil(x1) + 1):
        for yi in range(math.floor(y0), math.ceil(y1) + 1):
            bpy.ops.object.text_add(location=(xi + 0.03, yi + 0.03, 0.3))
            t = bpy.context.object; t.data.body = f"{xi},{yi}"; t.data.size = 0.18
            m = bpy.data.materials.new("t"); m.diffuse_color = (0, 0.2, 0.8, 1); t.data.materials.append(m)
    sc.render.engine = "BLENDER_WORKBENCH"; sc.display.shading.light = "FLAT"
    sc.display.shading.color_type = "MATERIAL"
    sc.world = bpy.data.worlds.new("w"); sc.world.color = (1, 1, 1)
    cam = bpy.data.objects.new("cam", bpy.data.cameras.new("cam")); sc.collection.objects.link(cam)
    sc.camera = cam; cam.data.type = "ORTHO"
    span_x, span_y = x1 - x0 + 1, y1 - y0 + 1
    cam.data.ortho_scale = max(span_x, span_y)
    cam.location = ((x0 + x1) / 2, (y0 + y1) / 2, 10)
    sc.render.resolution_x = 2000 if span_x >= span_y else int(2000 * span_x / span_y)
    sc.render.resolution_y = 2000 if span_y > span_x else int(2000 * span_y / span_x)
    sc.render.filepath = DBG
    bpy.ops.render.render(write_still=True)
print("LAYOUT done", OUT)
