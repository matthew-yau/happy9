extends Node3D
## A real (planar) mirror: a second camera sits at your eye reflected through the mirror's
## surface and renders through the mirror's rectangle into a texture shown on the glass.
## You see yourself (your own head is on render layer 2, which this camera does draw),
## other players and the room. It only renders while someone could be looking at it.
##
## setup(centre, normal, width, height): centre of the glass surface, normal pointing into the room.

const MIRROR_LAYER := 20          # the glass quad: hidden from the mirror's own camera
const RANGE := 7.0                # stop rendering beyond this distance
const PIXELS_PER_M := 560.0

var normal := Vector3.RIGHT
var width := 1.0
var height := 1.0
var viewport: SubViewport
var cam: Camera3D
var glass: MeshInstance3D


func setup(centre: Vector3, n: Vector3, w: float, h: float) -> void:
	normal = n.normalized()
	width = w
	height = h
	global_position = centre
	viewport = SubViewport.new()
	viewport.size = Vector2i(int(w * PIXELS_PER_M), int(h * PIXELS_PER_M))
	viewport.msaa_3d = Viewport.MSAA_2X
	viewport.render_target_update_mode = SubViewport.UPDATE_DISABLED
	add_child(viewport)
	cam = Camera3D.new()
	cam.keep_aspect = Camera3D.KEEP_HEIGHT
	cam.projection = Camera3D.PROJECTION_FRUSTUM
	cam.set_cull_mask_value(MIRROR_LAYER, false)
	viewport.add_child(cam)
	viewport.world_3d = get_world_3d()

	var quad := QuadMesh.new()
	quad.size = Vector2(w, h)
	glass = MeshInstance3D.new()
	glass.mesh = quad
	glass.layers = 0
	glass.set_layer_mask_value(MIRROR_LAYER, true)
	glass.cast_shadow = GeometryInstance3D.SHADOW_CASTING_SETTING_OFF
	var mat := StandardMaterial3D.new()
	mat.shading_mode = BaseMaterial3D.SHADING_MODE_UNSHADED
	mat.albedo_texture = viewport.get_texture()
	mat.albedo_color = Color(0.93, 0.96, 0.97)      # a faint cool tint, like real mirror glass
	mat.uv1_scale = Vector3(-1, 1, 1)               # the camera looks from behind: flip left-right
	mat.uv1_offset = Vector3(1, 0, 0)
	glass.material_override = mat
	add_child(glass)
	# the quad faces local +Z: turn it to face the room
	glass.global_basis = Basis.looking_at(-normal, Vector3.UP)
	glass.global_position = centre + normal * 0.001


func _process(_delta: float) -> void:
	if viewport == null:
		return
	var view := get_viewport().get_camera_3d()
	if view == null:
		return
	var eye := view.global_position
	var c := global_position
	var dist := (eye - c).dot(normal)          # how far in front of the glass your eye is
	if dist <= 0.02 or eye.distance_to(c) > RANGE:
		viewport.render_target_update_mode = SubViewport.UPDATE_DISABLED
		return
	viewport.render_target_update_mode = SubViewport.UPDATE_ALWAYS
	var reflected := eye - 2.0 * dist * normal
	# camera behind the glass, looking out through it into the room, square-on to the glass
	var b := Basis.looking_at(normal, Vector3.UP)
	cam.global_transform = Transform3D(b, reflected)
	var to_centre := c - reflected
	var offset := Vector2(to_centre.dot(b.x), to_centre.dot(b.y))
	cam.set_frustum(height, offset, dist + 0.004, 40.0)
