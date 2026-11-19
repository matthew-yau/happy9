extends CanvasLayer
## Screens you can use: the bedroom laptop and computer, the living-room TV and computer.
## Each one is a "device" with its own web browser, its own screen in the room, its own
## speaker and an on/off state - like the real things:
##   T (looking at it, or the nearest one)  turn it on / off
##   L                                      use it: this Chrome-style window opens on it
##   L or Esc                               put it down again (it keeps playing in the room)
## The TV fills its screen with the video when you're not holding the "remote".
##
## Real web pages are drawn by Godot CEF (CefTexture nodes in addons/godot_cef/).
## If Godot CEF isn't installed or fails to start, the page area shows an "Open in Chrome"
## button that opens the page in your real browser instead, and the screens show a
## standby picture.

signal opened
signal closed
signal page_touched(id: String)                     # you clicked / navigated this device
signal video_state(id: String, state: Dictionary)   # answer to request_video_state(): {t, p, u}

const HOME := "https://www.google.com"
const PAGE_SIZE := Vector2i(1280, 720)              # every browser renders at this size


class Device:
	var id := ""
	var title := ""
	var home := HOME
	var fill_video := false        # TV: the video fills the whole screen
	var on := false
	var cef = null                 # CefTexture node (Godot CEF)
	var screen: MeshInstance3D     # the picture on the device in the room
	var speaker: AudioStreamPlayer3D
	var glow: OmniLight3D          # light the screen throws into the room
	var glow_energy := 0.35
	var driver := 0                # peer id of whoever's using it (main.gd keeps this)
	var seq := 0                   # goes up each time someone new takes it over
	var video := {}                # last video state read back from the page
	var page_title := ""           # the page's own title (not our messages in it)


var devices := {}                  # id -> Device
var active: Device = null          # the device this window is showing

var url_bar: LineEdit
var tab_title: Label
var device_label: Label
var page_title: Label
var page_note: Label
var current_url := HOME
var history: Array[String] = []
var history_pos := -1

# Godot CEF (real browser) - CefTexture nodes created as needed
var cef_failed := false
var browser:                       # the active device's browser (CefTexture)
	get:
		return active.cef if active else null
var page: PanelContainer           # the page area in the UI (CefTexture is reparented into here)
var fallback_box: Control          # "Open in Chrome" message when Godot CEF isn't available
var holder: Control                # off-screen parent of every device's CefTexture
var page_focused := false          # true after clicking the web page


func _ready() -> void:
	layer = 20
	visible = false
	_build_ui()


## Adds a device (main.gd calls this for each screen it finds in the room)
func add_device(id: String, title: String, screen: MeshInstance3D, speaker: AudioStreamPlayer3D,
		glow: OmniLight3D, home := HOME, fill_video := false) -> Device:
	var d := Device.new()
	d.id = id
	d.title = title
	d.home = home
	d.fill_video = fill_video
	d.screen = screen
	d.speaker = speaker
	d.glow = glow
	d.glow_energy = glow.light_energy if glow else 0.0
	devices[id] = d
	return d


func open(id: String) -> void:
	active = devices.get(id)
	if active == null:
		return
	visible = true
	Input.mouse_mode = Input.MOUSE_MODE_VISIBLE
	device_label.text = ("TV remote  -  L / Esc  put it down and watch" if active.fill_video
		else "%s  -  L / Esc  close" % active.title)
	opened.emit()
	if await ensure_browser(active):
		fallback_box.visible = false
		_attach_to_page(active)
		if active.fill_video:
			fill_screen(active, false)           # normal page while you pick something
		current_url = page_url(active)
		url_bar.text = current_url
	else:
		fallback_box.visible = true
		if history.is_empty():
			_go(active.home, true)
	url_bar.grab_focus()
	url_bar.select_all()


func close() -> void:
	if active and active.cef:
		_detach_from_page(active)
	visible = false
	url_bar.release_focus()
	page_focused = false
	Input.mouse_mode = Input.MOUSE_MODE_CAPTURED
	closed.emit()


func _attach_to_page(d: Device) -> void:
	if d.cef == null or d.cef.get_parent() == page:
		return
	d.cef.reparent(page, false)
	d.cef.set_anchors_preset(Control.PRESET_FULL_RECT)
	d.cef.offset_left = 0
	d.cef.offset_top = 0
	d.cef.offset_right = 0
	d.cef.offset_bottom = 0
	d.cef.grab_focus()


