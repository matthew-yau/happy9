extends CanvasLayer
## Screens you can use: the bedroom laptop and computer, the living-room TV and computer.
## Each one is a "device" with its own web browser, its own screen in the room, its own
## speaker and an on/off state - like the real things:
##   T (looking at it, or the nearest one)  turn it on / off
##   L                                      use it: this Chrome-style window opens on it
##   L or Esc                               put it down again (it keeps playing in the room)
## The TV fills its screen with the video when you're not holding the "remote".
##
## Real web pages are drawn by gdCEF (Chromium for Godot, in res://cef_artifacts/).
## If gdCEF isn't installed or fails to start, the page area shows an "Open in Chrome"
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
	var browser = null             # GdBrowserView (gdCEF)
	var target: TextureRect        # gdCEF draws the page into this (off screen)
	var screen: MeshInstance3D     # the picture on the device in the room
	var speaker: AudioStreamPlayer3D
	var glow: OmniLight3D          # light the screen throws into the room
	var glow_energy := 0.35
	var driver := 0                # peer id of whoever's using it (main.gd keeps this)
	var seq := 0                   # goes up each time someone new takes it over
	var video := {}                # last video state read back from the page
	var page_title := ""           # the page's own title (not our messages in it)
	var _last_message := ""


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

# gdCEF (real browser) - created only if the add-on is installed
var cef: Node = null               # the GdCEF node
var cef_failed := false
var browser:                       # the active device's browser
	get:
		return active.browser if active else null
var page_view: TextureRect         # shows the active device's page in this window
var fallback_box: Control          # "Open in Chrome" message when gdCEF isn't available
var holder: Control                # off-screen parent of every device's render target
var mouse_down := false


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
		page_view.visible = true
		if active.fill_video:
			fill_screen(active, false)           # normal page while you pick something
		current_url = page_url(active)
		url_bar.text = current_url
	else:
		fallback_box.visible = true
		page_view.visible = false
		if history.is_empty():
			_go(active.home, true)
	url_bar.grab_focus()
	url_bar.select_all()


func close() -> void:
	visible = false
	url_bar.release_focus()
	page_focused = false
	Input.mouse_mode = Input.MOUSE_MODE_CAPTURED
	closed.emit()


func _start_cef() -> bool:
	# Start Chromium once, the first time any screen is used
	if cef != null:
		return true
	if cef_failed:
		return false
	var cef_class := ""
	for candidate in ["gdCEF", "GdCEF", "GDCef", "GdCef"]:   # gdCEF 0.21's DLL registers "gdCEF"
		if ClassDB.class_exists(candidate):
			cef_class = candidate
			break
	if cef_class == "":
		push_warning("gdCEF not installed - screens will open pages in your real browser")
		cef_failed = true
		return false
	cef = ClassDB.instantiate(cef_class)
	cef.name = "CEF"
	add_child(cef)
	var cache := _pick_cache_folder()
	# user_gesture_required is read here, when Chromium starts (not per browser): false lets
	# videos play without a click - the TV following someone else's video, P play/pause
	if not cef.initialize({"incognito": false, "locale": "en-US",
			"cache_path": cache, "root_cache_path": cache,
			"log_severity": "error", "user_gesture_required": false}):
		push_error("gdCEF failed to start: " + str(cef.get_error()))
		cef.queue_free()
		cef = null
		cef_failed = true
		return false
	return true


var _making := {}                  # device id -> true while its browser is being created

## Makes sure the device has a running browser (turning on a screen, or using it).
## Returns false without gdCEF.
func ensure_browser(d: Device) -> bool:
	if d.browser != null:
		return true
	if not _start_cef():
		return false
	if _making.get(d.id, false):
		while _making.get(d.id, false):
			await get_tree().process_frame
		return d.browser != null
	_making[d.id] = true
	d.target = TextureRect.new()
	d.target.name = "Target_" + d.id
	d.target.size = Vector2(PAGE_SIZE)
	d.target.custom_minimum_size = Vector2(PAGE_SIZE)
	d.target.mouse_filter = Control.MOUSE_FILTER_IGNORE
	holder.add_child(d.target)
	await get_tree().process_frame
	var b = cef.create_browser(d.home, d.target, {"javascript": true, "webgl": true, "frame_rate": 30,
		"user_gesture_required": false})   # lets synced videos start playing on their own
	_making[d.id] = false
	if b == null:
		push_error("gdCEF couldn't create a browser: " + str(cef.get_error()))
		return false
	b.name = "Browser_" + d.id
	d.browser = b
	b.connect("on_page_failed_loading", _on_page_failed)
	if b.has_method("resize"):
		b.resize(Vector2(PAGE_SIZE))
	_hook_audio(d)
	return true


