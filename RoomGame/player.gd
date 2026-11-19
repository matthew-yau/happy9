extends CharacterBody3D
## First-person controller: WASD/arrows move, mouse looks, Space jumps,
## Shift runs, Ctrl crouches, R respawns, Esc frees the mouse (click to grab it again).

@export var walk_speed := 3.0
@export var sprint_speed := 5.5
@export var crouch_speed := 1.5
@export var jump_velocity := 4.5          # ~1 m jump: enough to get onto the bed and desk
@export var mouse_sensitivity := 0.0025
@export var ground_accel := 14.0
@export var air_accel := 4.0
@export var start_yaw_degrees := -90.0    # start facing the window

@export var stand_eye_height := 1.05     # 4 ft tall characters
@export var crouch_eye_height := 0.7

var gravity: float = ProjectSettings.get_setting("physics/3d/default_gravity")
var spawn_point: Vector3
var spawn_yaw: float

@onready var head: Node3D = $Head
@onready var shape: CollisionShape3D = $CollisionShape3D
@onready var capsule: CapsuleShape3D = shape.shape


func _ready() -> void:
	_bind("move_forward", [KEY_W, KEY_UP])
	_bind("move_back", [KEY_S, KEY_DOWN])
	_bind("move_left", [KEY_A, KEY_LEFT])
	_bind("move_right", [KEY_D, KEY_RIGHT])
	_bind("jump", [KEY_SPACE])
	_bind("sprint", [KEY_SHIFT])
	_bind("crouch", [KEY_CTRL, KEY_C])
	_bind("respawn", [KEY_R])

	rotation.y = deg_to_rad(start_yaw_degrees)
	spawn_point = global_position
	spawn_yaw = rotation.y
	set_collision_mask_value(2, true)     # bump into other players (multiplayer)
	_make_camera_arm()


# ---------------------------------------------------------------- third person (V)

var third_person := false
var arm: SpringArm3D
const THIRD_PERSON_DISTANCE := 2.2


func _make_camera_arm() -> void:
	# Head -> SpringArm3D -> Camera3D. In first person the arm has length 0 (camera at
	# your eyes); in third person it swings back behind you and stops short of walls.
	var cam: Camera3D = $Head/Camera3D
	arm = SpringArm3D.new()
	arm.name = "CameraArm"
	var probe := SphereShape3D.new()
	probe.radius = 0.12
	arm.shape = probe
	arm.collision_mask = 1                # walls and furniture (not other players)
	arm.spring_length = 0.0
	arm.margin = 0.05
	head.add_child(arm)
	arm.add_excluded_object(get_rid())
	cam.reparent(arm, false)
	cam.position = Vector3.ZERO


func toggle_third_person() -> void:
	third_person = not third_person


func _process(delta: float) -> void:
	head.rotation.z = 0.0                 # the view is always level (no sideways tilt)
	if arm == null:
		return
	var want := THIRD_PERSON_DISTANCE if third_person else 0.0
	arm.spring_length = lerpf(arm.spring_length, want, clampf(8.0 * delta, 0.0, 1.0))
	if not third_person and arm.spring_length < 0.02:
		arm.spring_length = 0.0
	# A little above your head in third person, so you look over yourself
	# Straight behind you (centred, not over one shoulder), a little above your head
	arm.position = Vector3(0, 0.5, 0) * (arm.spring_length / THIRD_PERSON_DISTANCE)


func _bind(action: String, keys: Array) -> void:
	if not InputMap.has_action(action):
		InputMap.add_action(action)
	for k in keys:
		var ev := InputEventKey.new()
		ev.physical_keycode = k
		InputMap.action_add_event(action, ev)


func _unhandled_input(event: InputEvent) -> void:
	if input_locked or in_menu:
		return                            # laptop is open: the mouse is for the laptop
	if event is InputEventMouseMotion and Input.mouse_mode == Input.MOUSE_MODE_CAPTURED:
		if seated:
			# In a chair or in bed only your head turns, so your body stays put (under the duvet)
			head.rotation.y = clampf(head.rotation.y - event.relative.x * mouse_sensitivity,
				-SEATED_LOOK, SEATED_LOOK)
		else:
			rotate_y(-event.relative.x * mouse_sensitivity)
		# Set pitch directly (not rotate_x, which turns around the body's axis and tilts
		# the view sideways once the head is turned); the horizon never rolls.
		head.rotation = Vector3(
			clampf(head.rotation.x - event.relative.y * mouse_sensitivity, deg_to_rad(-89), deg_to_rad(89)),
			head.rotation.y, 0.0)
	elif event is InputEventMouseButton and event.pressed:
		Input.mouse_mode = Input.MOUSE_MODE_CAPTURED
	elif event.is_action_pressed("ui_cancel"):
		Input.mouse_mode = Input.MOUSE_MODE_VISIBLE