func _detach_from_page(d: Device) -> void:
	if d.cef == null or d.cef.get_parent() != page:
		return
	d.cef.reparent(holder, false)
	d.cef.set_anchors_preset(Control.PRESET_TOP_LEFT)
	d.cef.position = Vector2.ZERO
	d.cef.size = Vector2(PAGE_SIZE)


var _making := {}                  # device id -> true while its browser is being created

## Makes sure the device has a running browser (turning on a screen, or using it).
## Returns false without Godot CEF.
func ensure_browser(d: Device) -> bool:
	if d.cef != null:
		return true
	if cef_failed:
		return false
	if _making.get(d.id, false):
		while _making.get(d.id, false):
			await get_tree().process_frame
		return d.cef != null
	_making[d.id] = true
	if not ClassDB.class_exists("CefTexture"):
		push_warning("Godot CEF not installed - screens will open pages in your real browser")
		cef_failed = true
		_making[d.id] = false
		return false
	var node = ClassDB.instantiate("CefTexture")
	if node == null:
		cef_failed = true
		_making[d.id] = false
		return false
	node.name = "Browser_" + d.id
	node.custom_minimum_size = Vector2(PAGE_SIZE)
	node.mouse_filter = Control.MOUSE_FILTER_STOP
	node.focus_mode = Control.FOCUS_CLICK
	node.set("expand_mode", TextureRect.EXPAND_IGNORE_SIZE)
	node.set("stretch_mode", TextureRect.STRETCH_SCALE)
	holder.add_child(node)
	node.position = Vector2.ZERO
	node.size = Vector2(PAGE_SIZE)
	await get_tree().process_frame
	node.set("url", d.home)
	node.connect("title_changed", func(title): _on_title_changed(d, title))
	node.connect("ipc_message", func(msg): _on_ipc_message(d, msg))
	node.connect("focus_entered", func(): page_focused = true)
	node.connect("focus_exited", func(): page_focused = false)
	_hook_audio(d, node)
	d.cef = node
	_making[d.id] = false
	return true


func _on_title_changed(d: Device, title: String) -> void:
	d.page_title = title


func _on_ipc_message(d: Device, msg: String) -> void:
	var parsed = JSON.parse_string(msg)
	if parsed is Dictionary:
		d.video = parsed
		video_state.emit(d.id, parsed)


## Keeps the tab title and address bar up to date with the page the active device shows
func _refresh_title() -> void:
	if browser == null:
		return
	var url: String = browser.url
	current_url = url
	if not url_bar.has_focus():
		url_bar.text = url
	var title: String = active.page_title
	tab_title.text = title if title != "" else url.get_slice("://", 1).get_slice("/", 0)


# ---------------------------------------------------------------- browsing

func _go(text: String, add_to_history := true) -> void:
	if active:
		page_touched.emit(active.id)
	var url := _to_url(text)
	current_url = url
	url_bar.text = url
	if add_to_history:
		history = history.slice(0, history_pos + 1)
		history.append(url)
		history_pos = history.size() - 1
	_show_page(url)


func _to_url(text: String) -> String:
	var t := text.strip_edges()
	if t.is_empty():
		return active.home if active else HOME
	if t.begins_with("http://") or t.begins_with("https://"):
		return t
	if " " not in t and "." in t:
		return "https://" + t
	return "https://www.google.com/search?q=" + t.uri_encode()   # anything else = Google search


func _show_page(url: String) -> void:
	var host := url.get_slice("://", 1).get_slice("/", 0)
	tab_title.text = host if host != "" else "New Tab"
	if browser:
		browser.url = url
		page_focused = true
		url_bar.release_focus()
		if browser.get_parent() == page:
			browser.grab_focus()
		return
	page_title.text = host
	page_note.text = ("The in-game browser (Godot CEF) isn't running.\n"
		+ "\"Open in Chrome\" opens this page in your real browser.")


func _open_in_real_chrome() -> void:
	OS.shell_open(current_url)


func _back() -> void:
	if browser:
		page_touched.emit(active.id)
		browser.go_back()
	elif history_pos > 0:
		history_pos -= 1
		_go(history[history_pos], false)


func _forward() -> void:
	if browser:
		page_touched.emit(active.id)
		browser.go_forward()
	elif history_pos < history.size() - 1:
		history_pos += 1
		_go(history[history_pos], false)


func _reload() -> void:
	if browser:
		browser.reload()
	else:
		_show_page(current_url)


