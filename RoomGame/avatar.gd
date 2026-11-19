extends Node3D
## Your character (and other players'): a small, round, cute creature made of soft shapes.
## Two styles:  "sprout" - a bean-shaped little guy with a two-leaf sprout on top
##              "puff"   - a round woolly fluff-ball with floppy ears
##
## first_person = true hides the head from your own camera (render layer 2) so you see
## your body, arms and feet. In third person (show_head = true) everything is visible.
##
## The owner sets pitch / eye_height / mode / speed / action / hold_node / partner every
## frame and the avatar poses itself. Arms and legs use two-bone IK, so hands really
## reach Bob or the person you're hugging, and feet stay on the floor.
## Origin = the feet, facing -Z (same as the player).

const STYLES := ["p2", "p3"]
## The two characters are 3D models (made 4 ft / 1.22 m tall, feet at the origin, facing -Z
## by the Blender conversion). p2 = Snoopy (rigged, has a "Walk" animation),
## p3 = Miffy (a statue; its "dress" material takes the colour picked in the lobby).
const MODELS := {"p2": "res://models/p2.glb", "p3": "res://models/p3.glb"}
## Measured from the models (model space: feet at y 0, facing -Z, back = +Z):
##  eye        height of the eyes (where your camera is when standing)
##  bottom     lowest point of the bum (sits on the chair seat)
##  head_y     the point that lies on the pillow (high enough that ears stay off the wall)
##  head_back  back of the head,  face  front of the face
##  body_back / body_depth   tummy front-to-back (for lying under the duvet)
const FIT := {
	"p2": {"eye": 1.05, "bottom": 0.18, "head_y": 1.00, "head_back": 0.25, "face": 0.25, "body_back": 0.15, "body_depth": 0.31},
	"p3": {"eye": 0.72, "bottom": 0.13, "head_y": 0.95, "head_back": 0.19, "face": 0.20, "body_back": 0.22, "body_depth": 0.44},
}
## p2's rig: [bone that turns, bone at the end of the limb, side (-1 = left)]
const P2_LIMBS := {
	"arm": [["DEF-upper_arm.L", "DEF-hand.L", -1.0], ["DEF-upper_arm.R", "DEF-hand.R", 1.0]],
	"leg": [["DEF-thigh.L", "DEF-foot.L", -1.0], ["DEF-thigh.R", "DEF-foot.R", 1.0]],
}
const PILLOW := 0.12           # pillow top above the mattress (build_room.py)
const LIE_THICK := 0.30        # under the duvet the body is flattened to about this, front to back
const EYE := 1.05              # camera height when standing (player.gd stand_eye_height)
const HIP_Y := 0.4
const SEAT_Y := 0.47           # chair seat height
const UPPER_ARM := 0.18
const FOREARM := 0.16
const THIGH := 0.19
const SHIN := 0.17
const SHOULDER := Vector3(0.27, 0.58, 0.0)   # relative to the hips
const HEAD := Vector3(0, 0.55, 0.0)          # head centre, relative to the hips
const HEAD_R := 0.33
const BELLY := 0.27            # how far the tummy sticks out in front
const LIE_EYE := 0.36          # camera height above the mattress when lying in bed

enum Mode { STAND, SIT, LIE }
enum Action { NONE, HOLD, HUG_BOB, HUG, KISS }

var style := "p2"
var _model: Node3D = null
var _anim: AnimationPlayer = null
var _skel: Skeleton3D = null
var _limbs: Array[Dictionary] = []   # model arms / legs: {kind, side, node | bone + tip, rest_dir}
var _arm_target: Array = [null, null]  # world point each hand reaches for (hug / hold), or null
var _walk_w := 0.0                   # 0 = standing rest pose .. 1 = walk animation
var color := Color(0.62, 0.86, 0.6)
var first_person := false
var show_head := true

# Set by the owner every frame
var pitch := 0.0
var eye_height := EYE
var mode := Mode.STAND
var speed := 0.0
var action := Action.NONE
var hold_node: Node3D = null   # Bob, while holding / hugging him (origin at his feet)
var partner: Node3D = null     # the other avatar, while hugging / kissing

