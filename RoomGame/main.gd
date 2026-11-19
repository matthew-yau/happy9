extends Node3D
## Loads the room exported from Blender (room.glb in this folder) and runs the game:
## lighting, Bob the teddy bear, chairs and bed, the laptop, your avatar and multiplayer.
## Objects named "-col" in Blender become visible + solid, "-colonly" become invisible walls.
##
## Lighting:  1 = top light (default)   2 = just the desk lamp   3 = dark (not pitch black)
##            4 = chill ambience        E  = look at the desk lamp and press E to switch it on/off
## Bob:       E pick up / drop, hold H to hug him
## Players:   look at someone close and press H to hug, K to kiss
## Door:      look at the bedroom door and press E to open / close it (leads into flat.glb)

const ROOM_PATH := "res://room.glb"
# The rest of the flat (hallway, stairs, toilet, bathroom, living room, balcony), modelled by
# build_flat.py from the room scan (laid out with the scan-to-room skill's measurements).
# Same coordinates as room.glb; its "Flat_Light_N" empties mark where its ceiling lights go.
const FLAT_PATH := "res://flat.glb"
# The ground floor, downstairs (floor at Blender Z -2.76): modelled by build_ground.py from
# ground_scan.fbx (laid out with the scan-to-room skill). The flat's stairs run down into it.
const GROUND_PATH := "res://ground.glb"
const DOOR_OPEN_DEG := -88.0      # the door swings into the bedroom (Blender -Y)
const DOOR_SPEED := 2.2           # door open/close speed (1 / seconds)
const Blanket := preload("res://blanket.gd")
const Avatar := preload("res://avatar.gd")
const Hearts := preload("res://hearts.gd")
const FADE := 0.6  # seconds to fade between lighting moods

# Blender (X, Y, Z-up) -> Godot (X, Y-up, Z) : (x, y, z) -> (x, z, -y)
static func b2g(x: float, y: float, z: float) -> Vector3:
	return Vector3(x, z, -y)

# Where things are in the room (Blender coordinates, metres)
var DESK_LAMP_HEAD := b2g(2.07, 3.36, 1.53)
var SHELF_LAMP := b2g(2.92, 1.25, 1.15)
var PC_BACK := b2g(2.45, 3.48, 1.05)

# Glowing materials in room.glb that switch with the lights (by Blender material name)
const GLOW_MATERIALS := ["Desk_Lamp_LED", "Ceiling_Light_Diffuser", "Lamp_Shade"]

# Each mood: light energies, ambient light, and how much each glowing material glows (0..1)
const MODES := {
	1: {"name": "Top light", "ceiling": 1.2, "window": 0.6, "window_col": Color(0.85, 0.92, 1.0),
		"desk": 0.0, "shelf": 0.0, "accent": 0.0,
		"ambient": 0.7, "ambient_col": Color(1.0, 0.98, 0.95), "bg": Color(0.08, 0.08, 0.1),
		"glow": {"Ceiling_Light_Diffuser": 1.0, "Desk_Lamp_LED": 0.0, "Lamp_Shade": 0.0}},
	2: {"name": "Desk lamp", "ceiling": 0.0, "window": 0.08, "window_col": Color(0.6, 0.7, 1.0),
		"desk": 2.2, "shelf": 0.0, "accent": 0.0,
		"ambient": 0.12, "ambient_col": Color(1.0, 0.9, 0.8), "bg": Color(0.03, 0.03, 0.04),
		"glow": {"Ceiling_Light_Diffuser": 0.0, "Desk_Lamp_LED": 1.0, "Lamp_Shade": 0.0}},
	3: {"name": "Lights off", "ceiling": 0.0, "window": 0.25, "window_col": Color(0.5, 0.62, 1.0),
		"desk": 0.0, "shelf": 0.0, "accent": 0.0,
		"ambient": 0.07, "ambient_col": Color(0.55, 0.62, 0.9), "bg": Color(0.01, 0.01, 0.02),
		"glow": {"Ceiling_Light_Diffuser": 0.0, "Desk_Lamp_LED": 0.0, "Lamp_Shade": 0.0}},
	4: {"name": "Chill", "ceiling": 0.0, "window": 0.05, "window_col": Color(0.5, 0.55, 1.0),
		"desk": 0.35, "shelf": 1.0, "accent": 0.9,
		"ambient": 0.18, "ambient_col": Color(1.0, 0.72, 0.8), "bg": Color(0.03, 0.02, 0.04),
		"glow": {"Ceiling_Light_Diffuser": 0.0, "Desk_Lamp_LED": 0.35, "Lamp_Shade": 1.0}},
}

var mode := 1
var desk_on := false
var desk_level := 2.2            # brightness the desk lamp returns to when switched on with E

@onready var env: Environment = $WorldEnvironment.environment
@onready var ceiling_light: OmniLight3D = $CeilingLight
@onready var window_light: OmniLight3D = $WindowLight
@onready var player: CharacterBody3D = $Player
var desk_spot: SpotLight3D
var desk_glow: OmniLight3D
var shelf_light: OmniLight3D
var accent_light: OmniLight3D
var flat_lights: Array[OmniLight3D] = []
var glow_mats := {}              # material name -> [material, full emission energy]
var mode_label: Label
var hint_label: Label
var net_label: Label
var tween: Tween

# Teddy bear you can pick up and drop with E, and hug with H
var bear: RigidBody3D
var bear_mesh: Node3D
var holding_bear := false
var hugging_bear := false
var bob_holder := 0               # peer id of whoever is carrying Bob (0 = nobody)
var bear_spin := Basis.IDENTITY   # how you've turned Bob while holding him
var _bob_target := Transform3D()  # where Bob should be (synced from the network)
var _bob_has_target := false
var _bob_send := 0.0
var _hug_time := 0.0

# You, multiplayer, the start menu, the bed's duvet
var my_avatar: Avatar
var net               # net.gd
var lobby             # lobby.gd
var blanket: MeshInstance3D
var interaction := 0              # Avatar.Action.HUG / KISS while hugging / kissing someone
var interaction_partner := 0
var interaction_until := 0.0
var _toast_until := 0.0

# In-game laptop screen (laptop.gd)
var laptop   # laptop.gd (a CanvasLayer with open()/close() and opened/closed signals)
const BEAR_SIZE := Vector3(0.16, 0.21, 0.16)
const HOLD_DISTANCE := 0.48    # how far in front of your eyes Bob is held (within arm's reach)
const REACH := 2.5             # how far away you can grab him from
const PLAYER_REACH := 1.8      # how close someone has to be to hug / kiss them
const INTERACTION_TIME := 3.5


func _ready() -> void:
	if ResourceLoader.exists(ROOM_PATH):
		var room: Node3D = load(ROOM_PATH).instantiate()
		room.name = "Room"
		add_child(room)
		_hide_blender_cameras(room)
		_collect_glow_materials(room)
		_setup_bear(room)
		if ResourceLoader.exists(FLAT_PATH):
			var flat: Node3D = load(FLAT_PATH).instantiate()
			flat.name = "Flat"
			add_child(flat)
			_hide_blender_cameras(flat)
			_prepare_flat(flat)
			_make_flat_lights(flat)
		if ResourceLoader.exists(GROUND_PATH):
			var ground: Node3D = load(GROUND_PATH).instantiate()
			ground.name = "Ground"
			add_child(ground)
			_hide_blender_cameras(ground)
			_prepare_flat(ground)          # same treatment: per-vertex colours, both sides drawn
			_make_flat_lights(ground)      # its "Ground_Light_N" markers
			# Bamboo plant was placed at counter height (z=0.92) but has no support there
			var plant := ground.find_child("Ground_Plant", true, false) as Node3D
			if plant:
				plant.position.y -= 0.92
		_find_doors()
	else:
		_add_fallback_floor()
		$HUD/Help.text = "room.glb not found!\nExport it from Blender and drop it into this project's folder.\n\n" + $HUD/Help.text

	_make_lights()
	_make_labels()
	laptop = preload("res://laptop.gd").new()
	add_child(laptop)
	laptop.opened.connect(func(): player.input_locked = true)
	laptop.closed.connect(func(): player.input_locked = false)
	_make_devices()
	_make_my_phone()
	laptop.put_away.connect(_on_phone_put_away)
	_make_mirrors()
	_init_quality()
	laptop.page_touched.connect(_on_device_touched)
	set_mode(1, true)

	blanket = Blanket.new()
	blanket.name = "Blanket"
	add_child(blanket)

	net = preload("res://net.gd").new()
	net.name = "Net"
	net.main = self
	add_child(net)
	net.status_changed.connect(func(t): net_label.text = t)

	lobby = preload("res://lobby.gd").new()
	add_child(lobby)
	lobby.play_solo.connect(_start_solo)
	lobby.host_game.connect(_start_host)
	lobby.join_game.connect(_start_join)
	lobby.resume_game.connect(_resume_from_pause)
	lobby.leave_game.connect(_leave_to_menu)
	lobby.show_menu()


