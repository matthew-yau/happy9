extends CanvasLayer
## Start menu: your name, your character (Snoopy or Miffy) and its colour,
## then Play alone / Host / Join.
## Remembers your choices in user://profile.cfg.

signal play_solo
signal host_game
signal join_game(address: String)
signal resume_game              # Esc menu: back into the game (with any character changes)
signal leave_game               # Esc menu: back to the start menu

const COLORS := [Color(0.62, 0.86, 0.6), Color(1.0, 0.72, 0.78), Color(0.6, 0.78, 1.0),
	Color(1.0, 0.86, 0.5), Color(0.78, 0.66, 0.95), Color(1.0, 0.68, 0.5), Color(0.55, 0.9, 0.88), Color(0.95, 0.95, 0.92)]
const STYLES := {"p2": "Snoopy", "p3": "Miffy"}
const MAPS := {"home": "Home (house)", "new": "New map"}
const PROFILE := "user://profile.cfg"

var player_name := "Player"
var style := "p2"
var color: Color = COLORS[0]
var address := "127.0.0.1"
var map := "home"

var name_edit: LineEdit
var ip_edit: LineEdit
var status: Label
var _color_buttons := []
var _style_buttons := {}
var _map_buttons := {}
var paused := false             # true = showing as the in-game Esc menu
var _title: Label
var _start_box: VBoxContainer   # Play alone / Host / Join (start menu only)
var _pause_box: VBoxContainer   # Resume / Back to start menu (Esc menu only)


func _ready() -> void:
	layer = 30
	_load()
	_build()


func show_menu(message := "") -> void:
	_set_paused(false)
	visible = true
	status.text = message
	Input.mouse_mode = Input.MOUSE_MODE_VISIBLE


## The same panel as an in-game pause menu: change your name / character / colour.
func show_pause() -> void:
	_set_paused(true)
	visible = true
	status.text = ""
	Input.mouse_mode = Input.MOUSE_MODE_VISIBLE


func _set_paused(on: bool) -> void:
	paused = on
	_title.text = "Paused" if on else "Happy Nine"
	_start_box.visible = not on
	_pause_box.visible = on


## Remember the name / character / colour picked (also called when resuming).
func save_profile() -> void:
	_save()


func set_status(text: String) -> void:
	status.text = text


func _load() -> void:
	var cfg := ConfigFile.new()
	var user := OS.get_environment("USERNAME")
	if user != "":
		player_name = user
	if cfg.load(PROFILE) == OK:
		player_name = cfg.get_value("me", "name", player_name)
		style = cfg.get_value("me", "style", style)
		var default_color := COLORS[1] if style == "p3" else COLORS[0]
		color = cfg.get_value("me", "color", default_color)
		if not STYLES.has(style):
			style = "p2"
		address = cfg.get_value("me", "address", address)
		map = cfg.get_value("me", "map", map)
		if not MAPS.has(map):
			map = "home"


func _save() -> void:
	player_name = name_edit.text.strip_edges()
	if player_name == "":
		player_name = "Player"
	address = ip_edit.text.strip_edges()
	var cfg := ConfigFile.new()
	cfg.set_value("me", "name", player_name)
	cfg.set_value("me", "style", style)
	cfg.set_value("me", "color", color)
	cfg.set_value("me", "address", address)
	cfg.set_value("me", "map", map)
	cfg.save(PROFILE)


func _box(color: Color, radius := 10) -> StyleBoxFlat:
	var sb := StyleBoxFlat.new()
	sb.bg_color = color
	sb.set_corner_radius_all(radius)
	sb.set_content_margin_all(10)
	return sb


func _big_button(text: String, color: Color, cb: Callable) -> Button:
	var b := Button.new()
	b.text = text
	b.custom_minimum_size = Vector2(0, 44)
	b.add_theme_font_size_override("font_size", 18)
	b.add_theme_stylebox_override("normal", _box(color))
	b.add_theme_stylebox_override("hover", _box(color.lightened(0.15)))
	b.add_theme_stylebox_override("pressed", _box(color.darkened(0.15)))
	b.add_theme_color_override("font_color", Color.WHITE)
	b.add_theme_color_override("font_hover_color", Color.WHITE)
	b.pressed.connect(cb)
	return b


func _swatches(colors: Array, current: Color, store: Array, on_pick: Callable) -> HBoxContainer:
	var row := HBoxContainer.new()
	row.add_theme_constant_override("separation", 6)
	for c in colors:
		var b := Button.new()
		b.custom_minimum_size = Vector2(32, 32)
		b.focus_mode = Control.FOCUS_NONE
		store.append([b, c])
		b.pressed.connect(func():
			on_pick.call(c)
			_refresh_swatches(store, c))
		row.add_child(b)
	_refresh_swatches(store, current)
	return row


func _refresh_swatches(store: Array, picked: Color) -> void:
	for entry in store:
		var b: Button = entry[0]
		var c: Color = entry[1]
		var sb := _box(c, 16)
		if c.is_equal_approx(picked):
			sb.set_border_width_all(3)
			sb.border_color = Color.WHITE
		for s in ["normal", "hover", "pressed"]:
			b.add_theme_stylebox_override(s, sb)


