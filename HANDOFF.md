# Room Game – handoff notes

A first-person game of my real bedroom, built in Blender (Python script) and played in Godot 4.7.
Start Claude Code in this folder (`C:\Users\thema\Downloads\newgame`) and read this file first.

## Files

| Path | What it is |
|---|---|
| `build_room.py` | Blender script that builds the whole room and exports `RoomGame/room.glb`. Run in Blender: Scripting tab → paste/open → Run Script. Blender keeps its own copy of pasted text, so after edits use **Text → Reload** (or re-paste). |
| `room_scan.fbx` | Scaniverse LiDAR scan of the room (only used if `USE_SCAN = True`). |
| `toy_scan.fbx` | Scaniverse scan of Bob the teddy bear. |
| `RoomGame/` | Godot 4.7 project: `project.godot`, `main.tscn`, `main.gd`, `player.gd`, `laptop.gd`, `room.glb`, `bear_texture.png`. |

## How the room is built (`build_room.py`)

- `USE_SCAN = False` (default): fully modelled room, clean shapes + natural colours sampled from the scan. No photo textures. 1:1 with the real room.
- Coordinates (Blender, metres): X 0 = wardrobe wall → X 3.12 = window wall; Y 0 = bed wall → Y 3.56 = desk wall; ceiling 2.40. Door alcove X −0.60..0, Y 2.36..3.56.
  Godot = (x, z, −y) of Blender.