var body: Node3D               # pivots at the hips: tummy, head
var head: Node3D
var _head_parts: Array[MeshInstance3D] = []
var arms := []                 # [{upper, fore, hand, side}]
var legs := []                 # [{thigh, shin, foot, side}]
var _hands_local := [Vector3.ZERO, Vector3.ZERO]
var _walk := 0.0
var _crouch := 0.0
var _sit := 0.0
var _lean := 0.0
var _tilt := 0.0
var _act := 0.0
var _blink := 0.0
var _eyes: Array[Node3D] = []
var _ready_done := false


func _ready() -> void:
	_build()
	_ready_done = true


# ---------------------------------------------------------------- building

func _mat(c: Color, rough := 0.75, rim := 0.25) -> StandardMaterial3D:
	var m := StandardMaterial3D.new()
	m.albedo_color = c
	m.roughness = rough
	m.rim_enabled = rim > 0.0           # soft fuzzy edge light - makes it look plush
	m.rim = rim
	m.rim_tint = 0.6
	return m


func _sphere(r: float, segments := 24) -> SphereMesh:
	var s := SphereMesh.new()
	s.radius = r
	s.height = r * 2.0
	s.radial_segments = segments
	s.rings = segments / 2
	return s


func _capsule(r: float, h: float) -> CapsuleMesh:
	var c := CapsuleMesh.new()
	c.radius = r
	c.height = maxf(h, r * 2.0)
	c.radial_segments = 16
	c.rings = 6
	return c


func _part(parent: Node3D, mesh: Mesh, mat: Material, pos: Vector3, scale_by := Vector3.ONE,
		is_head := false) -> MeshInstance3D:
	var mi := MeshInstance3D.new()
	mi.mesh = mesh
	mi.material_override = mat
	mi.position = pos
	mi.scale = scale_by
	parent.add_child(mi)
	if is_head:
		_head_parts.append(mi)
	return mi


func _build_model() -> void:
	body = Node3D.new()
	body.name = "Body"
	body.position = Vector3(0, HIP_Y, 0)
	add_child(body)
	head = Node3D.new()                 # not drawn; kept so the posing code has a head to turn
	head.name = "Head"
	head.position = Vector3(0, 0.66, 0)
	body.add_child(head)

	_model = (load(MODELS[style]) as PackedScene).instantiate()
	_model.position = Vector3(0, -HIP_Y, 0)          # feet on the floor
	body.add_child(_model)
	for mi: MeshInstance3D in _model.find_children("*", "MeshInstance3D", true, false):
		if mi.mesh == null or mi.mesh.get_surface_count() == 0:
			continue
		if mi.mesh.get_aabb().size.length() > 2.5:     # bone-display helper shapes
			mi.visible = false
			continue
		_head_parts.append(mi)                       # first person: hide the whole model
		for i in mi.mesh.get_surface_count():
			var m := mi.mesh.surface_get_material(i)
			if m and m.resource_name == "dress":
				var dress := _mat(color, 0.8, 0.15)
				mi.set_surface_override_material(i, dress)
	if first_person:
		for p in _head_parts:
			p.layers = 2
	_anim = _model.find_child("AnimationPlayer", true, false) as AnimationPlayer
	var skels := _model.find_children("*", "Skeleton3D", true, false)
	_skel = skels[0] as Skeleton3D if skels.size() > 0 else null
	if _anim and _anim.has_animation("Walk") and _skel:
		_anim.get_animation("Walk").loop_mode = Animation.LOOP_LINEAR
		# We advance the animation ourselves, so we can blend back to the standing pose
		# and bend arms / legs on top of it in the same frame.
		_anim.callback_mode_process = AnimationMixer.ANIMATION_CALLBACK_MODE_PROCESS_MANUAL
		_anim.stop(true)
	else:
		_anim = null
	_find_limbs()

	# Arms and legs are still solved (hands for hugs / holding Bob) but not drawn
	var hidden := _mat(color)
	_build_limbs(hidden, hidden)
	for n in [arms, legs]:
		for limb: Dictionary in n:
			for part in limb.values():
				if part is Node3D:
					part.visible = false


