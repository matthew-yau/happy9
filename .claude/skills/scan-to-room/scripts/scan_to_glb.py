"""Turn a 3D room scan into a clean, game-ready .glb (no photo textures).

Run with Blender (no window needed):
  blender -b --factory-startup --python scan_to_glb.py -- <config.json>

config.json (all lengths in metres; "final" coordinates = the game's Blender room coordinates):
{
  "scan": "C:/.../room2_scan.fbx",
  "out": "C:/.../RoomGame/flat.glb",
  "name": "Flat",                       # prefix for object names
  "unit_scale": 1.0,                    # from measure.json
  "rotation_deg": -88.69,               # from measure.json (straightens the walls)
  "offset": [6.979, 2.851, -1.022],     # from measure.json (floor to Z=0, corner to 0,0)
  "place": {"rotation_deg": 180, "offset": [12.32, 9.31, 0]},   # optional: then move into the
                                        #   (offset z = this storey's floor height, e.g. -2.76)
                                        #   existing room's coordinates (rotate about 0,0 first)
  "decimate": 0.3,                      # keep this fraction of triangles
  "remove_boxes": [[x0,y0,z0, x1,y1,z1], ...],   # final x/y, z with this storey's floor at 0;
                                        #   scan faces inside are deleted
                                        #   (e.g. the part of another room seen through a door)
  "keep_z": [-0.08, 2.6],               # delete scan faces below / above (reflections, noise)
  "keep_boxes": [[x0,y0,z0, x1,y1,z1]], # never trimmed by keep_z / floor / ceiling rules (stairs)
  "floor_holes": [[x0,y0, x1,y1]],      # no rebuilt floor / backdrop here (stairwell from above)
  "ceiling_holes": [[x0,y0, x1,y1]],    # no rebuilt ceiling here (where the stairs go up)
  "ramps": [{"from": [x,y,z], "to": [x,y,z], "width": 0.9}],   # hidden walkable stair ramps
  "min_island_faces": 150,              # delete floating bits smaller than this
  "colour_smooth": 10,                  # colour blur passes (0 = keep photo detail as colours)
  "fill_hole_sides": 80,                # fill holes whose rim has up to this many edges
  "rebuild_floor": true,                # replace the scanned floor with a flat clean one
  "rebuild_ceiling": true,              # replace the scanned ceiling with a clean flat one
  "ceiling_colour": [0.9, 0.9, 0.88],   # optional: paint it this colour (scanned ones are dark)
  "ceiling_height": 2.42,
  "slab_margin": 0.5,                   # clean floor/ceiling reach this far past the walls
  "backdrop": true,                     # clean shell round the outside: windows/holes show it
  "backdrop_colour": [0.78, 0.86, 0.95],
  "grid": 0.1,                          # cell size for the rebuilt floor / ceiling
  "footprint_trim": 0.5,                # delete scan bits more than this far outside the floor
  "light_spacing": 2.6,                 # ceiling light markers ("<name>_Light_N") every ~N metres
  "collision": "godot"                  # "-col" names so Godot makes them solid; "none" = off
}

What it does: import -> straighten/place -> decimate -> bake the photo texture into per-vertex
colours -> delete the photo texture -> blur the colours -> remove junk (boxes, below floor,
above ceiling, outside the footprint, tiny islands) -> fill holes (their colours are
interpolated from the rim) -> rebuild floor / ceiling from a grid (empty cells take the average
colour of their neighbours) -> backdrop shell -> light markers -> export .glb with vertex colours only.
"""
import bpy, bmesh, sys, os, math, json
from collections import deque
from mathutils import Matrix, Vector

argv = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
if not argv:
    raise SystemExit("usage: blender -b --python scan_to_glb.py -- config.json")
with open(argv[0]) as fh:
    C = json.load(fh)
NAME = C.get("name", "Scan")
G = C.get("grid", 0.1)
CEIL = C.get("ceiling_height", 2.4)


def log(*a):
    print("[scan_to_glb]", *a, flush=True)


# ---------------------------------------------------------------- import + place
bpy.ops.wm.read_factory_settings(use_empty=True)
ext = os.path.splitext(C["scan"])[1].lower()
importers = {".fbx": lambda p: bpy.ops.import_scene.fbx(filepath=p),
             ".obj": lambda p: bpy.ops.wm.obj_import(filepath=p),
             ".glb": lambda p: bpy.ops.import_scene.gltf(filepath=p),
             ".gltf": lambda p: bpy.ops.import_scene.gltf(filepath=p),
             ".ply": lambda p: bpy.ops.wm.ply_import(filepath=p),
             ".usdz": lambda p: bpy.ops.wm.usd_import(filepath=p),
             ".usd": lambda p: bpy.ops.wm.usd_import(filepath=p)}