var _title_timer := 0.0

## Keeps the tab title and address bar up to date with the page the active device shows
func _refresh_title() -> void:
	if browser == null:
		return
	var url: String = browser.get_url()
	current_url = url
	if not url_bar.has_focus():
		url_bar.text = url
	var title: String = active.page_title
	tab_title.text = title if title != "" else url.get_slice("://", 1).get_slice("/", 0)


func _on_page_failed(_code = 0, msg = "", _b = null, _c = null) -> void:
	push_warning("Page failed: " + str(msg))


var page_focused := false   # true after clicking the web page: keys go to the page


func _input(event: InputEvent) -> void:
	if not visible:
		return
	if event is InputEventKey:
		var typing := url_bar.has_focus() or page_focused
		if event.pressed and not event.echo and (event.physical_keycode == KEY_ESCAPE
				or (event.physical_keycode == KEY_L and not typing)):
			close()
			get_viewport().set_input_as_handled()
			return
		if page_focused and browser and not url_bar.has_focus():
			# Typing into the web page (search boxes, logins, etc.)
			browser.set_key_pressed(event.unicode if event.unicode != 0 else event.keycode,
				event.pressed, event.shift_pressed, event.alt_pressed, event.is_command_or_control_pressed())
			get_viewport().set_input_as_handled()


func _on_page_gui_input(event: InputEvent) -> void:
	# Mouse on the web page -> Chromium (the page renders at PAGE_SIZE, so scale the position)
	if browser == null:
		return
	if event is InputEventMouseButton:
		if event.pressed:
			page_focused = true
			url_bar.release_focus()
			page_touched.emit(active.id)
		match event.button_index:
			MOUSE_BUTTON_WHEEL_UP:
				if event.pressed: browser.set_mouse_wheel_vertical(2, false, false, false)
			MOUSE_BUTTON_WHEEL_DOWN:
				if event.pressed: browser.set_mouse_wheel_vertical(-2, false, false, false)
			MOUSE_BUTTON_LEFT:
				mouse_down = event.pressed
				if event.pressed: browser.set_mouse_left_down()
				else: browser.set_mouse_left_up()
			MOUSE_BUTTON_RIGHT:
				if event.pressed: browser.set_mouse_right_down()
				else: browser.set_mouse_right_up()
	elif event is InputEventMouseMotion:
		var p: Vector2 = event.position / page_view.size * Vector2(PAGE_SIZE)
		browser.set_mouse_moved(int(p.x), int(p.y))


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
		browser.load_url(url)
		page_focused = true
		url_bar.release_focus()
		return
	page_title.text = host
	page_note.text = ("The in-game browser (gdCEF) isn't running.\n"
		+ "\"Open in Chrome\" opens this page in your real browser.")


func _open_in_real_chrome() -> void:
	OS.shell_open(current_url)


func _back() -> void:
	if browser:
		page_touched.emit(active.id)
		browser.previous_page()
	elif history_pos > 0:
		history_pos -= 1
		_go(history[history_pos], false)


func _forward() -> void:
	if browser:
		page_touched.emit(active.id)
		browser.next_page()
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

	# Page area: the active device's page ...
	var page := PanelContainer.new()
	page.size_flags_vertical = Control.SIZE_EXPAND_FILL
	var page_style := _box(Color.WHITE, 0)
	page_style.set_content_margin_all(0)
	page.add_theme_stylebox_override("panel", page_style)
	window.add_child(page)
	page_view = TextureRect.new()
	page_view.expand_mode = TextureRect.EXPAND_IGNORE_SIZE
	page_view.stretch_mode = TextureRect.STRETCH_SCALE
	page_view.mouse_filter = Control.MOUSE_FILTER_STOP
	page_view.focus_mode = Control.FOCUS_CLICK
	page_view.visible = false
	page_view.gui_input.connect(_on_page_gui_input)
	page.add_child(page_view)
	# ... or, without gdCEF, a message with an "Open in Chrome" button
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
				d.browser.load_url(want)
	else:
		if visible and active == d:
			close()
		if d.browser:
			d.browser.load_url("about:blank")
		d.video = {}