func _find_limbs() -> void:
	_limbs.clear()
	if _skel:
		for kind in P2_LIMBS:
			for l: Array in P2_LIMBS[kind]:
				var b := _skel.find_bone(l[0])
				var t := _skel.find_bone(l[1])
				if b >= 0 and t >= 0:
					_limbs.append({"kind": kind, "side": l[2], "bone": b, "tip": t})
		return
	# p3: separate pieces ArmL / ArmR / LegL / LegR, each turning at its own origin
	for n in ["ArmL", "ArmR", "LegL", "LegR"]:
		var mi := _model.find_child(n, true, false) as MeshInstance3D
		if mi == null or mi.mesh == null:
			continue
		var rest := mi.mesh.get_aabb().get_center()
		rest = rest.normalized() if rest.length() > 0.01 else Vector3.DOWN
		_limbs.append({"kind": "arm" if n.begins_with("Arm") else "leg",
			"side": -1.0 if n.ends_with("L") else 1.0, "node": mi, "rest_dir": rest})


func _fit(key: String) -> float:
	var f: Dictionary = FIT.get(style, FIT["p3"])
	return f[key]


## How the body lies in bed: head on the pillow, a little tilted so the hips sink into
## the mattress, flattened front-to-back so the duvet stays a gentle bump.
func _lie() -> Dictionary:
	var sq := clampf(LIE_THICK / _fit("body_depth"), 0.6, 1.0)
	var h := PILLOW + _fit("head_back") * sq - 0.07          # head sinks into the pillow a bit
	var s := clampf((h - _fit("body_back") * sq + 0.03) / (_fit("head_y") - 0.3), 0.0, 0.45)
	var top := h - (_fit("head_y") - 0.45) * s - _fit("body_back") * sq + _fit("body_depth") * sq
	return {"sq": sq, "h": h, "tilt": asin(s), "top": top, "eye": h + _fit("face") * sq + 0.03}


## Highest point of the tummy above the mattress when lying (blanket.gd fits the duvet to it)
func lie_top() -> float:
	return _lie()["top"]


## Camera height above the mattress when lying (just in front of the face)
func lie_eye_height() -> float:
	return _lie()["eye"]


## Camera height when sitting on a chair (the bum rests on the seat)
func seated_eye_height() -> float:
	return _fit("eye") + SEAT_Y - _fit("bottom")


## Camera height when standing / crouching: at this character's eyes
func stand_eye_height() -> float:
	return _fit("eye")


func crouch_eye_height() -> float:
	return _fit("eye") * 0.67