importers[ext](C["scan"])
bpy.context.view_layer.update()
meshes = [o for o in bpy.data.objects if o.type == "MESH"]
M = (Matrix.Translation(C.get("offset", (0, 0, 0)))
     @ Matrix.Rotation(math.radians(C.get("rotation_deg", 0)), 4, "Z")
     @ Matrix.Scale(C.get("unit_scale", 1.0), 4))
LIFT = 0.0
if "place" in C:
    P = C["place"]
    po = list(P.get("offset", (0, 0, 0)))
    LIFT = po[2] if len(po) > 2 else 0.0     # the height is applied at export: everything below
    po = (po[0], po[1], 0.0)                 # works with this floor at Z = 0
    M = (Matrix.Translation(po)
         @ Matrix.Rotation(math.radians(P.get("rotation_deg", 0)), 4, "Z")) @ M
for o in meshes:
    o.parent = None
bpy.context.view_layer.update()
for o in meshes:
    o.data.transform(M @ o.matrix_world)
    o.matrix_world = Matrix.Identity(4)
for o in [o for o in bpy.data.objects if o.type != "MESH"]:
    bpy.data.objects.remove(o, do_unlink=True)
bpy.ops.object.select_all(action="DESELECT")
for o in meshes:
    o.select_set(True)
bpy.context.view_layer.objects.active = meshes[0]
if len(meshes) > 1:
    bpy.ops.object.join()
scan = bpy.context.view_layer.objects.active
scan.name = NAME + "_Scan"
log("imported", len(scan.data.polygons), "faces")

if C.get("decimate", 1.0) < 1.0:
    # Scans come split along their texture seams: weld them first so the mesh is connected
    # (texture coordinates live on the corners, so they survive), then simplify.
    bmw = bmesh.new()
    bmw.from_mesh(scan.data)
    n0 = len(bmw.verts)
    bmesh.ops.remove_doubles(bmw, verts=bmw.verts, dist=0.0005)
    bmw.to_mesh(scan.data)
    bmw.free()
    log("welded seams:", n0, "->", len(scan.data.vertices), "vertices")
    d = scan.modifiers.new("dec", "DECIMATE")
    d.ratio = C["decimate"]
    bpy.ops.object.modifier_apply(modifier="dec")
    log("decimated to", len(scan.data.polygons), "faces")

# ---------------------------------------------------------------- texture -> vertex colours
me = scan.data
images = {}
for i, m in enumerate(me.materials):
    if m and m.node_tree:
        for n in m.node_tree.nodes:
            if n.type == "TEX_IMAGE" and n.image:
                images[i] = n.image
                break
pix = {}
for i, img in images.items():
    pix[i] = (img.size[0], img.size[1], img.pixels[:])
nv = len(me.vertices)
acc = [[0.0, 0.0, 0.0, 0] for _ in range(nv)]
uvl = me.uv_layers.active.data if me.uv_layers else None
if uvl and pix:
    for p in me.polygons:
        if p.material_index not in pix:
            continue
        W, H, px = pix[p.material_index]
        for li in p.loop_indices:
            u, v = uvl[li].uv
            x = min(W - 1, max(0, int((u % 1.0) * W)))
            y = min(H - 1, max(0, int((v % 1.0) * H)))
            k = (y * W + x) * 4
            a = acc[me.loops[li].vertex_index]
            a[0] += px[k]; a[1] += px[k + 1]; a[2] += px[k + 2]; a[3] += 1
known = [a[3] > 0 for a in acc]
col = [(a[0] / a[3], a[1] / a[3], a[2] / a[3]) if a[3] else (0.6, 0.6, 0.6) for a in acc]
log("baked colours from", len(images), "texture(s)")

# blur over the mesh (neighbour averaging); unknown vertices get filled in from neighbours
nbr = [[] for _ in range(nv)]
for e in me.edges:
    a, b = e.vertices
    nbr[a].append(b); nbr[b].append(a)