func _label(text: String, size := 15) -> Label:
	var l := Label.new()
	l.text = text
	l.add_theme_font_size_override("font_size", size)
	l.add_theme_color_override("font_color", Color(0.85, 0.87, 0.92))
	return l


func _build() -> void:
	var dim := ColorRect.new()
	dim.color = Color(0.03, 0.03, 0.06, 0.7)
	dim.set_anchors_preset(Control.PRESET_FULL_RECT)
	add_child(dim)

	var centre := CenterContainer.new()
	centre.set_anchors_preset(Control.PRESET_FULL_RECT)
	add_child(centre)
	var panel := PanelContainer.new()
	var ps := _box(Color(0.1, 0.11, 0.15, 0.96), 16)
	ps.set_content_margin_all(26)
	panel.add_theme_stylebox_override("panel", ps)
	panel.custom_minimum_size = Vector2(420, 0)
	centre.add_child(panel)

	var col := VBoxContainer.new()
	col.add_theme_constant_override("separation", 10)
	panel.add_child(col)
	_title = _label("Happy Nine", 34)
	_title.add_theme_color_override("font_color", Color.WHITE)
	col.add_child(_title)

	col.add_child(_label("Your name"))
	name_edit = LineEdit.new()
	name_edit.text = player_name
	name_edit.max_length = 20
	col.add_child(name_edit)

	col.add_child(_label("Character"))
	var style_row := HBoxContainer.new()
	style_row.add_theme_constant_override("separation", 8)
	for id in STYLES:
		var b := Button.new()
		b.text = STYLES[id]
		b.toggle_mode = true
		b.custom_minimum_size = Vector2(110, 36)
		b.focus_mode = Control.FOCUS_NONE
		b.button_pressed = id == style
		b.pressed.connect(func():
			style = id
			color = COLORS[1] if id == "p3" else COLORS[0]
			_refresh_swatches(_color_buttons, color)
			for other in _style_buttons:
				_style_buttons[other].button_pressed = other == id)
		_style_buttons[id] = b
		style_row.add_child(b)
	col.add_child(style_row)
	col.add_child(_label("Colour (Miffy's dress)"))
	col.add_child(_swatches(COLORS, color, _color_buttons, func(c): color = c))

	col.add_child(HSeparator.new())
	_pause_box = VBoxContainer.new()
	_pause_box.add_theme_constant_override("separation", 10)
	_pause_box.visible = false
	_pause_box.add_child(_big_button("Resume  (Esc)", Color(0.2, 0.55, 0.35), func():
		_save(); resume_game.emit()))
	_pause_box.add_child(_big_button("Back to start menu", Color(0.45, 0.25, 0.28), func():
		_save(); leave_game.emit()))
	_pause_box.add_child(_big_button("Quit game", Color(0.25, 0.25, 0.28), func():
		_save(); get_tree().quit()))
	col.add_child(_pause_box)
	_start_box = VBoxContainer.new()
	_start_box.add_theme_constant_override("separation", 10)
	col.add_child(_start_box)
	col = _start_box
	col.add_child(_label("Map"))
	var map_row := HBoxContainer.new()
	map_row.add_theme_constant_override("separation", 8)
	for id in MAPS:
		var mb := Button.new()
		mb.text = MAPS[id]
		mb.toggle_mode = true
		mb.custom_minimum_size = Vector2(150, 36)
		mb.focus_mode = Control.FOCUS_NONE
		mb.button_pressed = id == map
		mb.pressed.connect(func():
			map = id
			for other in _map_buttons:
				_map_buttons[other].button_pressed = other == id)
		_map_buttons[id] = mb
		map_row.add_child(mb)
	col.add_child(map_row)
	col.add_child(_big_button("Play alone", Color(0.3, 0.32, 0.4), func():
		_save(); play_solo.emit()))
	col.add_child(_big_button("Quit", Color(0.25, 0.25, 0.28), func():
		_save(); get_tree().quit()))
	col.add_child(_big_button("Host a game", Color(0.2, 0.55, 0.35), func():
		_save(); host_game.emit()))

	col.add_child(_label("Join a friend (their Tailscale address)"))
	var join_row := HBoxContainer.new()
	ip_edit = LineEdit.new()
	ip_edit.text = address
	ip_edit.size_flags_horizontal = Control.SIZE_EXPAND_FILL
	ip_edit.placeholder_text = "e.g. 100.101.102.103"
	ip_edit.text_submitted.connect(func(_t): _save(); join_game.emit(address))
	join_row.add_child(ip_edit)
	var join := _big_button("Join", Color(0.15, 0.45, 0.9), func():
		_save(); join_game.emit(address))
	join.custom_minimum_size = Vector2(90, 40)
	join_row.add_child(join)
	col.add_child(join_row)

	status = _label("", 14)
	status.autowrap_mode = TextServer.AUTOWRAP_WORD_SMART
	status.custom_minimum_size = Vector2(360, 0)
	status.add_theme_color_override("font_color", Color(1.0, 0.8, 0.5))
	_start_box.get_parent().add_child(status)