func _build() -> void:
	if MODELS.has(style):
		_build_model()
		return
	var main_col := color
	var dark_col := color.darkened(0.25)
	var belly_col := color.lerp(Color(1, 0.98, 0.92), 0.55)
	if style == "puff":
		main_col = color.lerp(Color(1, 1, 1), 0.55)      # wool is a pale version of the colour
		dark_col = color.darkened(0.15)                  # face, ears, hands and feet
		belly_col = main_col
	var skin := _mat(main_col)
	var dark := _mat(dark_col)
	var tummy := _mat(belly_col)
	var eye := _mat(Color(0.07, 0.06, 0.08), 0.15, 0.0)
	var shine := _mat(Color(1, 1, 1), 0.1, 0.0)
	shine.shading_mode = BaseMaterial3D.SHADING_MODE_UNSHADED
	var blush := _mat(Color(1.0, 0.55, 0.6), 0.8, 0.0)
	blush.transparency = BaseMaterial3D.TRANSPARENCY_ALPHA
	blush.albedo_color.a = 0.7
	var leaf := _mat(Color(0.35, 0.72, 0.3), 0.6, 0.2)

	body = Node3D.new()
	body.name = "Body"
	body.position = Vector3(0, HIP_Y, 0)
	add_child(body)

	# Tummy: a soft egg shape
	_part(body, _sphere(1.0, 32), skin, Vector3(0, 0.3, 0), Vector3(0.33, 0.42, 0.27))
	_part(body, _sphere(1.0, 24), tummy, Vector3(0, 0.25, -0.09), Vector3(0.24, 0.3, 0.2))
	if style == "puff":
		# woolly bumps all over the body
		for i in 14:
			var a := TAU * i / 14.0
			var y := 0.2 + 0.25 * float(i % 3) / 2.0
			_part(body, _sphere(0.12, 12), skin, Vector3(cos(a) * 0.27, y, sin(a) * 0.22))

	# Head (hidden from your own camera in first person)
	head = Node3D.new()
	head.name = "Head"
	head.position = Vector3(0, 0.66, 0)                  # neck pivot
	body.add_child(head)
	var hc := HEAD - Vector3(0, 0.66, 0)                 # head centre relative to the neck
	if style == "sprout":
		_part(head, _sphere(1.0, 32), skin, hc, Vector3(HEAD_R * 1.05, HEAD_R * 0.95, HEAD_R), true)
		# the sprout: little stem + two leaves
		var stem := CylinderMesh.new()
		stem.top_radius = 0.012
		stem.bottom_radius = 0.018
		stem.height = 0.12
		_part(head, stem, leaf, hc + Vector3(0, HEAD_R * 0.95 + 0.04, 0), Vector3.ONE, true)
		for s in [-1.0, 1.0]:
			var l := _part(head, _sphere(1.0, 16), leaf, hc + Vector3(s * 0.07, HEAD_R * 0.95 + 0.11, 0),
				Vector3(0.08, 0.025, 0.045), true)
			l.rotation.z = s * 0.45
	else:
		# wool on top, darker face in front, floppy ears
		_part(head, _sphere(1.0, 32), skin, hc, Vector3(HEAD_R, HEAD_R * 0.95, HEAD_R), true)
		for i in 9:
			var a := TAU * i / 9.0
			_part(head, _sphere(0.11, 12), skin,
				hc + Vector3(cos(a) * 0.22, 0.2 + 0.05 * sin(a * 2.0), sin(a) * 0.2 + 0.03), Vector3.ONE, true)
		_part(head, _sphere(1.0, 24), dark, hc + Vector3(0, -0.04, -0.17), Vector3(0.22, 0.2, 0.17), true)
		for s in [-1.0, 1.0]:
			var ear := _part(head, _sphere(1.0, 16), dark, hc + Vector3(s * 0.34, 0.02, 0.0),
				Vector3(0.06, 0.15, 0.08), true)
			ear.rotation.z = s * 1.1
	# Face: big shiny eyes, rosy cheeks, a little smile
	var face_z := -HEAD_R * 0.93 if style == "sprout" else -HEAD_R * 1.08 + 0.04
	for s in [-1.0, 1.0]:
		var e := _part(head, _sphere(1.0, 16), eye, hc + Vector3(s * 0.11, 0.02, face_z), Vector3(0.045, 0.06, 0.03), true)
		_eyes.append(e)
		_part(head, _sphere(1.0, 10), shine, hc + Vector3(s * 0.11 + 0.015, 0.045, face_z - 0.022),
			Vector3(0.016, 0.018, 0.01), true)
		_part(head, _sphere(1.0, 12), blush, hc + Vector3(s * 0.2, -0.07, face_z + 0.06),
			Vector3(0.05, 0.03, 0.02), true)
	var smile := TorusMesh.new()
	smile.inner_radius = 0.022
	smile.outer_radius = 0.03
	var m := _part(head, smile, eye, hc + Vector3(0, -0.07, face_z - 0.005), Vector3(1, 0.6, 1), true)
	m.rotation.x = PI / 2

	if first_person:
		for p in _head_parts:
			p.layers = 2                 # the player's camera doesn't draw layer 2 (shadows still do)

	# Arms and legs: placed in world space every frame by the IK, so they're top-level
	_build_limbs(skin, dark if style == "puff" else skin)