for it in range(max(C.get("colour_smooth", 10), 1 if not all(known) else 0)):
    new = []
    for i in range(nv):
        r = g = b = 0.0; n = 0
        if known[i]:
            r, g, b = col[i]; n = 1
        for j in nbr[i]:
            if known[j]:
                c = col[j]; r += c[0]; g += c[1]; b += c[2]; n += 1
        new.append((r / n, g / n, b / n) if n else col[i])
    newly = [known[i] or any(known[j] for j in nbr[i]) for i in range(nv)]
    col, known = new, newly

# throw the photo textures away - only vertex colours are kept
for img in list(bpy.data.images):
    bpy.data.images.remove(img)
for m in list(me.materials):
    if m:
        bpy.data.materials.remove(m)
me.materials.clear()
while me.uv_layers:
    me.uv_layers.remove(me.uv_layers[0])

# ---------------------------------------------------------------- clean-up in bmesh
bm = bmesh.new()
bm.from_mesh(me)
bm.verts.ensure_lookup_table()
cl = bm.verts.layers.float_color.new("Col")
for v in bm.verts:
    c = col[v.index]
    v[cl] = (c[0], c[1], c[2], 1.0)


def inside(c, b):
    return b[0] <= c.x <= b[3] and b[1] <= c.y <= b[4] and b[2] <= c.z <= b[5]


kz0, kz1 = C.get("keep_z", [-0.08, CEIL + 0.2])
boxes = C.get("remove_boxes", [])
kill = []
floor_cells = {}          # (i, j) -> [r, g, b, n]   colours of the scanned floor
ceil_cells = {}
bm.normal_update()
keeps = C.get("keep_boxes", [])
for f in bm.faces:
    c = f.calc_center_median()
    if any(inside(c, b) for b in boxes):
        kill.append(f)
        continue
    if any(inside(c, b) for b in keeps):
        continue                    # e.g. stairs: never trimmed as "above the ceiling" / "floor"
    if c.z < kz0 or c.z > kz1:
        kill.append(f)
        continue
    n = f.normal
    cell = (math.floor(c.x / G), math.floor(c.y / G))
    if n.z > 0.8 and c.z < 0.07:
        fc = floor_cells.setdefault(cell, [0, 0, 0, 0])
        for v in f.verts:
            fc[0] += v[cl][0]; fc[1] += v[cl][1]; fc[2] += v[cl][2]; fc[3] += 1
        if C.get("rebuild_floor", True):
            kill.append(f)
    elif n.z < -0.8 and c.z > CEIL - 0.25:
        cc = ceil_cells.setdefault(cell, [0, 0, 0, 0])
        for v in f.verts:
            cc[0] += v[cl][0]; cc[1] += v[cl][1]; cc[2] += v[cl][2]; cc[3] += 1
        if C.get("rebuild_ceiling", True):
            kill.append(f)          # scanned ceilings are dark and patchy: use the clean one
bmesh.ops.delete(bm, geom=list(set(kill)), context="FACES")
log("removed", len(set(kill)), "faces (boxes / out of range / old floor)")

# Footprint = floor cells, closed (fills gaps under furniture), minus removed boxes
fp = set(floor_cells)


def dilate(s, r):
    out = set()
    for (i, j) in s:
        for di in range(-r, r + 1):
            for dj in range(-r, r + 1):
                out.add((i + di, j + dj))
    return out


def erode(s, r):
    return {c for c in s if all((c[0] + di, c[1] + dj) in s
                                for di in range(-r, r + 1) for dj in range(-r, r + 1))}


fp = erode(dilate(fp, 3), 3)
def in_box_cell(cell):
    x, y = (cell[0] + 0.5) * G, (cell[1] + 0.5) * G
    return any(b[0] <= x <= b[3] and b[1] <= y <= b[4] and b[2] <= 0.05 <= b[5] for b in boxes)
def in_holes(cell, holes):
    x, y = (cell[0] + 0.5) * G, (cell[1] + 0.5) * G
    return any(h[0] <= x <= h[2] and h[1] <= y <= h[3] for h in holes)


FLOOR_HOLES = C.get("floor_holes", [])      # [x0, y0, x1, y1]: no floor here (stairwells)
CEIL_HOLES = C.get("ceiling_holes", [])     # no ceiling here (where the stairs go up)
fp = {c for c in fp if not in_box_cell(c) and not in_holes(c, FLOOR_HOLES)}
# drop specks of footprint (e.g. floor seen through a window)
seen, comps = set(), []
for c in fp:
    if c in seen:
        continue
    q, comp = deque([c]), []
    seen.add(c)
    while q:
        a = q.popleft(); comp.append(a)
        for d in ((1, 0), (-1, 0), (0, 1), (0, -1)):
            b = (a[0] + d[0], a[1] + d[1])
            if b in fp and b not in seen:
                seen.add(b); q.append(b)
    comps.append(comp)