func _home() -> void:
	if active:
		_go(active.home)


func _input(event: InputEvent) -> void:
	if not visible:
		return
	if event is InputEventKey and event.pressed and not event.echo:
		# When a real browser (CefTexture) is running, L is a normal key in that browser;
		# only Escape should close (caught here and also in _process for when CEF consumes it).
		var typing := url_bar.has_focus() or page_focused or (active != null and active.cef != null)
		if (event.physical_keycode == KEY_ESCAPE
				or (event.physical_keycode == KEY_L and not typing)):
			close()
			get_viewport().set_input_as_handled()


# ---------------------------------------------------------------- UI

func _box(color: Color, radius := 0, border := 0, border_color := Color.TRANSPARENT) -> StyleBoxFlat:
	var sb := StyleBoxFlat.new()
	sb.bg_color = color
	sb.set_corner_radius_all(radius)
	sb.set_border_width_all(border)
	sb.border_color = border_color
	sb.content_margin_left = 8
	sb.content_margin_right = 8
	sb.content_margin_top = 4
	sb.content_margin_bottom = 4
	return sb


func _button(text: String, cb: Callable, tip := "") -> Button:
	var b := Button.new()
	b.text = text
	b.tooltip_text = tip
	b.flat = true
	b.focus_mode = Control.FOCUS_NONE
	b.custom_minimum_size = Vector2(34, 30)
	b.add_theme_color_override("font_color", Color(0.25, 0.27, 0.3))
	b.pressed.connect(cb)
	return b


func _build_ui() -> void:
	holder = Control.new()                           # render targets live here, off screen
	holder.name = "Targets"
	holder.position = Vector2(-20000, -20000)
	holder.mouse_filter = Control.MOUSE_FILTER_IGNORE
	add_child(holder)

	var root := Control.new()
	root.set_anchors_preset(Control.PRESET_FULL_RECT)
	add_child(root)

	var dim := ColorRect.new()                       # darken the room behind the window
	dim.color = Color(0, 0, 0, 0.55)
	dim.set_anchors_preset(Control.PRESET_FULL_RECT)
	root.add_child(dim)

	var bezel := PanelContainer.new()                # the screen's black bezel
	bezel.anchor_left = 0.08
	bezel.anchor_right = 0.92
	bezel.anchor_top = 0.06
	bezel.anchor_bottom = 0.94
	var bz := _box(Color(0.07, 0.07, 0.08), 18)
	bz.set_content_margin_all(14)
	bezel.add_theme_stylebox_override("panel", bz)
	root.add_child(bezel)

	var window := VBoxContainer.new()
	window.add_theme_constant_override("separation", 0)
	bezel.add_child(window)

	# Tab strip
	var strip := PanelContainer.new()
	strip.add_theme_stylebox_override("panel", _box(Color(0.87, 0.89, 0.92), 0))
	window.add_child(strip)
	var strip_row := HBoxContainer.new()
	strip.add_child(strip_row)
	var tab := PanelContainer.new()
	tab.custom_minimum_size = Vector2(220, 0)
	tab.add_theme_stylebox_override("panel", _box(Color.WHITE, 8))
	strip_row.add_child(tab)
	var tab_row := HBoxContainer.new()
	tab.add_child(tab_row)
	tab_title = Label.new()
	tab_title.text = "New Tab"
	tab_title.size_flags_horizontal = Control.SIZE_EXPAND_FILL
	tab_title.add_theme_color_override("font_color", Color(0.2, 0.2, 0.22))
	tab_row.add_child(tab_title)
	tab_row.add_child(_button("✕", close, "Close (L or Esc)"))
	device_label = Label.new()
	device_label.size_flags_horizontal = Control.SIZE_EXPAND_FILL
	device_label.horizontal_alignment = HORIZONTAL_ALIGNMENT_RIGHT
	device_label.add_theme_color_override("font_color", Color(0.35, 0.37, 0.4))
	strip_row.add_child(device_label)

	# Toolbar: back, forward, reload, home, address bar
	var toolbar := PanelContainer.new()
	toolbar.add_theme_stylebox_override("panel", _box(Color.WHITE, 0))
	window.add_child(toolbar)
	var tools := HBoxContainer.new()
	toolbar.add_child(tools)
	tools.add_child(_button("←", _back, "Back"))
	tools.add_child(_button("→", _forward, "Forward"))
	tools.add_child(_button("⟳", _reload, "Reload"))
	tools.add_child(_button("⌂", _home, "Home"))
	url_bar = LineEdit.new()
	url_bar.size_flags_horizontal = Control.SIZE_EXPAND_FILL
	url_bar.placeholder_text = "Search Google or type a URL"
	url_bar.add_theme_stylebox_override("normal", _box(Color(0.94, 0.95, 0.96), 14))
	url_bar.add_theme_stylebox_override("focus", _box(Color.WHITE, 14, 2, Color(0.1, 0.45, 0.95)))
	url_bar.add_theme_color_override("font_color", Color(0.15, 0.15, 0.17))
	url_bar.text_submitted.connect(func(t): _go(t))
	url_bar.focus_entered.connect(func(): page_focused = false)
	tools.add_child(url_bar)

	# Page area: the active device's CefTexture is reparented here when the window is open
	page = PanelContainer.new()
	page.size_flags_vertical = Control.SIZE_EXPAND_FILL
	var page_style := _box(Color.WHITE, 0)
	page_style.set_content_margin_all(0)
	page.add_theme_stylebox_override("panel", page_style)
	window.add_child(page)
	# Fallback: without Godot CEF, show a message with an "Open in Chrome" button
	var centre := CenterContainer.new()
	fallback_box = centre
	page.add_child(centre)
	var col := VBoxContainer.new()
	col.add_theme_constant_override("separation", 14)
	centre.add_child(col)
	page_title = Label.new()
	page_title.horizontal_alignment = HORIZONTAL_ALIGNMENT_CENTER
	page_title.add_theme_font_size_override("font_size", 30)
	page_title.add_theme_color_override("font_color", Color(0.2, 0.2, 0.22))
	col.add_child(page_title)
	page_note = Label.new()
	page_note.horizontal_alignment = HORIZONTAL_ALIGNMENT_CENTER
	page_note.add_theme_color_override("font_color", Color(0.4, 0.42, 0.45))
	col.add_child(page_note)
	var open_btn := Button.new()
	open_btn.text = "Open in Chrome"
	open_btn.focus_mode = Control.FOCUS_NONE
	open_btn.add_theme_stylebox_override("normal", _box(Color(0.1, 0.45, 0.95), 16))
	open_btn.add_theme_stylebox_override("hover", _box(Color(0.08, 0.38, 0.85), 16))
	open_btn.add_theme_color_override("font_color", Color.WHITE)
	open_btn.add_theme_color_override("font_hover_color", Color.WHITE)
	open_btn.pressed.connect(_open_in_real_chrome)
	var btn_row := CenterContainer.new()
	btn_row.add_child(open_btn)
	col.add_child(btn_row)