# ---------------------------------------------------------------- start menu

func _make_my_avatar() -> void:
	if my_avatar:
		my_avatar.queue_free()
	my_avatar = Avatar.new()
	my_avatar.first_person = true
	my_avatar.style = lobby.style
	my_avatar.color = lobby.color
	my_avatar.name = "Avatar"
	player.add_child(my_avatar)
	player.seated_eye_height = my_avatar.seated_eye_height()   # bum on the seat, not legs through it
	player.stand_eye_height = my_avatar.stand_eye_height()     # camera at this character's eyes
	player.crouch_eye_height = my_avatar.crouch_eye_height()
	# Your own head would block the camera: the camera skips layer 2 (your head)
	var cam: Camera3D = player.find_child("Camera3D", true, false)
	cam.set_cull_mask_value(2, false)


func _enter_room() -> void:
	net.my_name = lobby.player_name
	net.my_style = lobby.style
	net.my_color = lobby.color
	_make_my_avatar()
	lobby.visible = false
	player.in_menu = false
	Input.mouse_mode = Input.MOUSE_MODE_CAPTURED


## Esc in the game: the menu comes up (change name / character / colour); the game keeps
## running for everyone else.
func _pause() -> void:
	player.in_menu = true
	lobby.show_pause()


func _resume_from_pause() -> void:
	lobby.save_profile()
	var changed: bool = lobby.style != net.my_style or not lobby.color.is_equal_approx(net.my_color) 		or lobby.player_name != net.my_name
	net.my_name = lobby.player_name
	net.my_style = lobby.style
	net.my_color = lobby.color
	if changed:
		_make_my_avatar()                    # new model; eye heights follow the character
		if lying_in_bed:
			player.current_eye_height = my_avatar.lie_eye_height()
		elif sitting_in != null:
			player.current_eye_height = player.seated_eye_height
		net.send_profile()
	lobby.visible = false
	var f := get_viewport().gui_get_focus_owner()
	if f:
		f.release_focus()
	player.in_menu = false
	Input.mouse_mode = Input.MOUSE_MODE_CAPTURED


func _leave_to_menu() -> void:
	if laptop.visible:
		laptop.close()
	net.leave()
	on_connection_lost("")


func _start_solo() -> void:
	_enter_room()


func _start_host() -> void:
	var err: String = net.host()
	if err != "":
		lobby.set_status(err)
		return
	_enter_room()


func _start_join(address: String) -> void:
	var err: String = net.join(address)
	if err != "":
		lobby.set_status(err)
		return
	_enter_room()
	if bear:
		bear.freeze = true            # the host runs Bob's physics; we just follow along


func on_joined_host() -> void:
	_toast("Joined! Look at someone and press H to hug, K to kiss")


func on_connection_lost(message: String) -> void:
	end_interaction()
	for d in laptop.devices.values():
		d.driver = 0
	bob_holder = 0
	holding_bear = false
	hugging_bear = false
	if bear:
		bear.freeze = false
		bear.collision_layer = 1
		bear.collision_mask = 1
		bear.sleeping = false
	player.in_menu = true
	lobby.show_menu(message)


# ---------------------------------------------------------------- lights

func _make_lights() -> void:
	desk_spot = SpotLight3D.new()                    # the lamp's beam onto the desk
	desk_spot.position = DESK_LAMP_HEAD
	desk_spot.rotation_degrees = Vector3(-90, 0, 0)  # point straight down
	desk_spot.spot_angle = 55.0
	desk_spot.spot_range = 2.4
	desk_spot.spot_attenuation = 0.8
	desk_spot.light_color = Color(1.0, 0.95, 0.86)
	desk_spot.shadow_enabled = true
	add_child(desk_spot)

	desk_glow = OmniLight3D.new()                    # soft spill around the lamp head
	desk_glow.position = DESK_LAMP_HEAD + Vector3(0, -0.05, 0)
	desk_glow.omni_range = 1.6
	desk_glow.light_color = Color(1.0, 0.93, 0.82)
	add_child(desk_glow)

	shelf_light = OmniLight3D.new()                  # table lamp on the cube shelf
	shelf_light.position = SHELF_LAMP
	shelf_light.omni_range = 3.0
	shelf_light.light_color = Color(1.0, 0.72, 0.42)
	shelf_light.shadow_enabled = true
	add_child(shelf_light)

	accent_light = OmniLight3D.new()                 # purple glow behind the PC for chill mode
	accent_light.position = PC_BACK
	accent_light.omni_range = 2.4
	accent_light.light_color = Color(0.55, 0.3, 1.0)
	add_child(accent_light)

	for l in [desk_spot, desk_glow, shelf_light, accent_light]:
		l.light_energy = 0.0


func _prepare_flat(flat: Node) -> void:
	# flat.glb is modelled (build_flat.py) with ordinary materials. Its lamp shades use the
	# bedroom's "Ceiling_Light_Diffuser" material, so they glow with the top light too.
	# (An older scan-based flat.glb stored its colours per vertex: still handled here.)
	for mi: MeshInstance3D in flat.find_children("*", "MeshInstance3D", true, false):
		for s in mi.mesh.get_surface_count():
			if mi.mesh.surface_get_format(s) & Mesh.ARRAY_FORMAT_COLOR == 0:
				continue
			var src := mi.get_active_material(s)
			var m := StandardMaterial3D.new()
			if src is StandardMaterial3D:
				m = (src as StandardMaterial3D).duplicate()
			m.vertex_color_use_as_albedo = true
			m.albedo_color = Color.WHITE
			m.cull_mode = BaseMaterial3D.CULL_DISABLED
			m.roughness = 0.9
			m.metallic = 0.0
			mi.set_surface_override_material(s, m)
	_collect_glow_materials(flat)
	# The stairs' walking slope is only for collision: you see the steps, not the ramp
	for ramp: Node in flat.find_children("Flat_Stair_Ramp*", "", true, false):
		if ramp is GeometryInstance3D:
			(ramp as GeometryInstance3D).visible = false


func _make_flat_lights(flat: Node) -> void:
	# A warm ceiling light at every "Flat_Light_N" marker; they follow the top light (mood 1)
	for marker: Node in flat.find_children("*_Light_*", "Node3D", true, false):
		var l := OmniLight3D.new()
		l.omni_range = 4.0
		l.omni_attenuation = 1.2
		l.light_color = Color(1.0, 0.95, 0.86)
		l.light_energy = 0.0
		add_child(l)
		l.global_position = (marker as Node3D).global_position
		flat_lights.append(l)


func set_mode(new_mode: int, instant := false) -> void:
	mode = new_mode
	var m: Dictionary = MODES[mode]
	desk_on = m["desk"] > 0.0
	if desk_on:
		desk_level = m["desk"]
	mode_label.text = "Lights: %d  %s" % [mode, m["name"]]
	_apply(instant)


func _apply(instant := false) -> void:
	var m: Dictionary = MODES[mode]
	var desk: float = desk_level if desk_on else 0.0
	var targets := [
		[ceiling_light, "light_energy", m["ceiling"]],
		[window_light, "light_energy", m["window"]],
		[window_light, "light_color", m["window_col"]],
		[desk_spot, "light_energy", desk],
		[desk_glow, "light_energy", desk * 0.15],
		[shelf_light, "light_energy", m["shelf"]],
		[accent_light, "light_energy", m["accent"]],
		[env, "ambient_light_energy", m["ambient"]],
		[env, "ambient_light_color", m["ambient_col"]],
		[env, "background_color", m["bg"]],
	]
	for l in flat_lights:
		targets.append([l, "light_energy", m["ceiling"] * 0.35])
	for mat_name in glow_mats:
		var level: float = m["glow"].get(mat_name, 0.0)
		if mat_name == "Desk_Lamp_LED":
			level = (desk / 2.2) if desk_on else 0.0
		targets.append([glow_mats[mat_name][0], "emission_energy_multiplier", glow_mats[mat_name][1] * level])

	if tween and tween.is_valid():
		tween.kill()
	if instant:
		for t in targets:
			t[0].set(t[1], t[2])
		return
	tween = create_tween().set_parallel(true).set_trans(Tween.TRANS_SINE)
	for t in targets:
		tween.tween_property(t[0], t[1], t[2], FADE)


func toggle_desk_lamp() -> void:
	desk_on = not desk_on
	if desk_on and desk_level <= 0.0:
		desk_level = 2.2
	_apply()
	if net.connected():
		_net_desk.rpc(desk_on, desk_level)


func change_mode(new_mode: int) -> void:
	set_mode(new_mode)
	if net.connected():
		_net_mode.rpc(new_mode)