func _build_limbs(skin: Material, limb: Material) -> void:
	for side in [-1.0, 1.0]:
		var upper := _limb_bone(UPPER_ARM, 0.075, skin)
		var fore := _limb_bone(FOREARM, 0.068, skin)
		var hand := Node3D.new()
		hand.top_level = true
		add_child(hand)
		_part(hand, _sphere(0.085, 16), limb, Vector3(0, 0, -0.02))
		arms.append({"upper": upper, "fore": fore, "hand": hand, "side": side})
		var thigh := _limb_bone(THIGH, 0.09, skin)
		var shin := _limb_bone(SHIN, 0.085, skin)
		var foot := Node3D.new()
		foot.top_level = true
		add_child(foot)
		_part(foot, _sphere(1.0, 16), limb, Vector3(0, 0.0, -0.05), Vector3(0.1, 0.07, 0.14))
		legs.append({"thigh": thigh, "shin": shin, "foot": foot, "side": side})
	for i in 2:
		var s: float = arms[i]["side"]
		_hands_local[i] = Vector3(s * 0.34, 0.3, 0.0)


func _limb_bone(length: float, radius: float, mat: Material) -> Node3D:
	var n := Node3D.new()
	n.top_level = true
	add_child(n)
	var mi := _part(n, _capsule(radius, length + radius * 2.0), mat, Vector3(0, 0, -length / 2.0))
	mi.rotation.x = -PI / 2           # capsule along -Z (the bone direction)
	return n


# ---------------------------------------------------------------- queries for main.gd

func chest_global() -> Vector3:
	return body.global_transform * Vector3(0, 0.3, 0)


func head_global() -> Vector3:
	return body.global_transform * HEAD


## Where Bob's middle goes: held out in your hands, or squeezed against your tummy
func hold_point(hug: bool) -> Vector3:
	var b := body.global_transform
	if hug:
		return b * Vector3(0, 0.22, -(BELLY + 0.07))
	return b * Vector3(0, 0.3, -(BELLY + 0.11))


## How close two players stand when hugging / kissing (the tummies and heads are round)
static func hug_distance(kind: int) -> float:
	return 0.56 if kind == Action.HUG else 0.74


# ---------------------------------------------------------------- posing

func _process(delta: float) -> void:
	if not _ready_done:
		return
	var k := func(rate: float) -> float: return 1.0 - exp(-rate * delta)

	if first_person:
		var lay := 1 if show_head else 2     # third person: show your head again
		if _head_parts.size() > 0 and _head_parts[0].layers != lay:
			for p in _head_parts:
				p.layers = lay

	# Lying down: the whole body turns flat, head where the camera is, feet forward (-Z)
	if mode == Mode.LIE and _model:
		# On your back, middle of the head on the pillow (the player's origin), feet down the bed
		var lie := _lie()
		rotation = Vector3(PI / 2 - lie["tilt"], 0, 0)
		position = Vector3(0, lie["h"], 0) - Basis.from_euler(rotation) * Vector3(0, _fit("head_y"), 0)
	elif mode == Mode.LIE:
		rotation = Vector3(PI / 2, 0, 0)
		position = Vector3(0, eye_height, 0) - Basis.from_euler(rotation) * Vector3(0, EYE, 0)
	else:
		position = Vector3.ZERO
		rotation = Vector3.ZERO

	var want_crouch := 0.0
	if mode == Mode.STAND:
		var eye := _fit("eye") if _model else EYE
		want_crouch = clampf((eye - eye_height) / (eye * 0.62), 0.0, 1.0)
	_crouch = lerpf(_crouch, want_crouch, k.call(14.0))
	_sit = lerpf(_sit, 1.0 if mode == Mode.SIT else 0.0, k.call(10.0))

	# Body height, bounce when walking, lean
	var moving := clampf(speed / 3.0, 0.0, 1.0) if mode == Mode.STAND else 0.0
	_walk += delta * speed * 5.5
	var bounce := absf(sin(_walk)) * 0.035 * moving
	body.position = Vector3(0, HIP_Y - 0.17 * _crouch + (SEAT_Y - HIP_Y) * _sit + bounce, 0)
	if _model:
		# Models: sit with the bum on the seat; crouching squashes instead of sinking into the floor
		body.position.y = HIP_Y + (SEAT_Y - _fit("bottom")) * _sit + (0.0 if _anim else bounce)
		_model.position.y = -HIP_Y
		_model.scale = Vector3(1, 1.0 - 0.3 * _crouch, _lie()["sq"] if mode == Mode.LIE else 1.0)
		_walk_w = lerpf(_walk_w, 1.0 if moving > 0.05 else 0.0, k.call(8.0))
		if _anim:
			_animate_walk(delta)
	var want_lean := 0.12 * _crouch
	if action == Action.KISS:
		want_lean = 0.1
	_lean = lerpf(_lean, want_lean, k.call(6.0))
	body.rotation.x = -_lean
	body.rotation.z = sin(_walk) * 0.06 * moving * (0.0 if _anim else 1.0)   # cute waddle

	# Head: looks up/down with the camera; tilts to one side for a hug so heads don't bump
	head.rotation.x = clampf(pitch, -0.8, 0.8) * 0.5
	var want_tilt := 0.0
	if action == Action.HUG:
		want_tilt = 0.32
	elif action == Action.KISS:
		want_tilt = 0.15
	_tilt = lerpf(_tilt, want_tilt, k.call(5.0))
	head.rotation.z = _tilt

	# Blink every few seconds
	_blink -= delta
	if _blink < -0.12:
		_blink = randf_range(2.0, 5.0)
	for e in _eyes:
		e.scale.y = 0.006 if _blink < 0.0 else 0.06

	_pose_legs(k)
	_pose_arms(k)
	_pose_model_limbs(moving)