# ---------------------------------------------------------------- power, sound, the screens in the room

## Turn a device on (its browser starts on its home page, or `url`) or off (page stops)
func set_power(d: Device, on: bool, url := "") -> void:
	if d.on == on:
		return
	d.on = on
	if on:
		if await ensure_browser(d):
			if not d.on:
				return                           # switched off again while starting up
			var want := url if url != "" else d.home
			if page_url(d).split("#")[0] != want.split("#")[0]:
				d.cef.url = want
	else:
		if visible and active == d:
			close()
		if d.cef:
			d.cef.url = "about:blank"
		d.video = {}


func _hook_audio(d: Device, node) -> void:
	# Godot CEF can capture browser audio and route it through Godot's audio system.
	# We play it from the device's 3D speaker so it sounds like it's coming from that screen.
	if d.speaker == null:
		return
	if not node.has_method("is_audio_capture_enabled") or not node.is_audio_capture_enabled():
		return
	var stream = node.create_audio_stream()
	if stream == null:
		return
	d.speaker.stream = stream
	d.speaker.play()


func page_url(d: Device) -> String:
	return d.cef.url if d and d.cef else ""


## Open the same page as the person using the device
func load_shared(d: Device, url: String) -> void:
	if d.cef == null or url == "":
		return
	if page_url(d).split("#")[0] == url.split("#")[0]:
		return
	d.cef.url = url
	if d == active:
		current_url = url
		url_bar.text = url


# JS_REPORT uses IPC (window.sendIpcMessage) instead of the old title-hack.
const JS_REPORT := ("(function(){var v=document.querySelector('video');if(!v)return;"
	+ "window.sendIpcMessage(JSON.stringify({t:v.currentTime,p:v.paused,u:location.href}));"
	+ "})();")