@rpc("any_peer", "call_remote", "reliable")
func _net_mode(m: int) -> void:
	if MODES.has(m):
		set_mode(m)


@rpc("any_peer", "call_remote", "reliable")
func _net_desk(on: bool, level: float) -> void:
	desk_on = on
	desk_level = level
	_apply()


# ---------------------------------------------------------------- input

func _input(event: InputEvent) -> void:
	# Turning Bob while you hold him: right mouse button + drag, or the mouse wheel.
	# Runs before the player's mouse-look, and swallows the event so the view doesn't move.
	if not holding_bear or laptop.visible or lobby.visible:
		return
	if event is InputEventMouseMotion and Input.is_mouse_button_pressed(MOUSE_BUTTON_RIGHT):
		bear_spin = (Basis(Vector3.UP, event.relative.x * 0.01)
			* Basis(Vector3.RIGHT, event.relative.y * 0.01) * bear_spin).orthonormalized()
		get_viewport().set_input_as_handled()
	elif event is InputEventMouseButton and event.pressed:
		if event.button_index == MOUSE_BUTTON_WHEEL_UP:
			bear_spin = Basis(Vector3.UP, deg_to_rad(15)) * bear_spin
			get_viewport().set_input_as_handled()
		elif event.button_index == MOUSE_BUTTON_WHEEL_DOWN:
			bear_spin = Basis(Vector3.UP, deg_to_rad(-15)) * bear_spin
			get_viewport().set_input_as_handled()


func _unhandled_input(event: InputEvent) -> void:
	if event is InputEventKey and event.pressed and not event.echo 			and event.physical_keycode == KEY_ESCAPE and not laptop.visible:
		if lobby.visible and lobby.paused:
			_resume_from_pause()                  # Esc again closes the menu
			get_viewport().set_input_as_handled()
		elif not lobby.visible:
			_pause()
			get_viewport().set_input_as_handled()
		return
	if laptop.visible or lobby.visible:
		return
	if not (event is InputEventKey) or event.echo:
		return
	if not event.pressed:
		if event.physical_keycode == KEY_H:
			hugging_bear = false              # let go of the hug (still holding him)
		return
	if event.physical_keycode == KEY_V:
		player.toggle_third_person()          # works any time, even mid-hug
		return
	if event.physical_keycode == KEY_G:
		set_quality(not low_quality)
		_toast("Graphics: " + ("Low (faster)" if low_quality else "High"), 2.0)
		return
	if interaction != 0:
		return                                # busy hugging / kissing someone
	if event.physical_keycode == KEY_M:
		take_out_phone()
		return
	match event.physical_keycode:
		KEY_1: change_mode(1)
		KEY_2: change_mode(2)
		KEY_3: change_mode(3)
		KEY_4: change_mode(4)
		KEY_L:
			var phone := _friend_phone_in_view()
			var dev := phone if phone != "" else _device_near()
			if dev != "":
				use_device(dev)
		KEY_H:
			var someone := _player_in_view()
			if holding_bear:
				hugging_bear = true
			elif someone != 0 and not lying_in_bed:
				_start_interaction(Avatar.Action.HUG, someone)
			elif _looking_at_bear():
				pick_up_bear()
				hugging_bear = true
		KEY_T:
			var dev := _device_near()
			if dev != "" and not _device(dev).is_phone:
				set_device_power(dev, not _device(dev).on)
		KEY_P:
			var dev := _device_near()
			if dev != "":
				toggle_device_play(dev)
		KEY_K:
			var someone := _player_in_view()
			if someone != 0 and not lying_in_bed:
				_start_interaction(Avatar.Action.KISS, someone)
		KEY_E:
			if holding_bear:
				drop_bear()
			elif _looking_at_bear():
				pick_up_bear()
			elif _looking_at_desk_lamp():
				toggle_desk_lamp()
			elif sitting_in == null and not lying_in_bed and _door_in_view() >= 0:
				toggle_door(_door_in_view())
			elif sitting_in == null and not lying_in_bed and _device_in_view() != "" 					and not _device(_device_in_view()).is_phone:
				set_device_power(_device_in_view(), not _device(_device_in_view()).on)
			elif sitting_in != null:
				stand_up()
			elif lying_in_bed:
				get_out_of_bed()
			elif _chair_in_view() != null:
				sit_down(_chair_in_view())
			elif _thing_in_view("Bed") != null:
				lie_down()


## Where you look from: your eyes (also in third person, where the camera is behind you)
func _eye() -> Transform3D:
	return ($Player/Head as Node3D).global_transform


func _looking_at_desk_lamp() -> bool:
	var cam := _eye()
	var to_lamp := DESK_LAMP_HEAD - cam.origin
	if to_lamp.length() > 3.0:
		return false
	var forward := -cam.basis.z
	return forward.dot(to_lamp.normalized()) > 0.95


func _player_in_view() -> int:
	# The other player the crosshair is on, if they're close enough to hug
	var hit := _camera_ray(PLAYER_REACH)
	if hit.is_empty():
		return 0
	var c: Object = hit["collider"]
	return c.get_meta("peer_id", 0) if c else 0


## Doors that open with E: the bedroom door (room.glb "Door_Leaf") and the flat's doors
## (flat.glb "Door_*": toilet, bathroom, hall cupboard). Each object's origin is its hinge.
## How far each one swings (degrees around the hinge; + = anticlockwise seen from above):
const DOOR_SWING := {"Door_Leaf": DOOR_OPEN_DEG, "Door_Toilet": -95.0, "Door_Bath": 95.0,
	"Door_Closet_L": -100.0, "Door_Closet_R": 100.0,
	# ground floor (build_ground.py): each swings into its room
	"Door_G_Study": -95.0, "Door_G_Laundry": -95.0, "Door_G_Bath": 95.0}
var doors: Array = []              # [{node, open, t, deg}], sorted by name (same order for everyone)


func _find_doors() -> void:
	var found := {}
	for n: Node in find_children("Door_*", "Node3D", true, false):
		var base := String(n.name).get_slice("-", 0)
		if DOOR_SWING.has(base) and not found.has(base):
			found[base] = n
	var names := found.keys()
	names.sort()
	for k in names:
		var node: Node3D = found[k]
		doors.append({"node": node, "open": false, "t": 0.0, "deg": DOOR_SWING[k],
			"rest": node.rotation.y})


## Index of the door the crosshair is on (or -1)
func _door_in_view() -> int:
	var hit := _camera_ray(REACH)
	if hit.is_empty():
		return -1
	var n: Node = hit["collider"]
	while n != null:
		for i in doors.size():
			if doors[i]["node"] == n:
				return i
		n = n.get_parent()
	return -1


func toggle_door(i: int) -> void:
	doors[i]["open"] = not doors[i]["open"]
	if net.connected():
		_net_door.rpc(i, doors[i]["open"])


@rpc("any_peer", "call_remote", "reliable")
func _net_door(i: int, open: bool) -> void:
	if i >= 0 and i < doors.size():
		doors[i]["open"] = open


func _update_door(delta: float) -> void:
	for d in doors:
		var target := 1.0 if d["open"] else 0.0
		if is_equal_approx(d["t"], target):
			continue
		d["t"] = move_toward(d["t"], target, DOOR_SPEED * delta)
		var e: float = d["t"] * d["t"] * (3.0 - 2.0 * d["t"])     # smoothstep
		(d["node"] as Node3D).rotation.y = d["rest"] + deg_to_rad(d["deg"]) * e


