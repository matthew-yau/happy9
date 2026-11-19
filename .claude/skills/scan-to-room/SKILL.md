---
name: scan-to-room
description: Turn a 3D room scan (Scaniverse / Polycam / LiDAR .fbx, .obj, .glb, .ply, .usdz) into a clean, walkable area in the RoomGame Godot game - straighten it, strip the photo textures, recolour and fill holes, rebuild floor/ceiling, add collision and lights, line it up with the rooms already in the game and connect them through a doorway. Use this whenever the user drops in a new scan, says "add this room/scan/mesh to the game", "convert this room mesh", "connect it to my room", "make the hallway/kitchen/living room playable", or wants an existing scan re-processed, even if they don't say "skill" or "pipeline".
---

# Scan → game room

Everything runs headless in Blender (`C:\Program Files\Blender Foundation\Blender 5.3\blender.exe -b --factory-startup --python <script> -- <args>`) and is checked in Godot (`C:\Users\thema\Downloads\Godot_v4.7.2-stable_win64.exe\Godot_v4.7.2-stable_win64_console.exe`). The project lives in `C:\Users\thema\Downloads\newgame` (read `HANDOFF.md` there first: coordinates, names the game looks for, quirks).

Coordinates: Blender metres, Z up. The bedroom (`build_room.py` → `RoomGame/room.glb`) is X 0..3.12 (wardrobe → window wall), Y 0..3.56 (bed → desk wall), alcove X −0.60..0, door in the desk wall at X −0.53..0.29. Godot = (x, z, −y). Every new area is exported **in these same coordinates**, so the game just loads it at the origin.

## Steps

### 0. Check what already exists
Other sessions keep developing the game. Before writing any `RoomGame/*.glb`, read the end of `HANDOFF.md` and the top of `main.gd` and check whether that file is now made by another script (e.g. `flat.glb` is **modelled by `build_flat.py`** since session 6, not by this pipeline). Never overwrite such a file with a scan export — give the new area its own file (`ground.glb`) and fit it to the modelled one. If you overwrite one by mistake, re-run its build script.

### 1. Bring the scan in
Copy the scan into the project (`newgame/<name>_scan.fbx`). Scaniverse file names contain a narrow no-break space before "am/pm", so typed paths fail: copy it with a glob (`cp Scaniverse*13640* newgame/room2_scan.fbx`).

### 2. Measure and straighten — `scripts/measure_scan.py`
```
blender ... --python scripts/measure_scan.py -- <scan> <out folder> [--turn 90]
```
Writes `measure.json` (unit scale, wall rotation, offset that puts the floor at Z=0 and a corner at 0,0, room size, ceiling height, every strong wall position) plus `plan.png` (top-down, ceiling cut away, 0.5 m grid, red dot = origin) and `slice.png` (outlines at 0.4/0.9/1.5 m). **Look at plan.png** — the numbers alone can't tell a wall from a wardrobe front, and scans that see through doors/windows make the "outer walls" guess too big. Use `x_wall_peaks` / `y_wall_peaks` with the picture to decide. Keep measure outputs in `newgame/scans/`.

### 3. Line it up with the existing rooms
Find one or two things visible in both scans and compute the placement (a rotation that is a multiple of 90° after straightening, plus an offset):
- **A doorway** is the most precise anchor: the gap in the new scan's wall must land on the existing door (bedroom door X −0.53..0.29, hallway-side face of the desk wall at Y 3.66). Find the gap by histogramming wall faces along the wall line (no faces = opening; an open door leaf shows as a diagonal run of faces).
- **A distinctive object** (the user may tell you, e.g. "the aqua suitcase marks the door") — find it by sampling the scan texture colour per face (aqua/teal: low red, high green and blue) in both scans and compare centres. Objects get moved between scans, so treat it as a cross-check (expect a few cm–10 cm error), not the final answer.
- The side of the wall the scanner peeked through tells you the 180° question: the other room must end up on the far side.
- **A staircase between storeys**: scans taken on one floor usually follow the stairs up or down a bit (the ground scan reached 5.5 m; the upstairs scan reached −1.9 m). Run `scripts/register_scans.py -- <config>` with the shared region of each scan: it tries the four 90° turns, searches x/y/height, refines, and prints the `place` block including the floor-to-floor height (ground floor here: rotation 270, offset (−8.381, 9.21, −2.76)). Confirm with the step positions: the flight's ends must land on the stairwell's ends in the other scan.
Placement is applied after straightening: `final = Translation(place.offset) @ RotZ(place.rotation_deg) @ [straighten]`; `place.offset[2]` is the storey's floor height (applied at export; all other config values use that storey's floor as Z = 0).