## Set by main.gd when you sit in a chair or lie in bed: no walking, lower camera,
## mouse look still works. input_locked = laptop open (no looking or walking at all).
var seated := false
const SEATED_LOOK := 1.75                 # how far you can turn your head left/right when seated
var input_locked := false
var in_menu := true                       # start menu is showing: no moving or looking
## While hugging / kissing someone: walk up to them and turn to face them (main.gd sets it)
var hug_target = null                     # Vector3 or null
var hug_distance := 0.32
@export var seated_eye_height := 1.17     # your character sits up on the chair (avatar.gd SEAT_Y)
var current_eye_height := 1.17


func sit_at(seat_position: Vector3, facing_yaw: float, eye_height := -1.0, pitch := 0.0) -> void:
	seated = true
	velocity = Vector3.ZERO
	shape.disabled = true                 # don't collide with the chair/bed we're on
	global_position = seat_position
	rotation.y = facing_yaw
	head.rotation.y = 0.0
	head.rotation.x = pitch
	current_eye_height = eye_height if eye_height >= 0.0 else seated_eye_height


## Getting up: you face `facing_yaw`, looking straight ahead (the head turn / tilt you had
## in the chair or in bed is dropped, so your view doesn't stay twisted).
func stand_at(stand_position: Vector3, facing_yaw := 0.0) -> void:
	seated = false
	rotation.y = facing_yaw
	head.rotation = Vector3.ZERO
	global_position = stand_position
	shape.disabled = false


func _physics_process(delta: float) -> void:
	if seated:
		velocity = Vector3.ZERO
		head.position.y = lerp(head.position.y, current_eye_height, clamp(10.0 * delta, 0.0, 1.0))
		return
	if input_locked or in_menu:
		velocity = Vector3.ZERO
		return
	if hug_target != null:
		_approach(delta)
		return

	if not is_on_floor():
		velocity.y -= gravity * delta

	var crouching: bool = Input.is_action_pressed("crouch")
	# Smoothly lower the camera and shrink the body when crouching
	var target_eye: float = crouch_eye_height if crouching else stand_eye_height
	head.position.y = lerp(head.position.y, target_eye, clamp(12.0 * delta, 0.0, 1.0))
	capsule.height = 0.85 if crouching else 1.25
	shape.position.y = capsule.height / 2.0

	if Input.is_action_just_pressed("jump") and is_on_floor():
		velocity.y = jump_velocity

	var input_dir: Vector2 = Input.get_vector("move_left", "move_right", "move_forward", "move_back")
	var direction: Vector3 = (transform.basis * Vector3(input_dir.x, 0, input_dir.y)).normalized()
	var speed: float = walk_speed
	if crouching:
		speed = crouch_speed
	elif Input.is_action_pressed("sprint"):
		speed = sprint_speed

	var accel: float = ground_accel if is_on_floor() else air_accel
	var t: float = clamp(accel * delta, 0.0, 1.0)
	velocity.x = lerp(velocity.x, direction.x * speed, t)
	velocity.z = lerp(velocity.z, direction.z * speed, t)

	move_and_slide()

	if global_position.y < -10.0 or Input.is_action_just_pressed("respawn"):
		global_position = spawn_point
		rotation.y = spawn_yaw
		velocity = Vector3.ZERO


func _approach(delta: float) -> void:
	# Step toward the person you're hugging and turn to face them
	if not is_on_floor():
		velocity.y -= gravity * delta
	var to: Vector3 = hug_target - global_position
	to.y = 0.0
	if to.length() > 0.01:
		rotation.y = lerp_angle(rotation.y, atan2(-to.x, -to.z), clamp(6.0 * delta, 0.0, 1.0))
	var gap: float = to.length() - hug_distance
	var v := Vector3.ZERO
	if gap > 0.0:
		v = to.normalized() * clampf(gap * 4.0, 0.0, 1.6)
	velocity.x = v.x
	velocity.z = v.z
	head.position.y = lerp(head.position.y, stand_eye_height, clamp(12.0 * delta, 0.0, 1.0))
	capsule.height = 1.25
	shape.position.y = 0.625
	move_and_slide()