func _process(delta: float) -> void:
	_update_culling(delta)
	_update_door(delta)
	_update_my_avatar()
	_update_interaction()
	blanket.visible = lying_in_bed or net.anyone_lying()
	if lying_in_bed:
		# Slide over to your side of the bed when someone else gets in (or back to the middle)
		var spot := b2g(Blanket.HEAD_X, _bed_side(), Blanket.MATTRESS)
		player.global_position = player.global_position.lerp(spot, 1.0 - exp(-6.0 * delta))
	if blanket.visible:
		# The duvet drapes over everyone in bed: [Blender Y of their middle, tummy height]
		var bodies := []
		if lying_in_bed and my_avatar:
			bodies.append([-player.global_position.z, my_avatar.lie_top()])
		for id in net.lying_ids():
			var rp = net.remotes[id]
			bodies.append([-rp.global_position.z, rp.avatar.lie_top()])
		blanket.fit(bodies)
	_update_devices(delta)
	_update_phones()

	if lobby.visible or laptop.visible:
		hint_label.text = ""
	elif Time.get_ticks_msec() / 1000.0 < _toast_until:
		pass                                  # keep showing the message
	elif interaction == Avatar.Action.HUG:
		hint_label.text = "Hugging %s" % net.name_for(interaction_partner)
	elif interaction == Avatar.Action.KISS:
		hint_label.text = "Kissing %s" % net.name_for(interaction_partner)
	elif holding_bear:
		hint_label.text = "Hold H  hug Bob     E  drop him     Right-drag / wheel  turn him     V  third person"
	elif _player_in_view() != 0 and not lying_in_bed:
		var who: String = net.name_for(_player_in_view())
		hint_label.text = "H  hug %s     K  kiss %s" % [who, who]
		if _friend_phone_in_view() != "":
			hint_label.text += "     L  join %s's phone" % who
	elif _friend_phone_in_view() != "":
		hint_label.text = "L  join %s's phone" % net.name_for(_friend_phone_in_view().to_int())
	elif _looking_at_bear():
		hint_label.text = "E  pick up Bob     H  hug him"
	elif _looking_at_desk_lamp():
		hint_label.text = "E  switch lamp %s" % ("off" if desk_on else "on")
	elif sitting_in != null:
		var dev := _device_near()
		hint_label.text = "E  stand up" + ("     " + _device_hint(dev) if dev != "" else "")
	elif lying_in_bed:
		hint_label.text = "E  get up     " + _device_hint("laptop")
	elif _door_in_view() >= 0:
		hint_label.text = "E  %s the door" % ("close" if doors[_door_in_view()]["open"] else "open")
	elif _device_in_view() != "" and not _device(_device_in_view()).is_phone:
		hint_label.text = _device_hint(_device_in_view()).replace("T  turn", "E  turn")
	elif _chair_in_view() != null:
		hint_label.text = "E  sit"
	elif _thing_in_view("Bed") != null:
		hint_label.text = "E  lie down"
	elif _device(MY_PHONE) and _device(MY_PHONE).on:
		hint_label.text = "M  look at your phone"
	else:
		hint_label.text = ""
	# While you sit / lie and watch, the same hint fades away after a few seconds
	var now := Time.get_ticks_msec() / 1000.0
	if hint_label.text != _last_hint:
		_last_hint = hint_label.text
		_hint_since = now
	var settled := (sitting_in != null or lying_in_bed) and now - _hint_since > 5.0
	hint_label.visible = hint_label.text != "" and not settled
	# Fade the controls hint out after a while
	var help: Label = $HUD/Help
	if not lobby.visible and help.modulate.a > 0.0 and Time.get_ticks_msec() > 12000:
		help.modulate.a = max(0.0, help.modulate.a - delta)


var _last_hint := ""
var _hint_since := 0.0


func _toast(text: String, seconds := 3.0) -> void:
	hint_label.text = text
	_toast_until = Time.get_ticks_msec() / 1000.0 + seconds


# ---------------------------------------------------------------- screens: TV, computers, laptop
# Every screen in the flat is a device (laptop.gd) you can turn on / off (T) and use (L).
# Its picture shows on the real screen in the room and its sound comes from there.
# Devices are shared, like real ones: whoever turns one on or clicks / types on it is
# "using" it, and twice a second their game sends its page address and video position
# (play/pause, time) to everyone, so everyone sees the same thing on that screen -
# sit on the sofa together and watch the TV.

## [id, name, screen material in the .glb, which way the screen faces (Godot), home page, fill video]
const DEVICES := [
	["laptop", "Laptop", "Laptop_Screen_Off", Vector3(0, 0, 1), "https://www.google.com", false],
	["pc", "Computer", "Monitor_Screen", Vector3(0, 0, 1), "https://www.google.com", false],
	["tv", "TV", "Flat_TV_Screen", Vector3(0, 0, 1), "https://www.youtube.com", true],
	["pc2", "Computer", "Flat_PC_Screen", Vector3(0, 0, -1), "https://www.google.com", false],
	# downstairs (ground.glb)
	["tv_g", "TV", "Ground_TV_Screen", Vector3(0, 0, -1), "https://www.youtube.com", true],
	["tv_g2", "TV", "Ground_TV2_Screen", Vector3(0, 0, -1), "https://www.youtube.com", true],
	["pc_g", "Computer", "Ground_PC_Screen", Vector3(-1, 0, 0), "https://www.google.com", false],
]
const DEVICE_REACH := 3.4        # how close you need to be to use / switch a screen
var _dev_timer := 0.0
var _screen_off_mat: StandardMaterial3D


## Finds each device's screen in the room / flat and puts a "picture" quad on it
## Bathroom mirror (material Flat_Bath_Mirror on the east wall, facing -X = into the room)
## + the full-length hall mirror outside the bedroom (Flat_Hall_Mirror on the hall wall, facing
## Blender +Y = Godot -Z)
var mirrors: Array = []


func _make_mirrors() -> void:
	var box := _find_surface_box("Flat_Bath_Mirror", false)
	if box.size != Vector3.ZERO:
		var front := Vector3(box.position.x, box.get_center().y, box.get_center().z)   # the room-side face
		_add_mirror("BathMirror", front, Vector3.LEFT, box.size.z, box.size.y)
	box = _find_surface_box("Flat_Hall_Mirror", false)
	if box.size != Vector3.ZERO:
		var front := Vector3(box.get_center().x, box.get_center().y, box.position.z)
		_add_mirror("HallMirror", front, Vector3.FORWARD, box.size.x, box.size.y)


func _add_mirror(nm: String, front: Vector3, normal: Vector3, w: float, h: float) -> void:
	var m := Node3D.new()
	m.name = nm
	m.set_script(load("res://mirror.gd"))
	add_child(m)
	m.setup(front, normal, w, h)
	mirrors.append(m)


func _make_devices() -> void:
	_screen_off_mat = StandardMaterial3D.new()
	_screen_off_mat.albedo_color = Color(0.03, 0.03, 0.035)
	_screen_off_mat.roughness = 0.12
	_screen_off_mat.metallic_specular = 0.8
	for spec in DEVICES:
		var box := _find_surface_box(spec[2])
		if box.size == Vector3.ZERO:
			push_warning("No screen found for " + str(spec[0]))
			continue
		var facing: Vector3 = spec[3]
		var quad := QuadMesh.new()
		var sideways := absf(facing.x) > 0.5          # a screen facing along X (study monitor)
		quad.size = Vector2(box.size.z if sideways else box.size.x, box.size.y)
		var mat := StandardMaterial3D.new()
		mat.shading_mode = BaseMaterial3D.SHADING_MODE_UNSHADED   # it glows like a real screen
		var screen := MeshInstance3D.new()
		screen.name = "Screen_" + spec[0]
		screen.mesh = quad
		screen.material_override = mat
		screen.cast_shadow = GeometryInstance3D.SHADOW_CASTING_SETTING_OFF
		add_child(screen)
		var depth := box.size.x if sideways else box.size.z
		screen.global_position = box.get_center() + facing * (depth / 2.0 + 0.002)
		if sideways:
			screen.rotation.y = PI / 2 if facing.x > 0.0 else -PI / 2
		elif facing.z < 0.0:
			screen.rotation.y = PI
		screen.visible = false
		var speaker := AudioStreamPlayer3D.new()
		speaker.name = "Speaker_" + spec[0]
		speaker.unit_size = 4.0 if spec[5] else 2.5
		speaker.max_distance = 14.0 if spec[5] else 9.0
		add_child(speaker)
		speaker.global_position = screen.global_position
		var glow := OmniLight3D.new()
		glow.name = "Glow_" + spec[0]
		glow.light_color = Color(0.72, 0.8, 1.0)
		glow.light_energy = 0.9 if spec[5] else 0.3
		glow.omni_range = 3.2 if spec[5] else 1.6
		add_child(glow)
		glow.global_position = screen.global_position + facing * 0.35
		laptop.add_device(spec[0], spec[1], screen, speaker, glow, spec[4], spec[5])


## Bounding box (global) of the mesh surfaces that use `material_name` - the screen panel
func _find_surface_box(material_name: String, override := true) -> AABB:
	var found := false
	var box := AABB()
	for mi: MeshInstance3D in find_children("*", "MeshInstance3D", true, false):
		if mi.mesh == null or mi.name.begins_with("Screen_"):
			continue
		for s in mi.mesh.get_surface_count():
			var mat := mi.get_active_material(s)
			if mat == null or mat.resource_name != material_name:
				continue
			if override:
				mi.set_surface_override_material(s, _screen_off_mat)   # a dark glossy screen when off
			var verts: PackedVector3Array = mi.mesh.surface_get_arrays(s)[Mesh.ARRAY_VERTEX]
			for v in verts:
				var g := mi.global_transform * v
				if not found:
					box = AABB(g, Vector3.ZERO)
					found = true
				else:
					box = box.expand(g)
	return box


func _device(id: String):
	return laptop.devices.get(id)