- Measured from the scan (rotation −38.84°, offset 1.37, 2.09): walls, bed, dresser (0.76 w × 0.45 d × 1.0 h), cube shelf, desks (PC desk 0.8 deep, small desk 0.6), AC, wardrobe doors Y 0.67..2.19, entry door on the **desk wall** at X −0.53..0.29 (hinged in the alcove corner).
- Window, posters taken from photos (scan can't see them).
- Props: PC + monitor + keyboard on PC desk; LED desk lamp on the PC tower, 30 cm arm facing right (+X); laptop open in middle of the small desk; plastic drawer organiser with red basket at the door end of the small desk; coats + tote + black bag on door hooks; bin under PC desk; round ceiling light; posters; cube shelf lamp.
- Collision: objects get Godot suffixes `-col` (visible + solid). Removes Blender's default cube.
- Bob (teddy bear): imported from `toy_scan.fbx`, seams welded, carpet cut off (z > ground + 0.025, r < 0.20), largest piece kept, bottom hole filled with tan fur, gold paw pads, cream pom-pom tail, smoothed (vertex group excludes pads/tail), decimated 0.3, texture shrunk to 2048 and saved as `RoomGame/bear_texture.png`. Sits on the bed at (2.20, 0.55). Object name `Bob`.
- Glowing materials toggled by the game: `Desk_Lamp_LED`, `Ceiling_Light_Diffuser`, `Lamp_Shade`.

## Godot game (`RoomGame/`)

- `player.gd`: first-person controller. WASD, mouse look, Space jump, Shift run, Ctrl/C crouch, R respawn, Esc frees mouse. `sit_at()` / `stand_at()` for chairs and bed; `input_locked` while laptop is open.
- `main.gd`: loads `room.glb`; lighting moods **1** top light, **2** desk lamp, **3** off (dim moonlight), **4** chill (warm shelf lamp + purple PC glow), with fades.
  **E** (priority order): drop Bob → pick up Bob → toggle desk lamp (when looking at it) → stand up / get out of bed → sit in chair (`Chair_*`) → lie in bed (`Bed`).
  Bob is wrapped in a RigidBody3D at runtime; while held: right-drag or mouse wheel turns him; on drop he's woken (`sleeping = false`) + nudged so he never hangs in mid-air. His texture is re-applied from `bear_texture.png` because Godot couldn't decode the JPEG Blender embeds in the .glb (`room.glb.import` also set to `embedded_image_handling=3`).
  **L** opens the laptop when sitting or lying in bed.
- `laptop.gd`: Chrome-style laptop screen (tab, back/forward/reload, address bar; text = Google search). Uses **gdCEF** if installed (class `GDCef`, `create_browser(url, TextureRect, settings)`, mouse/keys forwarded, `load_url`, `previous_page`, `next_page`, `reload`, `resize`). Otherwise shows an "Open in Chrome" button. Esc closes; L closes unless typing.

## In-game browser (gdCEF) - installed
- gdCEF 0.21.0 Windows files are in `RoomGame/cef_artifacts/` (zip + extracted copy in `Downloads/gdcef_download/`).
- Real class names: **`GdCEF`** (node) and `GdBrowserView`. `on_page_loaded` sends 2 args in 0.21.
- Verified from the CLI: Chromium starts, loads google.com and draws into the TextureRect. Still to check by hand: clicking / typing / scrolling on the laptop. Black page -> `"use_gpu": false`.
- **Restart the Godot editor** once so it registers the extension.

## Avatar, hugs and multiplayer (done)
| File | What it does |
|---|---|
| `avatar.gd` | Original round characters: **Sprout** (bean with a leaf sprout) and **Puff** (woolly fluff-ball), colour picked in the lobby. Two-bone IK arms and legs; walk waddle / crouch / sit / lie; blinking; actions HOLD, HUG_BOB, HUG, KISS. First person hides your head (render layer 2). |
| `blanket.gd` | Duvet mesh that drapes over the body when someone lies in bed (head on the pillow at Blender X 2.80). |
| `lobby.gd` | Start menu: name, shirt, skin, Play alone / Host / Join IP. Saved in `user://profile.cfg`. |
| `net.gd` | ENet on port 7777; each player sends their state 30x/s (relayed by the host); hug / kiss requests; hearts. |
| `remote_player.gd` | Other players: smoothed avatar, name tag, capsule body on collision layer 2. |
| `hearts.gd` | Floating heart particles (texture generated in code). |
- Keys: hold **H** = hug Bob; looking at a player: **H** hug, **K** kiss (3.5 s, the two players walk up to each other).
- Bob is host-authoritative: clients ask the host to pick him up; the holder streams his transform; the host runs his physics when he's free. Lights are synced too.
- Tested headless (solo + host/client on localhost): picking up, hugging and dropping Bob, lying in bed with the blanket, connecting, the hug request, a client holding Bob.

## Ideas not done
- Hug / kiss happen without asking the other player first (they're told "busy" only if they're in bed, on the laptop, or already hugging).
- Internet play needs port 7777 forwarded on the host's router, or Tailscale / ZeroTier / Hamachi.

## Known quirks

- Nothing here has been run by the assistant (Blender/Godot not driven from the CLI); the user tests and pastes errors.
- After editing `build_room.py`, re-run it in Blender so `room.glb` updates; Godot re-imports automatically (or Project → Reload Current Project).

## Session 3 additions
- **Third person:** **V** toggles. `player.gd` puts the camera on a SpringArm3D under Head (2.2 m back, over your shoulder). Interaction rays now start at the eyes (`main._eye()`), not the camera.
- **Watch party (laptop):** whoever clicks or types on the laptop drives it. Twice a second they broadcast the URL + video time / paused state (`main._party`). Others press **J** to join: their own gdCEF browser loads the same page, follows the video (it seeks if more than 1.5 s off) and shows on the 3D laptop screen (`LaptopScreen` quad). Sound plays from `LaptopSpeaker`.
  - gdCEF 0.21 `register_method` crashes Godot, so the page reports its video state by briefly setting `document.title` to `@@roomgame@@{json}` (`laptop.gd` JS_REPORT / `_check_title_message`).
  - Chromium here has no H.264 codec: YouTube (VP9) works; H.264-only sites (e.g. Twitch) and DRM sites (e.g. Netflix) don't.
  - A second copy of the game on the same PC uses `user://cef_cache_second` (the port 47391 lock decides).
- Tested: two windows on one PC, the guest's video stayed within ~0.1 s of the host's.
- `RoomGame/characters/` and `RoomGame/characters.gd` are leftovers and unused; safe to delete.

## Session 4: new characters (p2 / p3 models)
- The two characters are now 3D models instead of the built-from-spheres Sprout/Puff: **Snoopy** (`p2`, from `Downloads/p2`) and **Miffy** (`p3`, from `Downloads/p3`). Lobby style ids are `"p2"` / `"p3"`.
- `convert_characters.py` (run with Blender: `blender -b --factory-startup --python convert_characters.py`) turns `p2/source/model.fbx` and `p3/source/player1.stl` into `RoomGame/models/p2.glb` / `p3.glb`: both 1.22 m (4 ft) tall, feet at the origin, facing Godot -Z. Snoopy keeps his rig + `Walk` animation (played while moving); Miffy's STL is decimated to 20 % and split into `white` + `dress` materials - the dress takes the lobby colour.
- Everything was resized for 4 ft characters: eye height 1.05 (crouch 0.7, seated 1.17), player/remote capsules 1.25, name tags, Bob's hold point, blanket bump (`blanket.gd`).
- The procedural arms/legs still run (IK for holding/hugging) but are hidden; the models are statues apart from Snoopy's walk, so hugs/kisses only move the bodies together. First person hides your whole model (layer 2); third person (V) shows it.

## Session 5: idle pose, hugs, sitting, lying
- **p2 idle:** `Walk` frame 0 is mid-stride and `stop()` jumped there. The AnimationPlayer is now advanced manually (`_animate_walk`) and blends back to the skeleton's rest pose (a neutral stand) when you stop.
- **p3 is posable:** `convert_characters.py` (run `blender -b --factory-startup --python convert_characters.py -- p3`) splits the bunny into `Body`, `ArmL/ArmR` (pivot at the shoulders) and `LegL/LegR` (pivot at the hips). Her arms and legs also swing a little when she walks.
- **Hugs / holding Bob:** both models turn their arms toward the hug / Bob targets (`_pose_model_limbs`, `_aim_limb`; p2 uses the `DEF-upper_arm` / `DEF-thigh` bones).
- **Sitting:** bum on the seat (`FIT.bottom`), legs stretched forward, hands on the lap. `player.seated_eye_height` comes from `avatar.seated_eye_height()`.
- **Lying:** head on the pillow, slightly tilted, flattened front-to-back (`avatar._lie()`); the duvet (`blanket.fit()`) is rebuilt to the real tummy height (`lie_top()`, ~0.3 m) instead of the old fixed ~0.58 m bump.
- **Seated / in bed, mouse turns only your head** (`player.gd` `SEATED_LOOK`, ±100°), so your body can't swing out from under the duvet; standing up keeps the direction you were looking.
- **Two in bed:** alone you lie in the middle; with someone else you each slide to a side (`Blanket.SIDE` = 0.24 m from the middle; lower peer id takes the room side). Arms lie along your sides. The duvet drapes over every body in bed (`blanket.fit([[y, top], ...])`).

## Session 5: the rest of the flat (scan-to-room skill)
- New project skill **`.claude/skills/scan-to-room/`** (SKILL.md + `scripts/measure_scan.py`, `scan_to_glb.py`, `preview_glb.py`): measure/straighten any room scan, line it up with the existing rooms, turn it into a clean game area (no photo textures - per-vertex colours, blurred; holes and missing floor interpolated; flat rebuilt floor/ceiling; backdrop shell so windows/holes never show the void; `-col` collision; ceiling-light markers), preview it, hook it into the game.
- `room2_scan.fbx` (Scaniverse 2026-11-18 1:36 pm: hallway, living room, bathroom, balcony) -> **`RoomGame/flat.glb`**. Config: `scans/flat.json` (re-run: `blender -b --factory-startup --python .claude/skills/scan-to-room/scripts/scan_to_glb.py -- scans/flat.json`). Measurements + plan pictures: `scans/measure_room2/`, `scans/measure_bedroom/`.
- Alignment: straighten rot -88.69, offset (6.979, 2.851, -1.022), then rotate 180 and move (12.32, 9.31). Anchored on the doorway (0.83 m gap in the hallway wall = bedroom door X -0.53..0.29, hallway face of the desk wall at Y 3.66); the aqua suitcase seen through the door agreed to ~8 cm.
- `build_room.py`: doorway cut out of `Wall_Desk`, threshold added to `Floor`, the door is now `Door_Entry` (frame) + **`Door_Leaf`** (origin on the hinge, handles both sides) with `Door_Clothes` parented to it. `room.glb` rebuilt.
- `main.gd`: loads `flat.glb` (`_prepare_flat`: vertex-colour, double-sided materials), ceiling lights at `Flat_Light_N` that follow the top light (mood 1), **E on the door** opens/closes it (`toggle_door`, synced; joiners get the state).
- Tested: door opens with E, walked from the bedroom through the doorway into the hallway; screenshots of hall / living room / bedroom-through-door.
- Backups from before this session: `backup_before_flat/` (build_room.py, room.glb, bear_texture.png, main.gd).
- Rough edges: scanned furniture is blobby and pale (scan quality); the far end of the flat (balcony end) has a stair-stepped outline; flat lights only come on in mood 1.

## Session 6: clean modelled flat + Esc menu
- **`build_flat.py`** (new, `blender -b --factory-startup --python build_flat.py`) models the hallway, stair landing + stairs down, toilet, bathroom, living room and balcony as clean shapes (like `build_room.py`), laid out 1:1 from the scan, and exports `RoomGame/flat.glb`. It replaces the scan-based flat (old one: `backup_before_flat/flat_scan_version.glb`; the scan pipeline in `scans/flat.json` still works but would overwrite flat.glb).
  - Furniture rebuilt as game models where the real ones are: TV + white TV unit, toy shelf + guitar, wardrobe with luggage, coffee table, exercise bike, suitcase, leather sofa + grey armchair (both `Chair_*`: E sits, facing +Y), patterned armchair with pink cushion, desk with two monitors + chair, dartboard, shuttered window, cowhide + blue rug, curtains, sliding balcony door (half open), glass shower, bath under a blind, vanity + mirror, toilet, laundry basket, bath mat.
  - Shut doors stand in for the parts of the flat that weren't scanned. Outside: lawn 3 m below, trees, neighbours' houses, sky walls.
  - Lamp shades use the `Ceiling_Light_Diffuser` material (glow with mood 1); `Flat_Light_N` markers place the lights (`main.gd`, energy = top light × 0.35).
  - Layout numbers (walls, doors, stair well) are constants at the top of the layout section, measured from the textured top view of the scan.
- `main.gd` `_prepare_flat` only applies vertex colours to meshes that have them, and collects the flat's glowing materials.
- **Esc menu**: Esc in game opens the start panel as "Paused" (name / character / colour, Resume, Back to start menu). Resume (or Esc again) rebuilds your avatar if you changed it and sends the new profile to everyone (`net.send_profile`); other players swap your model (`remote_player.setup`).
- Tested: walked bedroom -> door -> hall -> living room -> balcony; sat on the sofa and armchair; switched Snoopy -> Miffy from the Esc menu; screenshots of every room.

## Session 7: softer furniture, working doors / stairs / closet, real screens (TV, computers, laptop)

**build_flat.py**
- `Piece` now has:
  - `rbox` (rounded, smooth-shaded box with optional tilt) and `tube` (round bar between two points).
  - A per-piece `bevel=` that rounds every sharp box edge.
  - `rot=` (object turn around Z, in degrees).
- New furniture:
  - Leather sofa and grey armchair (`lounge()`), the wooden armchair, an office chair.
  - Pleated curtains, round balusters and handrails, a shaped toilet and basins, cove cornices.
- **Chairs:** every `Chair_*` object's origin is the seat, and its local +X is the way you face. Sofa seats are `Chair_Sofa_1` / `Chair_Sofa_2`. main.gd `_chair_yaw()` reads the rotation (yaw = rotation − 90°).
- **Doors:** `Door_Toilet`, `Door_Bath`, `Door_Closet_L` / `Door_Closet_R` each have their origin on the hinge. They open with E; main.gd `DOOR_SWING` says how far.
  - The hall closet (mirror doors, rail, clothes, shelf) is in the wall opposite the bedroom door, X −0.40..1.00. The scan had a hole there because mirrors don't scan.
- **Stairs:**
  - They now go down from the living-room end (top, X 5.5) toward the bedroom end (bottom landing X 3.0..3.35).
  - You walk on the invisible `Flat_Stair_Ramp`, which main.gd hides; it is flush with the floor at the top so there's no lip.
  - The shut door downstairs is in the well's west wall.
- **Screens:** materials `Flat_TV_Screen` and `Flat_PC_Screen` are where the TV and living-room computer pictures go. Don't reuse those names on anything else.

**Screens (laptop.gd + main.gd "screens" section)**
- Each screen is a `Device` with its own gdCEF browser (1280×720, off screen), its picture quad, speaker and glow light:
  - `laptop` (bedroom laptop)
  - `pc` (bedroom monitor)
  - `tv` (living room)
  - `pc2` (living-room desk)
- main.gd `_make_devices()` finds each one's screen by material name (`DEVICES` table) and fits a quad over it.
- **Keys:**
  - T: turn the screen on / off. E also does this when standing and looking at it.
  - L: use it (the browser window).
  - P: play / pause.
  - Which screen: the one you look at, else the nearest within 3.4 m. In bed it's always the laptop.
- The TV fills its screen with the video (JS_FILL_ON: the YouTube player box goes position:fixed and everything else is hidden). It goes back to the normal page while you hold the "remote" (window open).
- `user_gesture_required: false` must go in `cef.initialize()`. In the browser settings it's ignored, and videos wouldn't autoplay or follow along.
- **Multiplayer:**
  - Screens are shared like real ones: `_net_power` (reliable) and `_device_party` (every 0.5 s from whoever is using it, carrying url, time and paused).
  - Whoever touched it last drives it; `seq` breaks ties (the newest claim wins, then the lower peer id).
  - There's no "J join" any more: everyone's TV shows the same thing automatically.
  - Door states and screen power go to joiners in `send_world_to`.
- Sofa / armchair: E on any part of them sits you on the nearest seat (`_chair_in_view`). You stand up in front of a lounge chair, and behind an office chair.
- Backups: `backup_before_flat/laptop_before_devices.gd`, `main_before_devices.gd`, `build_flat_v1.py`, `flat_v1.glb`.

## Session 8 - playing over Tailscale
- net.gd local_addresses(): if the PC has a Tailscale address (100.64-100.127.x.x) only that is shown, labelled "(Tailscale)"; join() ignores anything after the first space, so a pasted "100.x.x.x (Tailscale)" works. Lobby join label/placeholder say Tailscale. Backups: backup_before_flat/net_before_tailscale.gd, lobby_before_tailscale.gd.
- No export templates are installed, so the shareable build is the Godot runtime + the project: ~/Downloads/MyRoom_game/ (MyRoom.exe = Godot_v4.7.2 non-console exe, game/ = RoomGame copy incl. .godot import cache and cef_artifacts, "Play My Room.bat" runs `MyRoom.exe --path game`, READ ME FIRST.txt). Zipped as ~/Downloads/MyRoom_game.zip (311 MB). Rebuild by re-copying RoomGame into game/ after changes.
- Mac build (M1+ only: gdCEF's macOS libs are arm64): `python scripts/pack_mac.py` writes ~/Downloads/MyRoom_mac.zip (675 MB) straight from Downloads/godot_mac/Godot_mac.zip (Godot 4.7.2 macOS universal) + the gdCEF release zip (cef_artifacts/macos) + RoomGame, keeping Unix exec bits (re-zipping on Windows would lose them). project.godot now has import_etc2_astc=true for Apple Silicon. Untested on a real Mac.
- Session 9: bathroom wall-tile strip (Flat_Walls, 1.2 m) ran across the bathroom doorway and blocked it; now built with wall() + a hole. Shower walk-in gap widened to 2.95..3.58 (was 0.28 m, player capsule is 0.5 m).

## Session 10: the ground floor (downstairs)
- `ground_scan.fbx` (Scaniverse 2026-11-19 12:50 pm) -> **`RoomGame/ground.glb`** with the scan-to-room skill (`scans/ground.json`, measurements in `scans/measure_ground/`). Floor at Blender Z **-2.76**; spans X -8.6..10.9, Y 0.1..9.8 (under the bedroom and flat). 20 ceiling-light markers (`Ground_Light_N`, follow the top light).
- Aligned by the stairs: new `scripts/register_scans.py` matched the part of the ground scan that went up the stairs against the flat scan's stairwell -> turn 270, offset (-8.381, 9.21), floor-to-floor 2.76 m. The step positions agree (flight from X 5.45 at the top to ~1.96 at the bottom, Y ~3.8..4.7).
- **build_flat.py stairs changed to match**: well X 2.05..5.5 (was 3.0..5.5), 15 steps of 0.184 m straight down to the ground floor (was 10 steps to a landing with a shut "downstairs" door - landing and door removed), well walls stop at the ground floor's ceiling (Z -0.12), the stair-side wall starts at the bedroom wall's hallway face beside the bedroom (no overlapping faces), ramp runs 0.3 m out onto the ground floor. Backup: `backup_before_flat/build_flat_before_ground.py`.
- ground.glb drops the scanned stairs (`remove_boxes`) - the modelled flight is used - and has a ceiling opening over the well (`ceiling_holes`).
- main.gd: `GROUND_PATH`, loaded after the flat with `_prepare_flat` + `_make_flat_lights`. Backup: `backup_before_flat/main_before_ground.gd`.
- Tested: boot clean; walked from the top of the stairs down the flight and across the ground floor (ends on the floor at Z -2.76) and back up the stairs; screenshots from the top and bottom of the stairs and the ground-floor hall.
- Note: in this session the scan pipeline briefly overwrote the modelled flat.glb; it was regenerated from build_flat.py (55 objects). The skill now says to check for that first.
- Rough edges: ground floor furniture is scan-blobby; outside the ground floor's windows you see the flat's lawn (Z -3.0) and backdrop shell.
- Session 9 (cont.): bathroom vanity now wall to wall on the east wall (VAN_Y0..VAN_Y1, bath -> south wall), basin at the south end (SINK_Y), 4 doors. Bathroom mirror has its own material Flat_Bath_Mirror (z 0.93..2.05 so 4 ft characters see themselves); main.gd _make_mirrors() puts RoomGame/mirror.gd on it: a planar mirror (SubViewport camera at the eye reflected through the glass, frustum offset to the glass rectangle, renders only when within 7 m and in front). Closet mirror doors still use the plain Flat_Mirror. Backup: backup_before_flat/main_before_mirror.gd.

## Session 11: ground floor rebuilt as a clean model
- **`build_ground.py`** (new) models the whole ground floor 1:1 from the scan and exports **`RoomGame/ground.glb`** (76 objects), replacing the raw scan version. Run: `blender -b --factory-startup --python build_ground.py`.
  - It `exec`s build_flat.py's helper section (materials, Piece, wall/frame/door helpers) plus its `lounge()` and `office_chair()`, so both floors share one look; changes to those helpers apply to both. Built with this floor at Z 0, then moved to GROUND_Z -2.76.
  - Rooms: long hall (front door in its east wall, shoe cabinet, coat hooks, rugs), dining (table + 6 chairs, blue sideboard), kitchen (north counter, 5-burner hob, sink, hood, wall cupboards, island + 4 stools), wet kitchen (U counters + hob), pantry shelves + fridge facing the hall, laundry (washer, dryer, freezer, sink, drying rail), bathroom (grey bath, toilet, vanity, mirror, wall tiles), TV room (two sofas, keyboard + stool, side table, TV unit, coffee table, rug), living room (three sofas, red rug, coffee table, TV unit, ottoman), study (built-in wardrobe, desk, office chair, shelves), west room (pale floor, bed, chest). 6 windows, 12 ceiling lights (`Ground_Light_N`).
  - Doors E opens: `Door_G_Study`, `Door_G_Laundry`, `Door_G_Bath` (added to main.gd DOOR_SWING). Seats: `Chair_G_*` (sofas, dining chairs, stools, desk chair, keyboard stool).
  - TV room's east wall put under the flat's living-room east wall (X 10.55; the scan said 10.85), so the balcony deck doesn't poke through its ceiling.
- Measured with two new skill scripts: `extract_layout.py` (walls with door/window gaps, floor finishes, furniture footprints -> `scans/ground_layout.json`, picture `scans/plan_ground/layout.png`) and `plan_render.py` (labelled photo + wall-band plan tiles -> `scans/plan_ground4/`).
- build_flat.py: the outdoor lawn now sits just under the ground floor (GROUND_Z - 0.04) instead of at -3.0.
- Tested: boot clean; walked down the stairs onto the ground floor; screenshots of every room; all three ground doors registered.
- Not done: the ground floor's screens (TVs) aren't devices (no picture); the front door is shut (nothing outside to go to).
- Session 9 (cont.): interactions no longer reach through floors/walls: main.gd _can_see(point, tol) line-of-sight ray, used by _device_in_view/_device_near; _chair_in_view's nearest-seat fallback uses 3D distance + seat must be on your floor (eye 0.3 below .. 1.5 above) + line of sight. Backup: backup_before_flat/main_before_los.gd.
- Session 9 (cont.): downstairs sitting + screens.
  - build_ground.py turn(): used matrix_world (stale before a scene update), so every turned sofa's seat origins landed in the wrong place (e.g. TV-room seats at 16.9, 17.24) -> now matrix_basis. Backup: backup_before_flat/build_ground_before_seatfix.py / ground_before_seatfix.glb.
  - main.gd sit_down / stand_up kept Y = 0 (teleported you upstairs); now use the seat's own Y. "Stand up in front" applies to any seat whose name contains Sofa / Armchair.
  - Ground screens have their own materials (Ground_TV_Screen living room, Ground_TV2_Screen TV room, Ground_PC_Screen study monitor) and are devices tv_g, tv_g2 (fill video, YouTube) and pc_g (facing -X: _make_devices now handles X-facing screens). TV speaker/glow settings keyed on the fill flag, not id "tv".
  - _can_see also refuses points more than 1.8 m above/below your eye (floors can be one-sided to rays).

## Session 12: ground floor fixed from the user's reference photos
- 9 photos (Downloads, 2026-11-19 13:40: TV room, entry, hall/stairs, living, sunroom, dining, kitchen, scullery, pantry). build_ground.py rewritten to match (backups: `backup_before_flat/build_ground_before_photos.py`, `build_flat_before_photos.py`, `main_before_photos.gd`):
  - the "west room" is a **glassed-in sunroom**: deck floor, glass south + west walls with white frames, grey bulkhead, wicker table + 6 wicker chairs (`Chair_G_Patio_N`), hanging-plant pole; sliding glass doors into the dining room and the living room (grey curtains on the living side).
  - **dining**: dark timber table with clear cover, mismatched chairs, glass-box pendant, big shuttered west window, aquarium (blue glow), stainless fridge, tall white cupboard, lucky bamboo, pet bowls (the scan's "blue sideboard" was the aquarium light).
  - **kitchen**: galley with a long strip window over the bench, 5-burner hob + oven + stainless chimney hood, wall cupboards; island with the double sink; double-door fridge in a recess at the end facing the kitchen, next to the scullery doorway (navy noren curtain).
  - **scullery**: L of counters, 4-burner hob under its window with a glass canopy hood, round sink + coffee machine, subway tiles; the **walk-in pantry** (L shelves) opens off it, not the hall.
  - **living**: grey L sectional + third sofa, dark timber coffee table and TV unit, TV in front of a shuttered window.
  - **TV room**: three tall shuttered windows (east), black panelled feature wall with an 85" TV over a dark open-shelf unit, charcoal 3-seat sofa + armchair, white C-shaped side table (no rug / coffee table).
  - **entry**: dark timber 4-panel front door + shuttered sidelight, console table with plush toys, coat rail, slatted bench, black shoe cabinet, dark timber garage door with glass in the hall's south wall (the garage itself isn't modelled), white open shelves.
  - honey timber floors, pale grey walls, recessed downlights + AC vents.
- **build_flat.py stairs restyled** (as photographed): floating thick timber treads, black steel stringer, 1.1 m wide flight against the south wall (FLIGHT_Y1 = 4.85; the rest of the well is an open void), glass balustrades with timber handrails down the flight and round the well upstairs.
- TVs / seats downstairs: devices `tv_g` (living, material Ground_TV_Screen), `tv_g2` (TV room, Ground_TV2_Screen), `pc_g` (study, Ground_PC_Screen) are in main.gd DEVICES (added by another session) and are found + switch on. 27 `Chair_G_*` seats (every sofa cushion, armchair, dining/patio chairs, stools, desk + keyboard stools); sitting tested on the TV-room sofa and the living sectional.
- Tested: boot clean; screenshots from each photo's viewpoint; stairs walk test.

## Session 13: choppy screen sound, blocked doorways downstairs
- **Choppy sound (all screens: laptop, PCs, TVs)**: gdCEF delivers Chromium's audio at **44.1 kHz** but laptop.gd's AudioStreamGenerator played it at 48 kHz, so the buffer ran dry ~30x a second (measured with get_skips()/get_frames_available(); pausing the speaker showed sound arriving ~4100 frames/s slower than it was played). laptop.gd `_hook_audio`: mix_rate = AUDIO_RATE (44100), buffer 0.5 s; new `_pump_audio()` (called per device in `_process`) is a small jitter buffer: starts a speaker once 0.08 s is queued, pauses it to refill if it runs dry, clears the backlog if > 0.35 s (stays in sync with the picture). Measured after: 0 underruns over 40 s, ~0.1 s queued, no drift. Note: a paused AudioStreamPlayer reports playing = false.
- **TV room couldn't be entered**: the black feature-wall panel ran across the doorway, and the keyboard + stool sat just inside it. Panel now starts after the doorway (FEAT_X0); keyboard moved along the west wall to Y 7.25..8.15, stool to (7.0, 7.7).
- Pantry: the step stool blocked its doorway; moved to the corner.
- Walk-tested doorways: hall -> TV room, kitchen -> scullery, scullery -> pantry, living -> sunroom, dining -> sunroom (all OK). Boot clean.