func _pose_legs(k: Callable) -> void:
	var hip_xf := body.global_transform
	var root_xf := global_transform
	for leg in legs:
		var s: float = leg["side"]
		var hip := hip_xf * Vector3(s * 0.13, 0.02, 0.0)
		# Feet: on the floor (with a step when walking), or dangling forward when sitting
		var stride := sin(_walk) * s * 0.13 * clampf(speed / 3.0, 0.0, 1.0)
		var lift := maxf(0.0, cos(_walk) * s) * 0.06 * clampf(speed / 3.0, 0.0, 1.0)
		var foot_stand := root_xf * Vector3(s * 0.14, 0.07 + lift, stride)
		var foot_sit := hip_xf * Vector3(s * 0.14, -0.2, -0.3)
		var foot := foot_stand.lerp(foot_sit, _sit)
		if mode == Mode.LIE:
			foot = hip_xf * Vector3(s * 0.12, -0.33, 0.04)
		var pole := root_xf.basis * Vector3(0, 0.3, -1.0)     # knees bend forward
		_solve(leg["thigh"], leg["shin"], leg["foot"], THIGH, SHIN, hip, foot, pole, true)


func _pose_arms(k: Callable) -> void:
	var hip_xf := body.global_transform
	var to_local := hip_xf.affine_inverse()
	var parent_3d := get_parent() as Node3D
	var owner_xf := parent_3d.global_transform if parent_3d else global_transform
	var flat_basis := owner_xf.basis
	var swing := sin(_walk) * 0.5 * (clampf(speed / 3.0, 0.0, 1.0) if mode == Mode.STAND else 0.0)

	var doing := action != Action.NONE
	if (action == Action.HOLD or action == Action.HUG_BOB) and hold_node == null:
		doing = false
	if (action == Action.HUG or action == Action.KISS) and partner == null:
		doing = false
	_act = lerpf(_act, 1.0 if doing else 0.0, k.call(8.0))

	for i in 2:
		var arm: Dictionary = arms[i]
		var s: float = arm["side"]
		# Relaxed: little arms out by your sides, swinging when you walk; on your lap when sitting
		var relaxed := Vector3(s * 0.4, 0.33, swing * s * 0.18)
		relaxed = relaxed.lerp(Vector3(s * 0.2, 0.25, -0.25), _sit)
		if mode == Mode.LIE:
			relaxed = Vector3(s * 0.2, 0.36, -0.12)     # tucked in, hands on your tummy
		var pole_local := Vector3(s * 0.5, -0.6, 0.6)
		var target_local := relaxed
		if doing:
			var target := Vector3.ZERO
			var pole := Vector3(s, -0.8, 0.2)
			match action:
				Action.HOLD:
					var c := hold_node.global_transform * Vector3(0, 0.105, 0)
					target = c + flat_basis.x * s * 0.1
				Action.HUG_BOB:
					var c := hold_node.global_transform * Vector3(0, 0.105, 0)
					target = c - flat_basis.z * 0.06 + flat_basis.x * s * 0.04 + Vector3(0, s * 0.03, 0)
					pole = Vector3(s, -0.4, 0.0)
				Action.HUG, Action.KISS:
					var mine := chest_global()
					var theirs: Vector3 = partner.chest_global()
					var d := theirs - mine
					d.y = 0
					d = d.normalized() if d.length() > 0.01 else -flat_basis.z
					var right := d.cross(Vector3.UP)
					if action == Action.HUG:
						target = theirs - right * s * 0.3
					else:
						target = theirs - Vector3(0, 0.12, 0) - right * s * 0.25 - d * 0.05
					pole = Vector3(s, -0.2, 0.3)
			_arm_target[i] = target
			target_local = relaxed.lerp(to_local * target, _act)
			pole_local = pole_local.lerp(to_local.basis * pole, _act)
		_hands_local[i] = (_hands_local[i] as Vector3).lerp(target_local, k.call(20.0))
		var shoulder := hip_xf * Vector3(s * SHOULDER.x, SHOULDER.y, SHOULDER.z)
		_solve(arm["upper"], arm["fore"], arm["hand"], UPPER_ARM, FOREARM, shoulder,
			hip_xf * _hands_local[i], hip_xf.basis * pole_local, false)