## The screen your crosshair is on (within reach), or ""
func _device_in_view() -> String:
	var cam := _eye()
	var forward := -cam.basis.z
	var best := ""
	var best_dot := 0.0
	for d in laptop.devices.values():
		if d.is_phone and (d.mine or not d.on):
			continue                           # your own phone is M; others' only while it's out
		var c: Vector3 = d.screen.global_position
		var to := c - cam.origin
		var dist := to.length()
		if dist > DEVICE_REACH + 0.6 or dist < 0.01:
			continue
		var quad: QuadMesh = d.screen.mesh
		var half := maxf(quad.size.x, quad.size.y) * 0.5 + 0.1
		var need := cos(atan2(half, dist))     # inside the screen (plus a little)
		var dot := forward.dot(to / dist)
		if dot > need and dot > best_dot and _can_see(c):
			best = d.id
			best_dot = dot
	return best


## The device L / T / P act on: the one you look at, else the nearest one in reach
## (in bed it's the laptop - you take it to bed)
func _device_near() -> String:
	var seen := _device_in_view()
	if seen != "":
		return seen
	if lying_in_bed and laptop.devices.has("laptop"):
		return "laptop"
	var best := ""
	var best_d := DEVICE_REACH
	for d in laptop.devices.values():
		if d.is_phone:
			continue                           # phones: look at the person holding it
		var dist: float = d.screen.global_position.distance_to(_eye().origin)
		if dist < best_d and _can_see(d.screen.global_position):
			best = d.id
			best_d = dist
	return best


func use_device(id: String) -> void:
	var d = _device(id)
	if d == null:
		return
	if d.is_phone and not d.mine and not d.on:
		return                                # their phone is in their pocket
	if not d.on:
		set_device_power(id, true)
	_claim_device(d)
	laptop.open(id)


func set_device_power(id: String, on: bool) -> void:
	var d = _device(id)
	if d == null:
		return
	if on:
		_claim_device(d)
	laptop.set_power(d, on)
	if d.is_phone:
		_toast("Phone out  -  a friend can look at you and press L to join" if on
			else "Phone away", 2.0)
	else:
		_toast("%s %s" % [d.title, "on" if on else "off"], 1.5)
	if net.connected():
		_net_power.rpc(_net_dev_id(id), on, d.seq)


@rpc("any_peer", "call_remote", "reliable")
func _net_power(net_id: String, on: bool, seq: int) -> void:
	var id := _local_dev_id(net_id)
	var d = _device(id)
	if d == null:
		return
	if on:
		_accept_driver(d, multiplayer.get_remote_sender_id(), seq)
	laptop.set_power(d, on)


## You're using it now: your page / video is what everyone sees on it
func _claim_device(d) -> void:
	if net.online:
		d.seq += 1
		d.driver = net.my_id()


## Take a message from `from` about who's using the device? (the newest claim wins;
## two claims at once: the lower peer id wins, the same on every computer)
func _accept_driver(d, from: int, seq: int) -> bool:
	if seq > d.seq or (seq == d.seq and (from == d.driver or d.driver == 0 or from < d.driver)):
		d.seq = seq
		d.driver = from
		return true
	return false


func _on_device_touched(id: String) -> void:
	var d = _device(id)
	if d and d.driver != net.my_id():
		_claim_device(d)


func toggle_device_play(id: String) -> void:
	var d = _device(id)
	if d == null or not d.on:
		return
	_claim_device(d)
	laptop.toggle_play(d)


func _update_devices(delta: float) -> void:
	_dev_timer += delta
	if _dev_timer < 0.5:
		return
	_dev_timer = 0.0
	for d in laptop.devices.values():
		if not d.on or d.cef == null:
			continue
		# The TV shows the video full screen unless you've got the remote in your hand
		if d.fill_video:
			laptop.fill_screen(d, not (laptop.visible and laptop.active == d))
		laptop.request_video_state(d)            # answer arrives in d.video
		if net.connected() and d.driver == net.my_id():
			var url: String = laptop.page_url(d)
			var v: Dictionary = d.video
			var has_video: bool = v.get("u", "") == url
			_device_party.rpc(_net_dev_id(d.id), d.seq, url, float(v.get("t", 0.0)), bool(v.get("p", true)), has_video)


@rpc("any_peer", "call_remote", "unreliable_ordered")
func _device_party(net_id: String, seq: int, url: String, t: float, paused: bool, has_video: bool) -> void:
	var d = _device(_local_dev_id(net_id))
	if d == null or not _accept_driver(d, multiplayer.get_remote_sender_id(), seq):
		return
	if not d.on:
		return
	if not await laptop.ensure_browser(d):
		return
	laptop.load_shared(d, url)
	if has_video:
		d.sync_t = t + 0.15          # stored so load_finished can re-apply after page loads
		d.sync_paused = paused
		laptop.apply_video_state(d, t + 0.15, paused)   # + roughly the network delay


func _party_driver_left(id: int) -> void:
	for d in laptop.devices.values():
		if d.driver == id:
			d.driver = 0


func _send_devices_to(id: int) -> void:
	for d in laptop.devices.values():
		if d.on and not d.is_phone:            # phones: each player sends their own (net.gd)
			_net_power.rpc_id(id, d.id, true, d.seq)


# ---------------------------------------------------------------- smartphones
# Everyone has a phone. M takes yours out: a phone with a home screen and a Chrome app comes
# up ("Keep in hand" lowers it - still playing in your hand; Esc or Put away puts it away). While it's
# out, a friend can look at you and press L to join it - they see the same page and can tap
# and type on it too (the same sharing as the TV: whoever touches it last drives it).
# Locally your phone is the device "phone_me"; over the network it's "phone_<your peer id>".

const MY_PHONE := "phone_me"
const PHONE_SIZE := Vector2(0.072, 0.152)        # the screen, metres
const PHONE_IN_HAND := Vector3(0.1, -0.16, -0.34) # your phone, from your eyes (bottom right)


## The phone model: a dark slab with the screen on the side facing whoever holds it (+Z)
func _make_phone(id: String, title: String, parent: Node3D, mine: bool) -> void:
	var rig := Node3D.new()
	rig.name = "Phone_" + id
	rig.visible = false
	parent.add_child(rig)
	var body := MeshInstance3D.new()
	var box := BoxMesh.new()
	box.size = Vector3(PHONE_SIZE.x + 0.008, PHONE_SIZE.y + 0.012, 0.008)
	body.mesh = box
	var bm := StandardMaterial3D.new()
	bm.albedo_color = Color(0.08, 0.08, 0.1)
	bm.metallic = 0.6
	bm.roughness = 0.3
	body.material_override = bm
	body.cast_shadow = GeometryInstance3D.SHADOW_CASTING_SETTING_OFF
	rig.add_child(body)
	var screen := MeshInstance3D.new()
	screen.name = "Screen_" + id
	var quad := QuadMesh.new()
	quad.size = PHONE_SIZE
	screen.mesh = quad
	var sm := StandardMaterial3D.new()
	sm.shading_mode = BaseMaterial3D.SHADING_MODE_UNSHADED
	screen.material_override = sm
	screen.cast_shadow = GeometryInstance3D.SHADOW_CASTING_SETTING_OFF
	screen.position.z = 0.0042
	rig.add_child(screen)
	var speaker := AudioStreamPlayer3D.new()
	speaker.name = "Speaker_" + id
	speaker.unit_size = 1.5
	speaker.max_distance = 6.0
	rig.add_child(speaker)
	var d = laptop.add_device(id, title, screen, speaker, null, "https://www.google.com", false)
	d.is_phone = true
	d.mine = mine
	d.page_size = laptop.PHONE_PAGE_SIZE
	d.rig = rig


func _make_my_phone() -> void:
	_make_phone(MY_PHONE, "Your phone", $Player/Head, true)
	var rig: Node3D = _device(MY_PHONE).rig
	rig.position = PHONE_IN_HAND
	rig.rotation = Vector3(deg_to_rad(-20), deg_to_rad(-15), 0)   # tilted up toward your eyes


## M: take your phone out (or bring it back up if it's already out)
func take_out_phone() -> void:
	use_device(MY_PHONE)


func _on_phone_put_away(id: String) -> void:
	if id == MY_PHONE:
		set_device_power(id, false)
	else:
		laptop.close()                        # stop watching a friend's phone


## Device ids over the network: your "phone_me" is "phone_<your peer id>" to everyone else
func _net_dev_id(id: String) -> String:
	return "phone_%d" % net.my_id() if id == MY_PHONE else id


func _local_dev_id(id: String) -> String:
	return MY_PHONE if id == "phone_%d" % net.my_id() else id


## net.gd: someone joined or changed their name - they get a phone (in their hand)
func on_remote_profile(peer: int, rp) -> void:
	var id := "phone_%d" % peer
	var title := "%s's phone" % rp.display_name
	if _device(id):
		_device(id).title = title
		return
	_make_phone(id, title, rp, false)