fp = {c for comp in comps if len(comp) * G * G >= 0.5 for c in comp}
# fill gaps that are completely surrounded by floor (under tables, sofas, rugs the scanner missed)
if fp:
    i0 = min(c[0] for c in fp) - 1; i1 = max(c[0] for c in fp) + 1
    j0 = min(c[1] for c in fp) - 1; j1 = max(c[1] for c in fp) + 1
    outside, q = {(i0, j0)}, deque([(i0, j0)])
    while q:
        a = q.popleft()
        for d in ((1, 0), (-1, 0), (0, 1), (0, -1)):
            b = (a[0] + d[0], a[1] + d[1])
            if i0 <= b[0] <= i1 and j0 <= b[1] <= j1 and b not in fp and b not in outside:
                outside.add(b); q.append(b)
    enclosed = {(i, j) for i in range(i0, i1 + 1) for j in range(j0, j1 + 1)
                if (i, j) not in fp and (i, j) not in outside and not in_box_cell((i, j))
                and not in_holes((i, j), FLOOR_HOLES)}
    fp |= enclosed
    log("filled %.1f m2 of enclosed floor gaps" % (len(enclosed) * G * G))
log("footprint %.1f m2" % (len(fp) * G * G))

# delete anything well outside the footprint (seen through windows / doors)
trim = int(round(C.get("footprint_trim", 0.5) / G))
near = dilate(fp, trim)
out_faces = [f for f in bm.faces
             if (math.floor(f.calc_center_median().x / G), math.floor(f.calc_center_median().y / G)) not in near]
bmesh.ops.delete(bm, geom=out_faces, context="FACES")

# delete small floating islands
bm.faces.ensure_lookup_table()
seen = set()
small = []
for f in bm.faces:
    if f.index in seen:
        continue
    q, comp = deque([f]), []
    seen.add(f.index)
    while q:
        a = q.popleft(); comp.append(a)
        for e in a.edges:
            for b in e.link_faces:
                if b.index not in seen:
                    seen.add(b.index); q.append(b)
    if len(comp) < C.get("min_island_faces", 150):
        small += comp
bmesh.ops.delete(bm, geom=small, context="FACES")
loose = [v for v in bm.verts if not v.link_faces]
bmesh.ops.delete(bm, geom=loose, context="VERTS")
log("removed", len(out_faces), "faces outside the footprint and", len(small), "in small islands")

# fill holes: new faces use the rim vertices, so their colour is interpolated from the rim
before = len(bm.faces)
rim = [e for e in bm.edges if e.is_boundary]
if C.get("fill_hole_sides", 80) > 0:
    bmesh.ops.holes_fill(bm, edges=rim, sides=C.get("fill_hole_sides", 80))
    bmesh.ops.triangulate(bm, faces=[f for f in bm.faces if len(f.verts) > 4])
log("filled holes with", len(bm.faces) - before, "faces")
bm.to_mesh(me)
bm.free()
me.update()


# ---------------------------------------------------------------- rebuilt floor / ceiling
# The clean floor / ceiling reach a little past the walls (under / over them), so there's never
# a crack where a scanned wall stops short of the floor or ceiling.
margin = int(round(C.get("slab_margin", 0.5) / G))
big = {c for c in dilate(fp, margin) if not in_box_cell(c) and not in_holes(c, FLOOR_HOLES)}


def cell_colours(samples, default, cells):
    """Average colour per cell; cells without data are interpolated from their neighbours."""
    colc = {}
    for c in cells:
        s = samples.get(c)
        if s and s[3]:
            colc[c] = (s[0] / s[3], s[1] / s[3], s[2] / s[3])
    if not colc:
        return {c: default for c in cells}
    missing = [c for c in cells if c not in colc]
    while missing:
        still = []
        for c in missing:
            ns = [colc[(c[0] + di, c[1] + dj)] for di in (-1, 0, 1) for dj in (-1, 0, 1)
                  if (c[0] + di, c[1] + dj) in colc]
            if ns:
                colc[c] = tuple(sum(n[k] for n in ns) / len(ns) for k in range(3))
            else:
                still.append(c)
        if len(still) == len(missing):
            for c in still:
                colc[c] = default
            break
        missing = still
    # smooth so the floor reads as a clean surface, not a photo
    for _ in range(C.get("colour_smooth", 10)):
        colc = {c: tuple(sum(colc.get((c[0] + di, c[1] + dj), colc[c])[k]
                             for di in (-1, 0, 1) for dj in (-1, 0, 1)) / 9 for k in range(3))
                for c in colc}
    return colc