func _solve(upper: Node3D, fore: Node3D, end: Node3D, a: float, b: float,
		start: Vector3, target: Vector3, pole: Vector3, keep_end_flat: bool) -> void:
	# Two-bone IK: put the joint where both bones reach, bending toward `pole`
	var to := target - start
	var length := to.length()
	var dir := to / length if length > 0.0001 else Vector3.DOWN
	var d := clampf(length, 0.04, a + b - 0.002)
	var cos_a := clampf((a * a + d * d - b * b) / (2.0 * a * d), -1.0, 1.0)
	var sin_a := sqrt(1.0 - cos_a * cos_a)
	var p := pole - dir * pole.dot(dir)
	if p.length() < 0.001:
		p = dir.cross(Vector3.RIGHT)
		if p.length() < 0.001:
			p = dir.cross(Vector3.FORWARD)
	p = p.normalized()
	var joint := start + dir * (a * cos_a) + p * (a * sin_a)
	var tip := start + dir * d
	_place(upper, start, joint, p)
	_place(fore, joint, tip, p)
	if keep_end_flat:
		end.global_transform = Transform3D(global_basis, tip)       # feet stay level
	else:
		end.global_transform = Transform3D(fore.global_basis, tip)


func _place(node: Node3D, from: Vector3, to: Vector3, up: Vector3) -> void:
	var dir := to - from
	if dir.length() < 0.0001:
		return
	if absf(dir.normalized().dot(up.normalized())) > 0.99:
		up = Vector3.UP if absf(dir.normalized().y) < 0.9 else Vector3.FORWARD
	node.global_transform = Transform3D(Basis.looking_at(dir, up), from)


# ---------------------------------------------------------------- model arms and legs