func on_remote_removed(peer: int) -> void:
	laptop.remove_device("phone_%d" % peer)


## net.gd: a new player connected - tell them whether your phone is out
func send_my_phone_to(peer: int) -> void:
	var d = _device(MY_PHONE)
	if d and d.on:
		_net_power.rpc_id(peer, _net_dev_id(MY_PHONE), true, d.seq)


## The id of the phone of the friend you're looking at, if it's out ("" if not)
func _friend_phone_in_view() -> String:
	var seen := _device_in_view()
	if seen != "" and _device(seen).is_phone:
		return seen
	var someone := _player_in_view()
	if someone != 0:
		var d = _device("phone_%d" % someone)
		if d and d.on:
			return d.id
	return ""


## Friends' phones are held in front of them, a little below their eyes
func _update_phones() -> void:
	for peer in net.remotes:
		var d = _device("phone_%d" % peer)
		var rp = net.remotes[peer]
		if d == null or rp.avatar == null or not d.on:
			continue
		d.rig.position = Vector3(0.08, rp.avatar.eye_height - 0.28, -0.3)
		d.rig.rotation.x = deg_to_rad(-25)   # screen tilted up toward their face


func _device_hint(id: String) -> String:
	var d = _device(id)
	if d == null:
		return ""
	if not d.on:
		return "T  turn the %s on     L  use it" % d.title
	var play := "     P  play / pause" if d.video.has("t") else ""
	return "L  use the %s     T  turn it off%s" % [d.title, play]


# ---------------------------------------------------------------- your avatar

func _my_mode() -> int:
	if lying_in_bed:
		return Avatar.Mode.LIE
	if sitting_in != null:
		return Avatar.Mode.SIT
	return Avatar.Mode.STAND


func _my_action() -> int:
	if interaction != 0:
		return interaction
	if holding_bear:
		return Avatar.Action.HUG_BOB if hugging_bear else Avatar.Action.HOLD
	return Avatar.Action.NONE


func _eye_height() -> float:
	return player.current_eye_height if player.seated else $Player/Head.position.y


func _update_my_avatar() -> void:
	if my_avatar == null:
		return
	my_avatar.pitch = $Player/Head.rotation.x
	my_avatar.show_head = player.third_person
	my_avatar.eye_height = _eye_height()
	my_avatar.mode = _my_mode()
	my_avatar.speed = Vector2(player.velocity.x, player.velocity.z).length()
	my_avatar.action = _my_action()
	my_avatar.hold_node = bear if holding_bear else null
	my_avatar.partner = net.avatar_for(interaction_partner) if interaction != 0 else null


func local_state() -> Array:
	# What everyone else needs to draw you: see remote_player.gd apply_state()
	return [player.global_position, player.rotation.y, $Player/Head.rotation.x, _eye_height(),
		_my_mode(), Vector2(player.velocity.x, player.velocity.z).length(), _my_action(),
		interaction_partner if interaction != 0 else 0]


# ---------------------------------------------------------------- hugs and kisses with players

func _start_interaction(kind: int, partner_id: int) -> void:
	if not begin_interaction(kind, partner_id, true):
		return
	net.request_interaction(partner_id, kind)
	var them: Avatar = net.avatar_for(partner_id)
	var at := (my_avatar.chest_global() + them.chest_global()) / 2.0 + Vector3(0, 0.35, 0)
	net.hearts.rpc(at, INTERACTION_TIME - 0.5)


## Returns false if you're busy (then the other player is told).
func begin_interaction(kind: int, partner_id: int, _i_started: bool) -> bool:
	if interaction != 0 or laptop.visible or lobby.visible or lying_in_bed:
		return false
	if net.avatar_for(partner_id) == null:
		return false
	if holding_bear:
		drop_bear()
	if sitting_in != null:
		stand_up()
	interaction = kind
	interaction_partner = partner_id
	interaction_until = Time.get_ticks_msec() / 1000.0 + INTERACTION_TIME
	player.hug_distance = Avatar.hug_distance(kind)
	player.set_collision_mask_value(2, false)   # let you get close
	return true


func end_interaction(message := "") -> void:
	interaction = 0
	interaction_partner = 0
	player.hug_target = null
	player.set_collision_mask_value(2, true)
	if message != "":
		_toast(message)


func _update_interaction() -> void:
	if interaction == 0:
		return
	var them: Avatar = net.avatar_for(interaction_partner)
	if them == null or Time.get_ticks_msec() / 1000.0 > interaction_until:
		end_interaction()
		return
	player.hug_target = them.get_parent().global_position


# ---------------------------------------------------------------- teddy bear

func _setup_bear(room: Node) -> void:
	# The bear comes in as a plain mesh; wrap it in a RigidBody3D so it has physics.
	var mesh := room.find_child("Bob", true, false) as Node3D
	if mesh == null:
		mesh = room.find_child("Teddy_Bear", true, false) as Node3D   # older room.glb
	if mesh == null:
		return
	bear = RigidBody3D.new()
	bear.name = "Bob"
	bear.mass = 0.3
	bear.angular_damp = 3.0
	bear.linear_damp = 0.5
	bear.freeze_mode = RigidBody3D.FREEZE_MODE_KINEMATIC
	add_child(bear)
	bear.global_transform = mesh.global_transform
	bear.global_position.y += 0.01            # start just above the duvet, then settle
	mesh.get_parent().remove_child(mesh)
	bear.add_child(mesh)
	mesh.transform = Transform3D.IDENTITY     # model's origin is its bottom-centre
	bear_mesh = mesh
	_apply_bear_texture(mesh)
	var shape := CollisionShape3D.new()
	var box := BoxShape3D.new()
	box.size = BEAR_SIZE
	shape.shape = box
	shape.position.y = BEAR_SIZE.y / 2.0
	bear.add_child(shape)


const BEAR_TEXTURE := "res://bear_texture.png"

func _apply_bear_texture(mesh_node: Node3D) -> void:
	# Godot sometimes imports the bear from room.glb without its photo texture,
	# so put it back from bear_texture.png (saved next to room.glb by the Blender script).
	var mi := mesh_node as MeshInstance3D
	if mi == null or mi.mesh == null or not ResourceLoader.exists(BEAR_TEXTURE):
		return
	var tex: Texture2D = load(BEAR_TEXTURE)
	for i in mi.mesh.get_surface_count():
		var mat: StandardMaterial3D
		var current: Material = mi.get_active_material(i)
		if current and current.resource_name.begins_with("Bob_"):
			continue                          # his fur bottom / paw pads have their own colours
		if current is StandardMaterial3D:
			if current.albedo_texture != null:
				continue                      # already textured - leave it
			mat = current.duplicate()
		else:
			mat = StandardMaterial3D.new()
		mat.albedo_texture = tex
		mat.albedo_color = Color.WHITE
		mat.roughness = 0.9
		mat.metallic = 0.0
		mi.set_surface_override_material(i, mat)


## Nothing solid (a floor, ceiling, wall, shut door) between your eye and this point?
## Hits within `tolerance` of the point count as the thing itself (the TV's own frame, the sofa).
func _can_see(point: Vector3, tolerance := 0.35) -> bool:
	var from := _eye().origin
	if absf(point.y - from.y) > 1.8:            # another storey (floors can be one-sided to rays)
		return false
	var query := PhysicsRayQueryParameters3D.create(from, point)
	var skip: Array[RID] = [player.get_rid()]
	if bear and holding_bear:
		skip.append(bear.get_rid())
	query.exclude = skip
	var hit := get_world_3d().direct_space_state.intersect_ray(query)
	return hit.is_empty() or hit["position"].distance_to(point) <= tolerance


func _camera_ray(distance: float) -> Dictionary:
	var eye := _eye()
	var from := eye.origin
	var to := from - eye.basis.z * distance
	var query := PhysicsRayQueryParameters3D.create(from, to)
	var skip: Array[RID] = [player.get_rid()]
	if bear and holding_bear:
		skip.append(bear.get_rid())
	query.exclude = skip
	return get_world_3d().direct_space_state.intersect_ray(query)


func _looking_at_bear() -> bool:
	if bear == null or holding_bear or bob_holder != 0:
		return false
	var hit := _camera_ray(REACH)
	return not hit.is_empty() and hit["collider"] == bear


func pick_up_bear() -> void:
	if bear == null or bob_holder != 0:
		return
	# Keep whatever way he was lying, relative to the way you're facing
	bear_spin = (Basis(Vector3.UP, -player.rotation.y) * bear.global_basis).orthonormalized()
	if net.connected() and not multiplayer.is_server():
		_req_pick.rpc_id(1)                   # ask the host; it tells everyone who has him
	else:
		_server_pick(net.my_id())


