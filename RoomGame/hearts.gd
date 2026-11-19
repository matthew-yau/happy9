extends Node3D
## Little pink hearts that float up and fade. Hearts.burst(parent, position, seconds)

static var _tex: ImageTexture


static func heart_texture() -> Texture2D:
	if _tex:
		return _tex
	var n := 64
	var img := Image.create(n, n, false, Image.FORMAT_RGBA8)
	for py in n:
		for px in n:
			# Classic heart curve: (x² + y² - 1)³ - x² y³ <= 0
			var u := (px + 0.5) / n * 2.7 - 1.35
			var v := (1.0 - (py + 0.5) / n) * 2.7 - 1.25
			var t := u * u + v * v - 1.0
			var f := t * t * t - u * u * v * v * v
			img.set_pixel(px, py, Color(1, 1, 1, clampf(-f * 30.0, 0.0, 1.0)))
	_tex = ImageTexture.create_from_image(img)
	return _tex


static func burst(parent: Node, at: Vector3, seconds := 2.5) -> void:
	var h: Node3D = load("res://hearts.gd").new()
	parent.add_child(h)
	h.global_position = at
	h.run(seconds)


func run(seconds: float) -> void:
	var count := int(seconds * 5.0)
	for i in count:
		_spawn_one()
		await get_tree().create_timer(seconds / count).timeout
	await get_tree().create_timer(1.8).timeout
	queue_free()


func _spawn_one() -> void:
	var quad := QuadMesh.new()
	var size := randf_range(0.06, 0.12)
	quad.size = Vector2(size, size)
	var mat := StandardMaterial3D.new()
	mat.shading_mode = BaseMaterial3D.SHADING_MODE_UNSHADED
	mat.transparency = BaseMaterial3D.TRANSPARENCY_ALPHA
	mat.billboard_mode = BaseMaterial3D.BILLBOARD_ENABLED
	mat.albedo_texture = heart_texture()
	mat.albedo_color = Color(1.0, randf_range(0.25, 0.5), randf_range(0.45, 0.6), 1.0)
	var mi := MeshInstance3D.new()
	mi.mesh = quad
	mi.material_override = mat
	mi.cast_shadow = GeometryInstance3D.SHADOW_CASTING_SETTING_OFF
	add_child(mi)
	mi.position = Vector3(randf_range(-0.15, 0.15), randf_range(-0.05, 0.1), randf_range(-0.15, 0.15))
	var tw := create_tween().set_parallel(true)
	var drift := Vector3(randf_range(-0.12, 0.12), randf_range(0.35, 0.6), randf_range(-0.12, 0.12))
	tw.tween_property(mi, "position", mi.position + drift, 1.6).set_trans(Tween.TRANS_SINE)
	tw.tween_property(mat, "albedo_color:a", 0.0, 1.6).set_ease(Tween.EASE_IN)
	tw.chain().tween_callback(mi.queue_free)