### 4. Build the clean area — `scripts/scan_to_glb.py`
Write a config (keep it in `newgame/scans/<name>.json`; the full option list is at the top of the script) and run:
```
blender ... --python scripts/scan_to_glb.py -- scans/<name>.json
```
What it does, and why:
- **Welds texture seams first** — scans are split into thousands of patches along UV seams; without welding, "remove small islands" deletes most of the mesh.
- **No photo textures in the output**: the texture is baked to per-vertex colours, blurred (`colour_smooth`) so it reads as clean painted surfaces, then the image and UVs are deleted. Hole fills, missing floor cells and gaps get colours **interpolated** from their neighbours.
- **Clean-up**: deletes faces inside `remove_boxes` (always box out the existing rooms — the scan sees into them through doors), below the floor / above the ceiling (mirror and window reflections), far outside the floor outline, and tiny floating islands; fills small holes.
- **Rebuilds floor and ceiling** as flat grids (scanned floors are bumpy, ceilings dark and patchy) reaching `slab_margin` past the walls so there are no cracks; ceiling colour can be forced with `ceiling_colour`.
- **Backdrop shell** round the whole outline (pale sky colour), so windows and wall holes never show the black void. It is not built next to `remove_boxes`, so doorways into existing rooms stay open.
- Names get `-col` so Godot makes everything solid; `<name>_Light_N` empties mark ceiling-light spots.
- **Storeys**: `floor_holes` (stairwell seen from above: no floor/backdrop there), `ceiling_holes` (where stairs go up), `keep_boxes` (scan faces never trimmed by the height/floor/ceiling rules), `ramps` (hidden walkable slope over a flight: Godot's character can't climb 18 cm steps). If the stairs already exist as a model (build_flat.py), put the scanned flight in `remove_boxes` instead and extend the model.
Prints a summary and writes `scans/<name>_info.json` (footprint, bounds, light spots).

### 5. Check it before touching the game — `scripts/preview_glb.py`
```
blender ... --python scripts/preview_glb.py -- <out folder> RoomGame/room.glb RoomGame/<name>.glb --eye x,y,1.1,yaw ...
```
`top.png` shows both rooms together on a 1 m grid — confirm the doorway lines up. `--eye` renders first-person views (yaw 0 = looking +Y, 90 = −X, −90 = +X, 180 = −Y). Workbench lighting makes ceilings look dark; that's the preview, not the model.

### 6. Hook it into the game
- `main.gd` loads `res://flat.glb` (`FLAT_PATH`, modelled) and `res://ground.glb` (`GROUND_PATH`, scan), gives its meshes vertex-colour, double-sided materials (`_prepare_flat` — Godot's importer doesn't use glTF vertex colours as albedo on its own, and scanned walls seen from behind would vanish), and puts an OmniLight at each `*_Light_*` marker that follows the top light. For a second new area, load it the same way (or generalise to a list).
- To join rooms, the existing room's wall needs a real opening. For the bedroom that is done in `build_room.py` (doorway cut out of `Wall_Desk`, threshold in `Floor`, door leaf as its own `Door_Leaf` object with its origin on the hinge and `Door_Clothes` parented to it). Re-run it headless to update `room.glb` — **back up `room.glb` and `bear_texture.png` first**. `main.gd` swings `Door_Leaf` with E (`toggle_door`, synced with `_net_door`, sent to players who join).
- Import in Godot: `godot_console --headless --path RoomGame --import`, then boot-test: `--headless --path RoomGame --quit-after 900` and grep for errors.

### 7. Verify in the real game
Run a small SceneTree script that instantiates `main.tscn`, calls `_start_solo()`, places the player (Godot position = (x, 0.05, −y)) and saves `get_root().get_texture().get_image()` screenshots — look at them. Then a walk test: `Input.action_press("move_forward")` for a few seconds through the doorway and print the end position; check E works with `main._thing_in_view("Door_")`. Report what you saw, including what still looks rough.

## Tuning notes
- Too much deleted → raise `min_island_faces` threshold carefully; check the weld ran.
- Furniture sliced by walls → it isn't the backdrop (it sits outside the slab margin); look for a `remove_boxes` edge.
- Black gaps at wall bottoms → increase `slab_margin`.
- Washed-out / too bright → flat light energy in `main.gd` `_apply` (`m["ceiling"] * 0.5`).
- Scan very big/slow → lower `decimate` (0.3 of ~350k faces ≈ 70k faces is fine for Godot collision).

## Clean modelled version (what the user usually wants in the end)
The scan pipeline gives a playable but "raw" area. The project's standard is a **modelled** level (build_room.py, build_flat.py, build_ground.py): clean boxes, rounded furniture, shared materials. When the user asks for it cleaner / "like the other floors":
1. `scripts/plan_render.py -- <scan config> <out folder> [tile_m]` - labelled top-down tiles (photo cut at 2 m, and wall/low-furniture bands) in game coordinates. Use 4 m tiles to read furniture.
2. `scripts/extract_layout.py -- <scan config> <layout.json> [picture.png]` - straight wall runs with door/window gaps, floor-finish clusters and furniture footprints (+ heights). Box out the area outside the building with `remove_boxes`, or noise becomes walls. Trust the walls; read furniture and floor finishes off the photo tiles (its blobs merge neighbours).
3. Write `build_<area>.py` like build_ground.py: exec build_flat.py's helpers (so materials and style match), lay out walls/floors/ceiling (holes for stairs), doors (`hinged_door` + main.gd `DOOR_SWING`; sign = the Blender CCW angle the leaf turns into the room), windows + frames, lights + `<Name>_Light_N` markers, furniture (`lounge()` sofas facing any way via a turn, tables, chairs named `Chair_*`), then shift to the storey's height and export.
4. Where a modelled floor sits above another, stack walls (an outside wall downstairs under the one upstairs), or upstairs details (balcony decks) poke through.
5. Verify with in-game screenshots of every room + a stairs walk test, as above.