func drop_bear() -> void:
	var xf := bear.global_transform
	var vel: Vector3 = player.velocity * 0.8 + Vector3(0, -0.2, 0)  # a bit of your movement + a nudge down
	holding_bear = false
	hugging_bear = false
	if bear_mesh:
		bear_mesh.scale = Vector3.ONE
	if net.connected() and not multiplayer.is_server():
		_bob_target = xf
		_bob_has_target = true
		_req_drop.rpc_id(1, xf, vel)
	else:
		_server_drop(xf, vel)


# --- Bob over the network: the host decides who holds him and runs his physics when he's free

@rpc("any_peer", "call_remote", "reliable")
func _req_pick() -> void:
	if multiplayer.is_server():
		_server_pick(multiplayer.get_remote_sender_id())


@rpc("any_peer", "call_remote", "reliable")
func _req_drop(xf: Transform3D, vel: Vector3) -> void:
	if multiplayer.is_server() and multiplayer.get_remote_sender_id() == bob_holder:
		_server_drop(xf, vel)


func _server_pick(id: int) -> void:
	if bob_holder != 0:
		return
	if net.connected():
		_bob_holder_changed.rpc(id)
	else:
		_bob_holder_changed(id)


func _server_drop(xf: Transform3D, vel: Vector3) -> void:
	if net.connected():
		_bob_holder_changed.rpc(0)
	else:
		_bob_holder_changed(0)
	bear.global_transform = xf
	bear.linear_velocity = vel
	bear.angular_velocity = Vector3.ZERO
	# Wake the physics body up. Without this Bob could stay "asleep" after being carried
	# and hang in mid-air until something bumped him.
	bear.sleeping = false
	bear.apply_central_impulse(Vector3(0, -0.01, 0))


@rpc("authority", "call_local", "reliable")
func _bob_holder_changed(id: int) -> void:
	bob_holder = id
	var mine: bool = id != 0 and id == net.my_id()
	if mine:
		holding_bear = true
	else:
		holding_bear = false
		hugging_bear = false
	# Only the host simulates a free Bob; everyone else just follows the host's updates
	bear.freeze = id != 0 or not net.is_host()
	bear.collision_layer = 0 if id != 0 else 1   # don't bump into anyone while carried
	bear.collision_mask = 0 if id != 0 else 1
	if id != 0 and bear_mesh and not mine:
		bear_mesh.scale = Vector3.ONE


@rpc("any_peer", "call_remote", "unreliable_ordered")
func _bob_xform(xf: Transform3D, squeeze: float) -> void:
	var from := multiplayer.get_remote_sender_id()
	if holding_bear:
		return
	if from != bob_holder and not (bob_holder == 0 and from == 1):
		return                                # stale update from someone who let go
	_bob_target = xf
	_bob_has_target = true
	if bear_mesh:
		bear_mesh.scale = Vector3(1.0 + squeeze, 1.0 - squeeze, 1.0 + squeeze)


@rpc("authority", "call_remote", "reliable")
func _world(light_mode: int, desk: bool, level: float, holder: int, bob_xf: Transform3D) -> void:
	# Sent by the host when you join: the current lights and Bob
	set_mode(light_mode, true)
	desk_on = desk
	desk_level = level
	_apply(true)
	if bear:
		_bob_holder_changed(holder)
		bear.global_transform = bob_xf
		_bob_target = bob_xf
		_bob_has_target = true


func send_world_to(id: int) -> void:
	_world.rpc_id(id, mode, desk_on, desk_level, bob_holder,
		bear.global_transform if bear else Transform3D())
	for i in doors.size():
		if doors[i]["open"]:
			_net_door.rpc_id(id, i, true)
	_send_devices_to(id)


func on_player_left(id: int) -> void:
	if bob_holder == id and bear:
		_server_drop(bear.global_transform, Vector3.ZERO)
	if interaction_partner == id:
		end_interaction()


func _physics_process(delta: float) -> void:
	if interaction_partner != 0 and net.avatar_for(interaction_partner) == null:
		end_interaction()
	if bear == null:
		return
	if holding_bear:
		_hold_bear(delta)
	elif _bob_has_target and bear.freeze and bob_holder != net.my_id():
		# Someone else has him (or the host is simulating him): follow the updates smoothly
		var t := 1.0 - exp(-20.0 * delta)
		var xf := bear.global_transform
		bear.global_transform = Transform3D(
			xf.basis.orthonormalized().slerp(_bob_target.basis.orthonormalized(), t),
			xf.origin.lerp(_bob_target.origin, t))

	# Stream Bob to everyone: the holder sends him, otherwise the host sends his physics
	if net.connected():
		_bob_send += delta
		var i_send: bool = holding_bear or (bob_holder == 0 and multiplayer.is_server() and not bear.sleeping)
		if i_send and _bob_send >= 1.0 / 30.0:
			_bob_send = 0.0
			var squeeze: float = bear_mesh.scale.x - 1.0 if bear_mesh else 0.0
			_bob_xform.rpc(bear.global_transform, squeeze)


func _hold_bear(delta: float) -> void:
	var yaw_basis := Basis(Vector3.UP, player.rotation.y)
	var hold_basis := yaw_basis * bear_spin
	var middle := Vector3(0, BEAR_SIZE.y / 2.0, 0)
	var centre: Vector3
	if hugging_bear:
		# Pulled in against your tummy, squeezed a little
		centre = my_avatar.hold_point(true)
		_hug_time += delta
		var s := 0.05 + 0.03 * sin(_hug_time * 5.0)
		bear_mesh.scale = bear_mesh.scale.lerp(Vector3(1.0 + s, 1.0 - s, 1.0 + s), 1.0 - exp(-10.0 * delta))
		if int(_hug_time * 2.5) != int((_hug_time - delta) * 2.5):
			if net.connected():
				net.hearts.rpc(centre + Vector3(0, 0.15, 0), 0.25)
			else:
				Hearts.burst(self, centre + Vector3(0, 0.15, 0), 0.25)
	else:
		_hug_time = 0.0
		bear_mesh.scale = bear_mesh.scale.lerp(Vector3.ONE, 1.0 - exp(-10.0 * delta))
		# Held out in your little hands in front of you
		centre = my_avatar.hold_point(false)
	# He turns with you, plus however you've spun him (right-drag / wheel).
	# Rotate around his middle, not his feet, so he spins in place.
	var target := Transform3D(hold_basis, centre - hold_basis * middle)
	var t := 1.0 - exp(-25.0 * delta)
	bear.global_transform = Transform3D(
		bear.global_basis.orthonormalized().slerp(target.basis.orthonormalized(), t),
		bear.global_position.lerp(target.origin, t))


# ---------------------------------------------------------------- chairs and bed

var sitting_in: Node3D = null
var lying_in_bed := false


func _thing_in_view(name_prefix: String) -> Node3D:
	# The object (e.g. "Chair_..." or "Bed") the crosshair is on, within reach
	var hit := _camera_ray(REACH)
	if hit.is_empty():
		return null
	var n: Node = hit["collider"]
	while n != null:
		if n is Node3D and String(n.name).begins_with(name_prefix):
			return n
		n = n.get_parent()
	return null


## The seat you're looking at: a "Chair_" seat itself, or the seat nearest to where you're
## looking on a sofa / armchair (its arms, back, base) - like sitting down in real life
func _chair_in_view() -> Node3D:
	var hit := _camera_ray(REACH)
	if hit.is_empty():
		return null
	var n: Node = hit["collider"]
	while n != null:
		if n is Node3D and String(n.name).begins_with("Chair_"):
			return n
		n = n.get_parent()
	var best: Node3D = null
	var best_d := 0.9
	for c: Node3D in find_children("Chair_*", "Node3D", true, false):
		var d: float = c.global_position.distance_to(hit["position"])   # 3D: not through floors
		var rise: float = _eye().origin.y - c.global_position.y     # the seat is on your floor
		if d < best_d and rise > -0.3 and rise < 1.5 and _can_see(c.global_position + Vector3(0, 0.15, 0), 0.6):
			best = c
			best_d = d
	return best


func lie_down() -> void:
	# In the bed, under the duvet: head on the pillow (window end), looking down the bed.
	# The duvet (blanket.gd) drapes over your body while you're in bed.
	lying_in_bed = true
	player.sit_at(b2g(Blanket.HEAD_X, _bed_side(), Blanket.MATTRESS), deg_to_rad(90), my_avatar.lie_eye_height(), deg_to_rad(12))


## Where you lie across the bed (Blender Y): the middle when you're alone, otherwise
## side by side - the lower peer id takes the room side, the other the wall side.
func _bed_side() -> float:
	var others: Array = net.lying_ids()
	if others.is_empty():
		return Blanket.BODY_Y
	var rank := 0
	for id in others:
		if id < net.my_id():
			rank += 1
	return Blanket.BODY_Y + (Blanket.SIDE if rank == 0 else -Blanket.SIDE)