# The TV: the video fills the screen (like a TV app going full screen), page scrolling off
# The TV: the video player fills the screen (like a TV app going full screen). On YouTube the
# whole player box goes full screen so its own layout keeps the picture the right shape.
const JS_FILL_ON := ("(function(){var v=document.querySelector('video');var s=document.getElementById('__rgtv');"
	+ "if(!v){if(s)s.remove();return;}var p=v.closest('.html5-video-player')||v;"
	+ "if(!s){s=document.createElement('style');s.id='__rgtv';(document.head||document.documentElement).appendChild(s);"
	+ "s.textContent='.__rgtvp{position:fixed!important;left:0!important;top:0!important;width:100vw!important;"
	+ "height:100vh!important;max-width:none!important;max-height:none!important;z-index:2147483647!important;"
	+ "background:#000!important;transform:none!important;margin:0!important}"
	+ ".__rgtvp .html5-video-container{position:absolute!important;left:0!important;top:0!important;"
	+ "width:100%!important;height:100%!important}"
	+ ".__rgtvp video{position:absolute!important;width:100%!important;height:100%!important;left:0!important;"
	+ "top:0!important;object-fit:contain!important}"
	+ "body *{visibility:hidden!important}.__rgtvp,.__rgtvp *{visibility:visible!important}"
	+ "html,body{overflow:hidden!important;background:#000!important}';}"
	+ "if(!p.classList.contains('__rgtvp')){document.querySelectorAll('.__rgtvp').forEach(function(e){e.classList.remove('__rgtvp')});"
	+ "p.classList.add('__rgtvp');window.dispatchEvent(new Event('resize'));}})();")
const JS_FILL_OFF := ("(function(){var s=document.getElementById('__rgtv');if(!s)return;s.remove();"
	+ "document.querySelectorAll('.__rgtvp').forEach(function(e){e.classList.remove('__rgtvp')});"
	+ "window.dispatchEvent(new Event('resize'));})();")


## Asks the page where its video is up to; the answer arrives as the video_state signal
func request_video_state(d: Device) -> void:
	if d.cef:
		d.cef.eval(JS_REPORT)


func fill_screen(d: Device, fill: bool) -> void:
	if d.cef:
		d.cef.eval(JS_FILL_ON if fill else JS_FILL_OFF)


func toggle_play(d: Device) -> void:
	if d.cef:
		d.cef.eval(
			"(function(){var v=document.querySelector('video');if(!v)return;if(v.paused)v.play();else v.pause();})();")


## Seek / play / pause the page's video to match the person using the device
func apply_video_state(d: Device, t: float, paused: bool) -> void:
	if d.cef == null:
		return
	var p := "true" if paused else "false"
	d.cef.eval(("(function(){var v=document.querySelector('video');if(!v)return;"
		+ "if(Math.abs(v.currentTime-%.2f)>1.5)v.currentTime=%.2f;"
		+ "if(%s&&!v.paused)v.pause();if(!%s&&v.paused)v.play();})();") % [t, t, p, p])


var _title_timer := 0.0

func _process(delta: float) -> void:
	# CefTexture (native C++) consumes Escape before _input sees it; use the Input singleton
	# instead, which is updated independently of event propagation.
	if visible and Input.is_action_just_pressed("ui_cancel"):
		close()
		return
	for d: Device in devices.values():
		# Push audio each frame if capture is enabled
		if d.cef and d.speaker and d.speaker.playing:
			if d.cef.has_method("is_audio_capture_enabled") and d.cef.is_audio_capture_enabled():
				var pb = d.speaker.get_stream_playback()
				if pb:
					d.cef.push_audio_to_playback(pb)
		var tex: Texture2D = null
		if d.cef:
			tex = d.cef.texture
		if d.screen:
			d.screen.visible = d.on
			if d.on:
				var m := d.screen.material_override as StandardMaterial3D
				m.albedo_texture = tex
				m.albedo_color = Color.WHITE if tex else Color(0.10, 0.16, 0.35)   # standby blue
		if d.glow:
			var want := d.glow_energy if d.on else 0.0
			d.glow.light_energy = move_toward(d.glow.light_energy, want, delta * 2.0)
			d.glow.visible = d.glow.light_energy > 0.001
	if visible and active:
		_title_timer += delta
		if _title_timer > 0.5:
			_title_timer = 0.0
			_refresh_title()
