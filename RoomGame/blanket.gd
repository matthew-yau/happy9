extends MeshInstance3D
## The duvet as it looks with someone in bed: it drapes over the body (chest, hips, legs,
## a little tent over the feet) and hangs down the sides of the bed, with the top sheet
## folded back at the shoulders. main.gd shows it whenever someone is lying in bed.
##
## Everything here is in Blender coordinates (metres) to match build_room.py:
## bed X 1.05..3.02 (head at the window end), Y 0..0.98, mattress top Z 0.58, duvet top 0.63.

const HEAD_X := 2.80         # where the head lies on the pillow (also used by main.gd)
const BODY_Y := 0.49         # centre line of the bed (one person lies here)
const SIDE := 0.24           # two people: BODY_Y +- SIDE, shoulder to shoulder
const MATTRESS := 0.58
const BASE := 0.665          # flat duvet height (just above the made bed's duvet + sheet fold)
const HANG := 0.30           # how far down the sides it hangs
const X0 := 1.015            # foot end
const X1 := 2.44             # top edge, just under the chin
const Y0 := -0.015
const Y1 := 1.015
const SHEET_FOLD := 0.13     # width of the folded-back sheet band at the top

# Shape of the bump along the body (d = distance from the middle of the head toward the
# feet; avatar.gd puts the top of the head at about d = 0), as a fraction of the tummy height that avatar.gd lie_top() reports
const SHAPE := [[0.30, 0.75], [0.42, 1.0], [0.62, 0.97], [0.80, 0.8], [0.92, 0.55], [1.08, 0.0]]
const THICK := 0.035         # the duvet's own thickness on top of the body
# How wide the bump is
const WIDE := [[0.36, 0.36], [0.70, 0.33], [0.88, 0.25], [1.05, 0.21]]

var _bodies := []            # [[Blender Y of the body's middle, tummy height], ...] the mesh fits
var _key := ""


const DUVET := Color("#c9d0d6")
const SHEET := Color("#c4ae94")


static func b2g(x: float, y: float, z: float) -> Vector3:
	return Vector3(x, z, -y)


static func _curve(points: Array, d: float) -> float:
	if d <= points[0][0]:
		return points[0][1]
	for i in range(1, points.size()):
		if d <= points[i][0]:
			var t: float = (d - points[i - 1][0]) / (points[i][0] - points[i - 1][0])
			return lerpf(points[i - 1][1], points[i][1], smoothstep(0.0, 1.0, t))
	return points[-1][1]


func _height(x: float, y: float) -> float:
	var d := HEAD_X - x
	var shape := _curve(SHAPE, d)
	var wide := _curve(WIDE, d)
	var z := BASE
	for b: Array in _bodies:
		var top: float = MATTRESS + (b[1] + THICK) * shape
		var dy: float = (y - b[0]) / wide
		z = maxf(z, BASE + maxf(0.0, top - BASE) * exp(-dy * dy * dy * dy))
	return z


func _point(u: float, v: float) -> Vector3:
	# u, v in 0..1 across the sheet; the outer bands hang down over the bed's edges
	var hang_u := 0.08     # foot end hang
	var top_u := 0.07      # the top edge folds down onto the mattress
	var side_v := 0.1
	var x: float
	var foot := 0.0        # 0 = on top of the bed .. 1 = hanging all the way down
	var head := 0.0
	if u < hang_u:
		x = X0
		foot = 1.0 - u / hang_u
	elif u > 1.0 - top_u:
		x = X1
		head = (u - (1.0 - top_u)) / top_u
	else:
		x = lerpf(X0, X1, (u - hang_u) / (1.0 - hang_u - top_u))
	var y: float
	var side := 0.0
	if v < side_v:
		y = Y0
		side = 1.0 - v / side_v
	elif v > 1.0 - side_v:
		y = Y1
		side = (v - (1.0 - side_v)) / side_v
	else:
		y = lerpf(Y0, Y1, (v - side_v) / (1.0 - 2.0 * side_v))
	var z := _height(x, y)
	var hang := maxf(foot, side)
	z = lerpf(z, HANG, hang)                    # over the foot end and the sides
	z = lerpf(z, maxf(MATTRESS + 0.05, z - 0.08), head * head)  # the top edge rolls down onto your chest
	if hang > 0.0 and hang < 0.25:
		z += 0.012 * sin(hang / 0.25 * PI)      # soft rounded edge where it bends over
	return Vector3(x, y, z)


func _ready() -> void:
	var mat := StandardMaterial3D.new()
	mat.vertex_color_use_as_albedo = true
	mat.roughness = 0.95
	mat.cull_mode = BaseMaterial3D.CULL_DISABLED
	material_override = mat
	visible = false
	fit([[BODY_Y, 0.29]])


## Rebuild the duvet to drape over these bodies: [[Blender Y of the middle, tummy height above
## the mattress], ...]. Only rebuilds when something moved by a centimetre or more.
func fit(bodies: Array) -> void:
	var clean := []
	var key := ""
	for b: Array in bodies:
		var y: float = snappedf(b[0], 0.01)
		var top: float = snappedf(clampf(b[1], 0.1, 0.5), 0.01)
		clean.append([y, top])
		key += "%.2f/%.2f " % [y, top]
	if key == _key or clean.is_empty():
		return
	_key = key
	_bodies = clean
	var nu := 90
	var nv := 44
	var st := SurfaceTool.new()
	st.begin(Mesh.PRIMITIVE_TRIANGLES)
	for iu in nu + 1:
		for iv in nv + 1:
			var u := float(iu) / nu
			var v := float(iv) / nv
			var p := _point(u, v)
			var near_top := p.x > X1 - SHEET_FOLD
			st.set_color(SHEET if near_top else DUVET)
			st.set_uv(Vector2(u, v))
			st.add_vertex(b2g(p.x, p.y, p.z))
	for iu in nu:
		for iv in nv:
			var a := iu * (nv + 1) + iv
			var b := a + 1
			var c := a + (nv + 1)
			var e := c + 1
			st.add_index(a); st.add_index(c); st.add_index(b)
			st.add_index(b); st.add_index(c); st.add_index(e)
	st.generate_normals()
	mesh = st.commit()