func get_out_of_bed() -> void:
	lying_in_bed = false
	player.stand_at(b2g(2.0, 1.35, 0.05), 0.0)   # step off on the room side, facing into the room


## Which way a chair faces (Godot yaw). Every chair object's local +X (Blender) points
## the way you face when sitting in it (the bedroom chairs face their desks this way too).
func _chair_yaw(chair: Node3D) -> float:
	return chair.global_rotation.y - PI / 2.0


func sit_down(chair: Node3D) -> void:
	sitting_in = chair
	var seat := chair.global_position        # (origin on that storey's floor: upstairs 0, downstairs -2.76)
	player.sit_at(seat, _chair_yaw(chair))


func stand_up() -> void:
	# Office chairs: step out behind the chair. Sofas / armchairs: stand up in front.
	var yaw := _chair_yaw(sitting_in)
	var forward := Vector3(-sin(yaw), 0, -cos(yaw))
	var lounge := String(sitting_in.name).contains("Sofa") or String(sitting_in.name).contains("Armchair")
	var spot := sitting_in.global_position + (forward * 0.7 if lounge else -forward * 0.6)
	spot.y = sitting_in.global_position.y + 0.05
	player.stand_at(spot, yaw)
	sitting_in = null


# ---------------------------------------------------------------- setup helpers

func _collect_glow_materials(node: Node) -> void:
	var mi := node as MeshInstance3D
	if mi and mi.mesh:
		for i in mi.mesh.get_surface_count():
			var mat: Material = mi.get_active_material(i)
			if mat is BaseMaterial3D and mat.resource_name in GLOW_MATERIALS:
				var key: String = mat.resource_name
				if not glow_mats.has(key):
					var dup: BaseMaterial3D = mat.duplicate()
					dup.emission_enabled = true
					var full: float = dup.emission_energy_multiplier
					if full <= 0.0:
						full = 2.0
					glow_mats[key] = [dup, full]
				mi.set_surface_override_material(i, glow_mats[key][0])
	for child in node.get_children():
		_collect_glow_materials(child)


func _make_labels() -> void:
	var settings: LabelSettings = $HUD/Help.label_settings
	mode_label = Label.new()
	mode_label.label_settings = settings
	mode_label.anchor_left = 1.0
	mode_label.anchor_right = 1.0
	mode_label.offset_left = -300
	mode_label.offset_right = -16
	mode_label.offset_top = 12
	mode_label.horizontal_alignment = HORIZONTAL_ALIGNMENT_RIGHT
	$HUD.add_child(mode_label)

	net_label = Label.new()
	var small := settings.duplicate()
	small.font_size = 14
	net_label.label_settings = small
	net_label.anchor_left = 1.0
	net_label.anchor_right = 1.0
	net_label.offset_left = -700
	net_label.offset_right = -16
	net_label.offset_top = 40
	net_label.horizontal_alignment = HORIZONTAL_ALIGNMENT_RIGHT
	$HUD.add_child(net_label)

	hint_label = Label.new()
	hint_label.label_settings = settings
	hint_label.anchor_left = 0.5
	hint_label.anchor_right = 0.5
	hint_label.anchor_top = 0.5
	hint_label.anchor_bottom = 0.5
	hint_label.offset_left = -400
	hint_label.offset_right = 400
	hint_label.offset_top = 24
	hint_label.horizontal_alignment = HORIZONTAL_ALIGNMENT_CENTER
	hint_label.visible = false
	$HUD.add_child(hint_label)


func _hide_blender_cameras(node: Node) -> void:
	for child in node.get_children():
		if child is Camera3D:
			child.current = false
		_hide_blender_cameras(child)


func _add_fallback_floor() -> void:
	var floor_body := StaticBody3D.new()
	var col := CollisionShape3D.new()
	var box := BoxShape3D.new()
	box.size = Vector3(20, 1, 20)
	col.shape = box
	col.position.y = -0.5
	floor_body.add_child(col)
	var mesh := MeshInstance3D.new()
	var plane := PlaneMesh.new()
	plane.size = Vector2(20, 20)
	mesh.mesh = plane
	floor_body.add_child(mesh)
	add_child(floor_body)


# ---------------------------------------------------------------- performance
# Only the storey you're on is drawn (both near the stairs), and only its lights are on - lights
# without shadows would also shine through the floors. "Low" graphics (auto on integrated GPUs,
# G to switch, remembered) renders at 75 %, drops ambient occlusion and shadows, keeps only
# lights near you, makes mirrors smaller and runs physics at 60 Hz.
const SETTINGS_PATH := "user://settings.cfg"
const LIGHT_RANGE_LOW := 9.0
var low_quality := false
var _cull_timer := 0.0
var _upstairs_nodes: Array[Node3D] = []      # bedroom + the flat's rooms (not its garden / sky)
var _ground_nodes: Array[Node3D] = []
var _light_floor := {}                       # OmniLight3D -> true if it's downstairs
var _well_view := {}                         # node -> true if it can be seen through the stair well
# the stair well (and a margin) in Godot coordinates: Blender X 1.0..7.0, Y 2.8..6.6
const WELL_BOX := AABB(Vector3(1.0, -3.2, -6.6), Vector3(6.0, 6.4, 3.8))


func _init_quality() -> void:
	for root_name in ["Room", "Flat"]:
		var r := get_node_or_null(root_name) as Node3D
		if r == null:
			continue
		for c in r.get_children():
			var nm := String(c.name)
			if c is Node3D and not (nm.begins_with("Flat_Outside") or nm.begins_with("Flat_Lawn")
					or nm.begins_with("Flat_Sky") or nm.begins_with("Flat_Stair") or nm.begins_with("Flat_Balustrade")):
				_upstairs_nodes.append(c)
	var g := get_node_or_null("Ground") as Node3D
	if g:
		for c in g.get_children():
			if c is Node3D:
				_ground_nodes.append(c)
	for l in flat_lights:
		_light_floor[l] = l.global_position.y < -1.0
	for n in _upstairs_nodes + _ground_nodes:
		var mi := n as MeshInstance3D
		_well_view[n] = mi == null or (mi.global_transform * mi.get_aabb()).intersects(WELL_BOX)
	var cfg := ConfigFile.new()
	var low := _weak_hardware()
	if cfg.load(SETTINGS_PATH) == OK:
		low = cfg.get_value("graphics", "low", low)
	set_quality(low, false)


func _weak_hardware() -> bool:
	var kind := RenderingServer.get_video_adapter_type()
	if kind == RenderingDevice.DEVICE_TYPE_INTEGRATED_GPU or kind == RenderingDevice.DEVICE_TYPE_CPU:
		return true
	return OS.get_processor_count() <= 4


func set_quality(low: bool, save := true) -> void:
	low_quality = low
	var vp := get_viewport()
	vp.scaling_3d_mode = Viewport.SCALING_3D_MODE_FSR if low else Viewport.SCALING_3D_MODE_BILINEAR
	vp.scaling_3d_scale = 0.75 if low else 1.0
	env.ssao_enabled = not low
	for l in [desk_spot, shelf_light]:
		if l:
			l.shadow_enabled = not low
	Engine.physics_ticks_per_second = 60 if low else 120
	for m in mirrors:
		if m.viewport:
			var px := 280.0 if low else 560.0
			m.viewport.size = Vector2i(int(m.width * px), int(m.height * px))
			m.viewport.msaa_3d = Viewport.MSAA_DISABLED if low else Viewport.MSAA_2X
	_cull_timer = 0.0
	if save:
		var cfg := ConfigFile.new()
		cfg.load(SETTINGS_PATH)
		cfg.set_value("graphics", "low", low)
		cfg.save(SETTINGS_PATH)


func _update_culling(delta: float) -> void:
	_cull_timer -= delta
	if _cull_timer > 0.0 or player == null:
		return
	_cull_timer = 0.25
	var p := player.global_position
	var bx := p.x
	var by := -p.z                                 # Blender Y
	var downstairs := p.y < -1.3
	# near the stair well you can see both storeys
	var near_well := bx > 0.5 and bx < 7.5 and by > 2.8 and by < 6.6
	var show_up := not downstairs or near_well
	var show_down := downstairs or near_well
	for n in _upstairs_nodes:
		n.visible = show_up or _well_view[n]       # what's around the well stays: you can look through it
	for n in _ground_nodes:
		n.visible = show_down or _well_view[n]
	for l: OmniLight3D in _light_floor:
		var on: bool = show_down if _light_floor[l] else show_up
		if on and low_quality:
			on = l.global_position.distance_to(p) < LIGHT_RANGE_LOW
		l.visible = on
