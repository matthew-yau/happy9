extends Node3D
## Another player in the room (multiplayer). Smoothly follows the state that player sends
## ~30 times a second, and has a solid body so you can't walk through them and can
## look at them to hug / kiss.

const Avatar := preload("res://avatar.gd")

var peer_id := 0
var display_name := "Player"
var avatar: Avatar
var label: Label3D
var shape: CollisionShape3D
var partner_id := 0
var action := 0
var mode := 0

var _target_pos := Vector3.ZERO
var _target_yaw := 0.0
var _has_state := false


func setup(id: int, player_name: String, style: String, color: Color) -> void:
	peer_id = id
	display_name = player_name
	name = "Player_%d" % id
	if avatar != null and (avatar.style != style or not avatar.color.is_equal_approx(color)):
		# They changed character in their Esc menu: swap the model (state follows in ~1/30 s)
		var old := avatar
		avatar = Avatar.new()
		avatar.style = style
		avatar.color = color
		add_child(avatar)
		avatar.mode = old.mode
		avatar.eye_height = old.eye_height
		old.queue_free()
	if avatar == null:
		avatar = Avatar.new()
		avatar.style = style
		avatar.color = color
		add_child(avatar)

		var body := AnimatableBody3D.new()
		body.sync_to_physics = false
		body.collision_layer = 2          # layer 2 = players (the camera ray still sees it)
		body.collision_mask = 0
		body.set_meta("peer_id", id)
		shape = CollisionShape3D.new()
		var cap := CapsuleShape3D.new()
		cap.radius = 0.25
		cap.height = 1.25
		shape.shape = cap
		shape.position.y = 0.625
		body.add_child(shape)
		add_child(body)

		label = Label3D.new()
		label.billboard = BaseMaterial3D.BILLBOARD_ENABLED
		label.font_size = 36
		label.pixel_size = 0.004
		label.outline_size = 10
		label.position.y = 2.05
		label.no_depth_test = false
		add_child(label)
	label.text = player_name


func apply_state(s: Array) -> void:
	# [position, yaw, pitch, eye height, mode, speed, action, partner id]
	_target_pos = s[0]
	_target_yaw = s[1]
	avatar.pitch = s[2]
	avatar.eye_height = s[3]
	mode = s[4]
	avatar.mode = mode
	avatar.speed = s[5]
	action = s[6]
	avatar.action = action
	partner_id = s[7]
	if not _has_state or global_position.distance_to(_target_pos) > 2.0:
		global_position = _target_pos    # first update, or a jump (respawn / sitting down)
		rotation.y = _target_yaw
	_has_state = true


func _physics_process(delta: float) -> void:
	if not _has_state:
		visible = false
		return
	visible = true
	var t := 1.0 - exp(-15.0 * delta)
	global_position = global_position.lerp(_target_pos, t)
	rotation.y = lerp_angle(rotation.y, _target_yaw, t)
	shape.disabled = mode != Avatar.Mode.STAND or action == Avatar.Action.HUG or action == Avatar.Action.KISS
	label.position.y = 1.45 if mode == Avatar.Mode.STAND else (1.6 if mode == Avatar.Mode.SIT else 0.75)