def grid_mesh(name, z, colc, flip, cells):
    bm2 = bmesh.new()
    lay = bm2.verts.layers.float_color.new("Col")
    verts = {}

    def vert(i, j):
        if (i, j) not in verts:
            v = bm2.verts.new((i * G, j * G, z))
            cs = [colc[c] for c in ((i, j), (i - 1, j), (i, j - 1), (i - 1, j - 1)) if c in colc]
            v[lay] = (*[sum(c[k] for c in cs) / len(cs) for k in range(3)], 1.0)
            verts[(i, j)] = v
        return verts[(i, j)]

    for (i, j) in cells:
        q = [vert(i, j), vert(i + 1, j), vert(i + 1, j + 1), vert(i, j + 1)]
        bm2.faces.new(q[::-1] if flip else q)
    m = bpy.data.meshes.new(name)
    bm2.to_mesh(m)
    bm2.free()
    o = bpy.data.objects.new(name, m)
    bpy.context.scene.collection.objects.link(o)
    return o


extra = []
def avg(cells):
    vals = [v for v in cells.values() if v[3]]
    if not vals:
        return (0.8, 0.8, 0.8)
    n = sum(v[3] for v in vals)
    return tuple(sum(v[k] for v in vals) / n for k in range(3))


if C.get("rebuild_floor", True):
    extra.append(grid_mesh(NAME + "_Floor", 0.0, cell_colours(floor_cells, avg(floor_cells), big), False, big))
if C.get("rebuild_ceiling", True):
    cbig = {c for c in big if not in_holes(c, CEIL_HOLES)}
    if C.get("ceiling_colour"):
        cc = tuple(C["ceiling_colour"][:3])
        extra.append(grid_mesh(NAME + "_Ceiling", CEIL, {c: cc for c in cbig}, True, cbig))
    else:
        cc = avg(ceil_cells) if ceil_cells else (0.85, 0.85, 0.83)
        extra.append(grid_mesh(NAME + "_Ceiling", CEIL, cell_colours(ceil_cells, cc, cbig), True, cbig))

# ---------------------------------------------------------------- backdrop shell
# One clean wall all the way round the outside of the whole space (beyond the slab margin, so it
# sits behind the real walls). Windows and holes in the scan then show this instead of the void.
# Not built next to removed areas (e.g. the other room), which have their own walls.
if C.get("backdrop", True):
    bc = tuple(C.get("backdrop_colour", [0.78, 0.86, 0.95])[:3])
    bw = bmesh.new()
    lay = bw.verts.layers.float_color.new("Col")
    for (i, j) in big:
        for (di, dj) in ((1, 0), (-1, 0), (0, 1), (0, -1)):
            nb = (i + di, j + dj)
            if nb in big or in_box_cell(nb) or in_holes(nb, FLOOR_HOLES):
                continue
            if di:
                x = (i + (1 if di > 0 else 0)) * G
                a, b = (x, j * G), (x, (j + 1) * G)
            else:
                y = (j + (1 if dj > 0 else 0)) * G
                a, b = (i * G, y), ((i + 1) * G, y)
            vs = [bw.verts.new((a[0], a[1], 0)), bw.verts.new((b[0], b[1], 0)),
                  bw.verts.new((b[0], b[1], CEIL)), bw.verts.new((a[0], a[1], CEIL))]
            for v in vs:
                v[lay] = (*bc, 1.0)
            f = bw.faces.new(vs)
            f.normal_update()
            if f.normal.dot(Vector((-di, -dj, 0))) < 0:      # face into the room
                f.normal_flip()
    bmesh.ops.remove_doubles(bw, verts=bw.verts, dist=0.001)
    mw = bpy.data.meshes.new(NAME + "_Backdrop")
    bw.to_mesh(mw)
    bw.free()
    ow = bpy.data.objects.new(NAME + "_Backdrop", mw)
    bpy.context.scene.collection.objects.link(ow)
    extra.append(ow)
    log("backdrop shell:", len(mw.polygons), "faces")