func _hook_audio(d: Device) -> void:
	# gdCEF can hand the page's sound to Godot: play it from the device's speaker
	if d.speaker == null or not d.browser.has_method("set_audio_stream"):
		return
	var gen := AudioStreamGenerator.new()
	gen.mix_rate = 48000
	gen.buffer_length = 0.25
	d.speaker.stream = gen
	d.speaker.play()
	d.browser.set_audio_stream(d.speaker.get_stream_playback())


func page_url(d: Device) -> String:
	return d.browser.get_url() if d and d.browser else ""


## Open the same page as the person using the device
func load_shared(d: Device, url: String) -> void:
	if d.browser == null or url == "":
		return
	if page_url(d).split("#")[0] == url.split("#")[0]:
		return
	d.browser.load_url(url)
	if d == active:
		current_url = url
		url_bar.text = url


# The page answers by briefly putting a marked message in its title, which we read back
# (gdCEF 0.21's register_method crashes, so we can't call GDScript from the page directly).
const MARK := "@@roomgame@@"
const JS_REPORT := ("(function(){var v=document.querySelector('video');if(!v)return;"
	+ "var o=window.__rgTitle!==undefined?window.__rgTitle:document.title;window.__rgTitle=o;"
	+ "document.title='" + MARK + "'+JSON.stringify({t:v.currentTime,p:v.paused,u:location.href});"
	+ "clearTimeout(window.__rgT);window.__rgT=setTimeout(function(){document.title=o;delete window.__rgTitle;},400);})();")
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
	if d.browser:
		d.browser.execute_javascript(JS_REPORT)


func fill_screen(d: Device, fill: bool) -> void:
	if d.browser:
		d.browser.execute_javascript(JS_FILL_ON if fill else JS_FILL_OFF)


func toggle_play(d: Device) -> void:
	if d.browser:
		d.browser.execute_javascript(
			"(function(){var v=document.querySelector('video');if(!v)return;if(v.paused)v.play();else v.pause();})();")


## Seek / play / pause the page's video to match the person using the device
func apply_video_state(d: Device, t: float, paused: bool) -> void:
	if d.browser == null:
		return
	var p := "true" if paused else "false"
	d.browser.execute_javascript(("(function(){var v=document.querySelector('video');if(!v)return;"
		+ "if(Math.abs(v.currentTime-%.2f)>1.5)v.currentTime=%.2f;"
		+ "if(%s&&!v.paused)v.pause();if(!%s&&v.paused)v.play();})();") % [t, t, p, p])


func _check_title_message(d: Device) -> void:
	var title: String = d.browser.get_title()
	if not title.begins_with(MARK):
		d.page_title = title
		return
	var parsed = JSON.parse_string(title.substr(MARK.length()))
	if parsed is Dictionary and title != d._last_message:
		d._last_message = title
		d.video = parsed
		video_state.emit(d.id, parsed)


func _process(delta: float) -> void:
	for d: Device in devices.values():
		var tex: Texture2D = null
		if d.browser:
			_check_title_message(d)
			tex = d.target.texture
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
		page_view.texture = active.target.texture if active.target else null



var _cache_lock: TCPServer   # held while this copy of the game owns the main browser cache

func _pick_cache_folder() -> String:
	# Chromium can't share its cache folder between two running games (e.g. testing
	# host + guest on one PC). The first copy of the game claims a local port as a lock;
	# a second copy can't, so it uses its own folder.
	_cache_lock = TCPServer.new()
	if _cache_lock.listen(47391, "127.0.0.1") == OK:
		return "user://cef_cache"
	_cache_lock = null
	return "user://cef_cache_second"