func _animate_walk(delta: float) -> void:
	# Walk animation while moving; standing still blends back to the rest pose (a neutral
	# stand), instead of freezing wherever the walk cycle was (frame 0 is mid-stride).
	if _walk_w > 0.01:
		if not _anim.is_playing():
			_anim.play("Walk")
		_anim.speed_scale = clampf(speed / 1.5, 0.6, 2.5)
		_anim.advance(delta)
	elif _anim.is_playing():
		_anim.stop(true)
	if _walk_w >= 0.99:
		return
	for b in _skel.get_bone_count():
		var rest := _skel.get_bone_rest(b)
		var rq := rest.basis.get_rotation_quaternion()
		if _walk_w <= 0.01:
			_skel.set_bone_pose_position(b, rest.origin)
			_skel.set_bone_pose_rotation(b, rq)
			_skel.set_bone_pose_scale(b, rest.basis.get_scale())
		else:
			_skel.set_bone_pose_position(b, rest.origin.lerp(_skel.get_bone_pose_position(b), _walk_w))
			_skel.set_bone_pose_rotation(b, rq.slerp(_skel.get_bone_pose_rotation(b), _walk_w))


func _limb_root(limb: Dictionary) -> Vector3:
	if limb.has("node"):
		return (limb["node"] as Node3D).global_position
	return _skel.global_transform * _skel.get_bone_global_pose(limb["bone"]).origin


## Turn a limb (from where it points now) toward `dir` (world space), by `weight` 0..1
func _aim_limb(limb: Dictionary, dir: Vector3, weight: float) -> void:
	if weight < 0.002 or dir.length() < 0.001:
		return
	if limb.has("node"):
		var n: Node3D = limb["node"]
		var par := n.get_parent() as Node3D
		var want_n := (par.global_basis.inverse() * dir).normalized()
		var cur_n := (n.quaternion * (limb["rest_dir"] as Vector3)).normalized()
		var qn := Quaternion.IDENTITY.slerp(Quaternion(cur_n, want_n), weight)
		n.quaternion = (qn * n.quaternion).normalized()
		return
	var b: int = limb["bone"]
	var g := _skel.get_bone_global_pose(b)
	var cur := _skel.get_bone_global_pose(limb["tip"]).origin - g.origin
	var want := _skel.global_basis.inverse() * dir
	if cur.length() < 0.0001 or want.length() < 0.0001:
		return
	var q := Quaternion.IDENTITY.slerp(Quaternion(cur.normalized(), want.normalized()), weight)
	var pb := _skel.get_bone_parent(b)
	var pg := _skel.get_bone_global_pose(pb) if pb >= 0 else Transform3D()
	var local := pg.basis.orthonormalized().inverse() * (Basis(q) * g.basis.orthonormalized())
	_skel.set_bone_pose_rotation(b, local.get_rotation_quaternion())


func _pose_model_limbs(moving: float) -> void:
	if _limbs.is_empty():
		return
	var bb := body.global_basis
	for limb in _limbs:
		var s: float = limb["side"]
		var arm: bool = limb["kind"] == "arm"
		if limb.has("node"):
			# p3 has no walk animation: swing the arms and legs a little as she walks
			var swing := sin(_walk) * s * moving * (-0.35 if arm else 0.55)
			(limb["node"] as Node3D).quaternion = Quaternion(Vector3.RIGHT, swing)
		if mode == Mode.LIE:
			# Arms along your sides, toward your tummy, so two people fit side by side
			if arm:
				_aim_limb(limb, bb * Vector3(s * 0.2, -1.0, -0.3), 1.0)
			continue
		if arm:
			# Bone-based idle: aim arms down and slightly out so they hang at sides, not T-pose
			if not limb.has("node"):
				var idle_w := (1.0 - _walk_w) * (1.0 - _act) * (1.0 - _sit)
				_aim_limb(limb, bb * Vector3(s * 0.3, -0.95, 0.0), idle_w)
			# Sitting: hands rest on the lap. Hugging / holding Bob: reach for them.
			_aim_limb(limb, bb * Vector3(s * 0.35, -1.0, -0.8), _sit * 0.7)
			var t = _arm_target[0 if s < 0.0 else 1]
			if t != null and _act > 0.01:
				var to: Vector3 = t - _limb_root(limb)
				_aim_limb(limb, to, _act)
		else:
			# Sitting: legs stretched out in front, resting on the seat
			_aim_limb(limb, bb * Vector3(s * 0.08, -0.12, -1.0), _sit)