# ---------------------------------------------------------------- light markers
markers = []
spacing = C.get("light_spacing", 2.6)
if spacing > 0:
    cells = sorted(fp)
    # keep cells with lots of footprint around them (room middles, not narrow edges)
    def openness(c):
        r = int(0.5 / G)
        return sum((c[0] + di, c[1] + dj) in fp for di in range(-r, r + 1) for dj in range(-r, r + 1))
    cand = sorted(cells, key=lambda c: -openness(c))
    for c in cand:
        p = Vector(((c[0] + 0.5) * G, (c[1] + 0.5) * G))
        if all((p - m).length >= spacing for m in markers):
            markers.append(p)
    for k, p in enumerate(markers):
        e = bpy.data.objects.new(f"{NAME}_Light_{k + 1}", None)
        e.location = (p.x, p.y, CEIL - 0.1)
        bpy.context.scene.collection.objects.link(e)
    log("light markers:", len(markers))

# ---------------------------------------------------------------- stair ramps (invisible collision)
# A character controller can't climb 18 cm steps, so each flight gets a hidden ramp laid over
# the step nosings: {"from": [x, y, z], "to": [x, y, z], "width": w}
ramps = []
for k, r in enumerate(C.get("ramps", [])):
    a, b = Vector(r["from"]), Vector(r["to"])
    d = b - a
    flat = Vector((d.x, d.y, 0)).normalized()
    side = Vector((-flat.y, flat.x, 0)) * (r.get("width", 0.9) / 2)
    th = Vector((0, 0, -0.08))
    co = [a - side, a + side, b + side, b - side]
    co += [c + th for c in co]
    rm = bpy.data.meshes.new(f"{NAME}_Ramp_{k + 1}")
    rm.from_pydata([tuple(c) for c in co], [], [(0, 1, 2, 3), (7, 6, 5, 4), (0, 4, 5, 1),
                                              (1, 5, 6, 2), (2, 6, 7, 3), (3, 7, 4, 0)])
    ro = bpy.data.objects.new(f"{NAME}_Ramp_{k + 1}", rm)
    bpy.context.scene.collection.objects.link(ro)
    ramps.append(ro)
log("ramps:", len(ramps))

# ---------------------------------------------------------------- materials (vertex colour only)
mat = bpy.data.materials.new(NAME + "_VertexColour")
nt = mat.node_tree
bsdf = nt.nodes.get("Principled BSDF")
attr = nt.nodes.new("ShaderNodeVertexColor")
attr.layer_name = "Col"
nt.links.new(attr.outputs["Color"], bsdf.inputs["Base Color"])
bsdf.inputs["Roughness"].default_value = 0.85
for o in [scan] + extra:
    o.data.materials.clear()
    o.data.materials.append(mat)
    if o.data.color_attributes.get("Col"):
        o.data.color_attributes.active_color = o.data.color_attributes["Col"]
        o.data.color_attributes.render_color_index = o.data.color_attributes.active_color_index
    o.data.shade_flat() if o is not scan else None
if C.get("collision", "godot") == "godot":
    for o in [scan] + extra:
        o.name = o.name + "-col"
    for o in ramps:
        o.name = o.name + "-colonly"          # solid but invisible

# move the whole storey to its height (e.g. the floor below: negative)
if LIFT:
    for o in bpy.context.scene.objects:
        if o.parent is None:
            o.location.z += LIFT
    log("lifted by", LIFT)

# ---------------------------------------------------------------- export
os.makedirs(os.path.dirname(C["out"]), exist_ok=True)
bpy.ops.object.select_all(action="SELECT")
bpy.ops.export_scene.gltf(filepath=C["out"], export_format="GLB", use_selection=True,
                          export_apply=True, export_vertex_color="ACTIVE",
                          export_all_vertex_colors=False)
info = {"out": C["out"], "faces": len(scan.data.polygons), "footprint_m2": round(len(fp) * G * G, 1),
        "lights": [[round(p.x, 2), round(p.y, 2), round(CEIL - 0.1 + LIFT, 2)] for p in markers],
        "bounds_x": [round(min(c[0] for c in fp) * G, 2), round((max(c[0] for c in fp) + 1) * G, 2)],
        "bounds_y": [round(min(c[1] for c in fp) * G, 2), round((max(c[1] for c in fp) + 1) * G, 2)]}
with open(os.path.splitext(argv[0])[0] + "_info.json", "w") as fh:
    json.dump(info, fh, indent=2)
log("DONE", json.dumps(info))
