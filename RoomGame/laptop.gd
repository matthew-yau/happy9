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
signal put_away(id: String)                         # phone: "Put away" / "Stop watching" pressed

const HOME := "https://www.google.com"
const PAGE_SIZE := Vector2i(1280, 720)              # every browser renders at this size
const PHONE_PAGE_SIZE := Vector2i(390, 832)         # phones render a portrait, mobile-width page
## Apps on the phone's home screen: [name, icon colour, letter, page]. Chrome opens the
## browser where you left it; the others are shortcuts that open their site in Chrome.
const PHONE_APPS := [
	["Chrome", Color(0.26, 0.52, 0.96), "C", ""],
	["YouTube", Color(0.9, 0.16, 0.14), "▶", "https://m.youtube.com"],
	["Google", Color(0.2, 0.66, 0.33), "G", "https://www.google.com"],
	["Maps", Color(0.98, 0.74, 0.02), "M", "https://maps.google.com"],
	["Wikipedia", Color(0.35, 0.35, 0.38), "W", "https://en.m.wikipedia.org"],
]


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
	var shared_url := ""           # URL last set by load_shared; suppresses url_changed claim
	var sync_t := 0.0              # last received video time (re-applied after page loads)
	var sync_paused := true
	var sync_at := 0               # Time.get_ticks_msec() when sync_t arrived
	var shared_at := 0             # when load_shared last navigated (the page may still be loading)
	var actual_url := ""           # where the browser really is (CefTexture.url is only what was asked for)
	var page_title := ""           # the page's own title (not our messages in it)
	var page_size := PAGE_SIZE
	var is_phone := false          # a player's smartphone (main.gd makes one per player)
	var mine := false              # your own phone (others' phones you can only join)
	var on_home := true            # phone: showing the home screen (not the Chrome app)
	var rig: Node3D                # phone: the phone in someone's hand (shown while it's out)
	var cdp: WebSocketPeer         # phone: DevTools connection that makes its browser a phone


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
var desk_root: Control             # the big Chrome window (TV, computers, laptop)
var phone_root: Control            # the phone (home screen + Chrome app)
var phone_body: PanelContainer
var phone_home: Control            # home screen with the app icons
var phone_chrome: Control          # the Chrome app (toolbar + page)
var phone_clock: Label
var phone_big_clock: Label
var phone_away_btn: Button
var _desk_ui := {}                 # the widgets of each layout; open() picks one
var _phone_ui := {}
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


## Removes a device (a player's phone when they leave)
func remove_device(id: String) -> void:
	var d: Device = devices.get(id)
	if d == null:
		return
	if visible and active == d:
		close()
	if d.cdp:
		d.cdp.close()
	if d.cef:
		d.cef.queue_free()
	if d.rig:
		d.rig.queue_free()
	elif d.screen:
		d.screen.queue_free()
	devices.erase(id)


func open(id: String) -> void:
	if visible and active and active.id != id:
		close()
	active = devices.get(id)
	if active == null:
		return
	_use_ui(_phone_ui if active.is_phone else _desk_ui)
	desk_root.visible = not active.is_phone
	phone_root.visible = active.is_phone
	visible = true
	Input.mouse_mode = Input.MOUSE_MODE_VISIBLE
	if active.is_phone:
		if not active.mine:
			active.on_home = false               # joining a friend's phone: straight to what's on it
		device_label.text = active.title
		phone_away_btn.text = "Put away" if active.mine else "Stop watching"
		_layout_phone()
	else:
		device_label.text = ("TV remote  -  L / Esc  put it down and watch" if active.fill_video
			else "%s  -  L / Esc  close" % active.title)
	opened.emit()
	var d := active
	if await ensure_browser(d):
		if d != active or not visible:
			return                               # closed again while the browser started
		fallback_box.visible = false
		if d.is_phone:
			_show_phone_home(d.on_home)
		else:
			_attach_to_page(d)
		if d.fill_video:
			fill_screen(d, false)                # normal page while you pick something
		current_url = page_url(d)
		url_bar.text = current_url
	else:
		if d != active or not visible:
			return
		fallback_box.visible = true
		if d.is_phone:
			_show_phone_home(d.on_home)
		if history.is_empty():
			_go(d.home, true)
	if not (d.is_phone and d.on_home):
		url_bar.grab_focus()
		url_bar.select_all()


## Points url_bar / page / ... at one layout's widgets (the big window or the phone)
func _use_ui(ui: Dictionary) -> void:
	url_bar = ui["url_bar"]
	tab_title = ui["tab_title"]
	device_label = ui["device_label"]
	page_title = ui["page_title"]
	page_note = ui["page_note"]
	page = ui["page"]
	fallback_box = ui["fallback_box"]


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
	d.cef.size = Vector2(d.page_size)


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
	node.custom_minimum_size = Vector2(d.page_size)
	node.mouse_filter = Control.MOUSE_FILTER_STOP
	node.focus_mode = Control.FOCUS_CLICK
	node.set("expand_mode", TextureRect.EXPAND_IGNORE_SIZE)
	node.set("stretch_mode", TextureRect.STRETCH_SCALE)
	holder.add_child(node)
	node.position = Vector2.ZERO
	node.size = Vector2(d.page_size)
	await get_tree().process_frame
	if d.is_phone:
		await _make_mobile(d, node)              # mobile sites, phone-width pages
	d.shared_url = d.home              # suppress url_changed for initial home load
	node.set("url", d.home)
	node.connect("title_changed", func(title): _on_title_changed(d, title))
	node.connect("ipc_message", func(msg): _on_ipc_message(d, msg))
	node.connect("focus_entered", func(): page_focused = true)
	node.connect("focus_exited", func(): page_focused = false)
	if node.has_signal("url_changed"):
		node.connect("url_changed", func(new_url: String):
			d.actual_url = new_url
			# Only you clicking around in the open browser window counts as taking the device
			# over. Redirects, "/" added to an address, YouTube rewriting its own URL or playing
			# the next video happen on everyone's screen and must not steal it from the driver.
			if not (visible and active == d):
				return
			if new_url == "" or new_url.begins_with("about:") or same_page(new_url, d.shared_url):
				return
			d.shared_url = ""
			page_touched.emit(d.id))
	if node.has_signal("load_finished"):
		# load_finished(url, http_status_code): the page someone else picked has loaded -
		# jump its video to where theirs is now (the earlier seek ran before the video existed)
		node.connect("load_finished", func(_url = "", _code = 0):
			if d.sync_t > 0.0:
				var t := d.sync_t
				if not d.sync_paused:
					t += (Time.get_ticks_msec() - d.sync_at) / 1000.0
				apply_video_state(d, t, d.sync_paused))
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
	var url: String = page_url(active)
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
			_escape()
			get_viewport().set_input_as_handled()


## Esc: close the window - or, on a phone, put it away (stop watching if it's a friend's)
func _escape() -> void:
	if active and active.is_phone:
		put_away.emit(active.id)
		if visible:
			close()
	else:
		close()


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
	_build_desk_ui()
	_build_phone_ui()
	_use_ui(_desk_ui)


## Toolbar (back, forward, reload, home, address bar) + the page area, into `window`.
## Fills `ui` with the widgets.
func _build_browser(window: VBoxContainer, ui: Dictionary, compact: bool) -> void:
	var toolbar := PanelContainer.new()
	toolbar.add_theme_stylebox_override("panel", _box(Color.WHITE, 0))
	window.add_child(toolbar)
	var tools := HBoxContainer.new()
	toolbar.add_child(tools)
	tools.add_child(_button("←", _back, "Back"))
	if not compact:
		tools.add_child(_button("→", _forward, "Forward"))
	tools.add_child(_button("⟳", _reload, "Reload"))
	if not compact:
		tools.add_child(_button("⌂", _home, "Home"))
	var bar := LineEdit.new()
	bar.size_flags_horizontal = Control.SIZE_EXPAND_FILL
	bar.placeholder_text = "Search or type URL" if compact else "Search Google or type a URL"
	bar.add_theme_stylebox_override("normal", _box(Color(0.94, 0.95, 0.96), 14))
	bar.add_theme_stylebox_override("focus", _box(Color.WHITE, 14, 2, Color(0.1, 0.45, 0.95)))
	bar.add_theme_color_override("font_color", Color(0.15, 0.15, 0.17))
	bar.text_submitted.connect(func(t): _go(t))
	bar.focus_entered.connect(func(): page_focused = false)
	tools.add_child(bar)
	if compact:
		tools.add_child(_button("→", _forward, "Forward"))
	ui["url_bar"] = bar

	# Page area: the active device's CefTexture is reparented here when the window is open
	var pg := PanelContainer.new()
	pg.size_flags_vertical = Control.SIZE_EXPAND_FILL
	pg.clip_contents = true
	var page_style := _box(Color.WHITE, 0)
	page_style.set_content_margin_all(0)
	pg.add_theme_stylebox_override("panel", page_style)
	window.add_child(pg)
	ui["page"] = pg
	# Fallback: without Godot CEF, show a message with an "Open in Chrome" button
	var centre := CenterContainer.new()
	ui["fallback_box"] = centre
	pg.add_child(centre)
	var col := VBoxContainer.new()
	col.add_theme_constant_override("separation", 14)
	centre.add_child(col)
	var pt := Label.new()
	pt.horizontal_alignment = HORIZONTAL_ALIGNMENT_CENTER
	pt.add_theme_font_size_override("font_size", 22 if compact else 30)
	pt.add_theme_color_override("font_color", Color(0.2, 0.2, 0.22))
	col.add_child(pt)
	ui["page_title"] = pt
	var pn := Label.new()
	pn.horizontal_alignment = HORIZONTAL_ALIGNMENT_CENTER
	pn.autowrap_mode = TextServer.AUTOWRAP_WORD_SMART
	pn.custom_minimum_size = Vector2(260 if compact else 0, 0)
	pn.add_theme_color_override("font_color", Color(0.4, 0.42, 0.45))
	col.add_child(pn)
	ui["page_note"] = pn
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


func _build_desk_ui() -> void:
	var root := Control.new()
	root.set_anchors_preset(Control.PRESET_FULL_RECT)
	add_child(root)
	desk_root = root

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
	var tt := Label.new()
	tt.text = "New Tab"
	tt.size_flags_horizontal = Control.SIZE_EXPAND_FILL
	tt.add_theme_color_override("font_color", Color(0.2, 0.2, 0.22))
	tab_row.add_child(tt)
	_desk_ui["tab_title"] = tt
	tab_row.add_child(_button("✕", close, "Close (L or Esc)"))
	var dl := Label.new()
	dl.size_flags_horizontal = Control.SIZE_EXPAND_FILL
	dl.horizontal_alignment = HORIZONTAL_ALIGNMENT_RIGHT
	dl.add_theme_color_override("font_color", Color(0.35, 0.37, 0.4))
	strip_row.add_child(dl)
	_desk_ui["device_label"] = dl

	_build_browser(window, _desk_ui, false)


# ---------------------------------------------------------------- the phone

func _build_phone_ui() -> void:
	var root := Control.new()
	root.set_anchors_preset(Control.PRESET_FULL_RECT)
	root.visible = false
	add_child(root)
	phone_root = root

	var dim := ColorRect.new()
	dim.color = Color(0, 0, 0, 0.35)
	dim.set_anchors_preset(Control.PRESET_FULL_RECT)
	root.add_child(dim)

	phone_body = PanelContainer.new()                # the phone itself: black, rounded
	var bs := _box(Color(0.06, 0.06, 0.07), 46, 3, Color(0.32, 0.33, 0.36))
	bs.set_content_margin_all(12)
	phone_body.add_theme_stylebox_override("panel", bs)
	root.add_child(phone_body)

	var screen := PanelContainer.new()               # the glass: clips the rounded corners
	var ss := _box(Color(0.1, 0.12, 0.2), 36)
	ss.set_content_margin_all(0)
	screen.add_theme_stylebox_override("panel", ss)
	screen.clip_children = CanvasItem.CLIP_CHILDREN_AND_DRAW
	phone_body.add_child(screen)

	var col := VBoxContainer.new()
	col.add_theme_constant_override("separation", 0)
	screen.add_child(col)

	# Status bar: time - whose phone - signal / battery
	var status := PanelContainer.new()
	var sts := _box(Color(0.0, 0.0, 0.0, 0.35), 0)
	sts.content_margin_left = 26
	sts.content_margin_right = 26
	sts.content_margin_top = 8
	sts.content_margin_bottom = 6
	status.add_theme_stylebox_override("panel", sts)
	col.add_child(status)
	var srow := HBoxContainer.new()
	status.add_child(srow)
	phone_clock = Label.new()
	phone_clock.add_theme_font_size_override("font_size", 14)
	srow.add_child(phone_clock)
	var dl := Label.new()
	dl.size_flags_horizontal = Control.SIZE_EXPAND_FILL
	dl.horizontal_alignment = HORIZONTAL_ALIGNMENT_CENTER
	dl.add_theme_font_size_override("font_size", 13)
	dl.add_theme_color_override("font_color", Color(0.85, 0.87, 0.92))
	srow.add_child(dl)
	_phone_ui["device_label"] = dl
	var batt := Label.new()
	batt.text = "5G  100%"
	batt.add_theme_font_size_override("font_size", 13)
	srow.add_child(batt)

	# Content: the home screen and the Chrome app on top of each other
	var content := Control.new()
	content.size_flags_vertical = Control.SIZE_EXPAND_FILL
	col.add_child(content)

	phone_home = _build_phone_home()
	content.add_child(phone_home)

	var chrome := VBoxContainer.new()
	chrome.set_anchors_preset(Control.PRESET_FULL_RECT)
	chrome.add_theme_constant_override("separation", 0)
	chrome.visible = false
	content.add_child(chrome)
	phone_chrome = chrome
	var tab_bar := PanelContainer.new()              # the app's title (the page it's on)
	tab_bar.add_theme_stylebox_override("panel", _box(Color(0.95, 0.96, 0.97), 0))
	chrome.add_child(tab_bar)
	var tt := Label.new()
	tt.text = "New Tab"
	tt.clip_text = true
	tt.horizontal_alignment = HORIZONTAL_ALIGNMENT_CENTER
	tt.add_theme_font_size_override("font_size", 13)
	tt.add_theme_color_override("font_color", Color(0.3, 0.32, 0.35))
	tab_bar.add_child(tt)
	_phone_ui["tab_title"] = tt
	_build_browser(chrome, _phone_ui, true)

	# Bottom: home bar + put away
	var bottom := PanelContainer.new()
	var bts := _box(Color(0.0, 0.0, 0.0, 0.55), 0)
	bts.content_margin_top = 6
	bts.content_margin_bottom = 10
	bottom.add_theme_stylebox_override("panel", bts)
	col.add_child(bottom)
	var brow := HBoxContainer.new()
	brow.alignment = BoxContainer.ALIGNMENT_CENTER
	brow.add_theme_constant_override("separation", 18)
	bottom.add_child(brow)
	brow.add_child(_pill("Home", func(): _show_phone_home(true)))
	phone_away_btn = _pill("Put away", _on_put_away)
	brow.add_child(phone_away_btn)
	brow.add_child(_pill("Keep in hand", close))


func _on_put_away() -> void:
	if active:
		put_away.emit(active.id)


func _pill(text: String, cb: Callable) -> Button:
	var b := Button.new()
	b.text = text
	b.focus_mode = Control.FOCUS_NONE
	b.custom_minimum_size = Vector2(0, 28)
	b.add_theme_font_size_override("font_size", 13)
	b.add_theme_stylebox_override("normal", _box(Color(1, 1, 1, 0.16), 14))
	b.add_theme_stylebox_override("hover", _box(Color(1, 1, 1, 0.3), 14))
	b.add_theme_stylebox_override("pressed", _box(Color(1, 1, 1, 0.4), 14))
	b.add_theme_color_override("font_color", Color.WHITE)
	b.add_theme_color_override("font_hover_color", Color.WHITE)
	b.pressed.connect(cb)
	return b


func _build_phone_home() -> Control:
	var home := Control.new()
	home.set_anchors_preset(Control.PRESET_FULL_RECT)
	var bg := TextureRect.new()                      # wallpaper: a soft gradient
	var grad := Gradient.new()
	grad.set_color(0, Color(0.36, 0.3, 0.62))
	grad.set_color(1, Color(0.95, 0.56, 0.5))
	var gt := GradientTexture2D.new()
	gt.gradient = grad
	gt.fill_from = Vector2(0, 0)
	gt.fill_to = Vector2(0.4, 1)
	bg.texture = gt
	bg.expand_mode = TextureRect.EXPAND_IGNORE_SIZE
	bg.stretch_mode = TextureRect.STRETCH_SCALE
	bg.set_anchors_preset(Control.PRESET_FULL_RECT)
	home.add_child(bg)

	var col := VBoxContainer.new()
	col.set_anchors_preset(Control.PRESET_FULL_RECT)
	col.offset_left = 22
	col.offset_right = -22
	col.offset_top = 30
	col.add_theme_constant_override("separation", 30)
	home.add_child(col)
	phone_big_clock = Label.new()
	phone_big_clock.horizontal_alignment = HORIZONTAL_ALIGNMENT_CENTER
	phone_big_clock.add_theme_font_size_override("font_size", 56)
	phone_big_clock.add_theme_color_override("font_shadow_color", Color(0, 0, 0, 0.3))
	col.add_child(phone_big_clock)

	var grid := GridContainer.new()
	grid.columns = 4
	grid.add_theme_constant_override("h_separation", 14)
	grid.add_theme_constant_override("v_separation", 18)
	col.add_child(grid)
	for app in PHONE_APPS:
		grid.add_child(_app_icon(app[0], app[1], app[2], app[3]))
	return home


func _app_icon(app_name: String, color: Color, letter: String, url: String) -> Control:
	var box := VBoxContainer.new()
	box.size_flags_horizontal = Control.SIZE_EXPAND_FILL
	box.add_theme_constant_override("separation", 4)
	var b := Button.new()
	b.text = letter
	b.focus_mode = Control.FOCUS_NONE
	b.custom_minimum_size = Vector2(58, 58)
	b.size_flags_horizontal = Control.SIZE_SHRINK_CENTER
	b.add_theme_font_size_override("font_size", 26)
	var normal: StyleBoxFlat
	if app_name == "Chrome":
		# A white disc in a coloured ring, like a browser app icon
		normal = _box(Color.WHITE, 29, 9, color)
		b.add_theme_color_override("font_color", color)
		b.add_theme_color_override("font_hover_color", color)
	else:
		normal = _box(color, 15)
		b.add_theme_color_override("font_color", Color.WHITE)
		b.add_theme_color_override("font_hover_color", Color.WHITE)
	b.add_theme_stylebox_override("normal", normal)
	var hover := normal.duplicate() as StyleBoxFlat
	hover.bg_color = normal.bg_color.lightened(0.15)
	b.add_theme_stylebox_override("hover", hover)
	b.add_theme_stylebox_override("pressed", hover)
	b.pressed.connect(func(): _open_app(url))
	box.add_child(b)
	var l := Label.new()
	l.text = app_name
	l.horizontal_alignment = HORIZONTAL_ALIGNMENT_CENTER
	l.add_theme_font_size_override("font_size", 12)
	l.add_theme_color_override("font_shadow_color", Color(0, 0, 0, 0.4))
	box.add_child(l)
	return box


## Tapping an app: Chrome opens where you left it (a new tab on Google the first time);
## the others open their site in Chrome.
func _open_app(url: String) -> void:
	if active == null:
		return
	_show_phone_home(false)
	if url != "":
		_go(url)
	elif page_url(active) == "" or page_url(active) == "about:blank":
		_go(active.home)
	else:
		url_bar.grab_focus()
		url_bar.select_all()


func _show_phone_home(home: bool) -> void:
	if active == null or not active.is_phone:
		return
	active.on_home = home
	phone_home.visible = home
	phone_chrome.visible = not home
	if active.cef:
		if home:
			_detach_from_page(active)            # keeps playing (and showing in the room)
		else:
			_attach_to_page(active)
	if home:
		url_bar.release_focus()
		page_focused = false


## The phone stands upright in the middle of the window, as tall as fits
func _layout_phone() -> void:
	var vp := get_viewport().get_visible_rect().size
	var h := minf(vp.y * 0.92, 900.0)
	var w := h * 0.49
	phone_body.anchor_left = 0.5
	phone_body.anchor_right = 0.5
	phone_body.anchor_top = 0.5
	phone_body.anchor_bottom = 0.5
	phone_body.offset_left = -w / 2.0
	phone_body.offset_right = w / 2.0
	phone_body.offset_top = -h / 2.0
	phone_body.offset_bottom = h / 2.0


# ---------------------------------------------------------------- phones get mobile websites
# Godot CEF has one user agent for every browser, so a phone's browser is turned into a
# phone through Chromium's DevTools (godot_cef/debug/remote_devtools_port, 9229): it gets an
# Android Chrome user agent and a mobile viewport, so sites send their phone layouts sized to
# the phone's screen. The TVs and computers stay desktop. The connection stays open for as
# long as the phone exists (DevTools drops the emulation when it closes). If DevTools isn't
# reachable (e.g. a second copy of the game holds the port) the phone just shows desktop pages.

const ANDROID_UA := ("Mozilla/5.0 (Linux; Android 14; Pixel 8) AppleWebKit/537.36 "
	+ "(KHTML, like Gecko) Chrome/%s Mobile Safari/537.36")


func _make_mobile(d: Device, node) -> void:
	var port := int(ProjectSettings.get_setting("godot_cef/debug/remote_devtools_port", 0))
	if port <= 0:
		return
	# A unique page title to find this browser among DevTools' targets
	var tag := "rgphone-%s-%d" % [d.id, randi()]
	node.set("url", "data:text/html,<title>%s</title>" % tag)
	var deadline := Time.get_ticks_msec() + 6000
	var target := {}
	while target.is_empty() and Time.get_ticks_msec() < deadline:
		await get_tree().create_timer(0.25).timeout
		var list = await _devtools_get(port, "/json")
		if list is Array:
			for t in list:
				if t is Dictionary and t.get("title", "") == tag and t.has("webSocketDebuggerUrl"):
					target = t
	if target.is_empty():
		push_warning("Phone %s: DevTools not reachable - showing desktop pages" % d.id)
		return
	var version := "130.0.0.0"
	var info = await _devtools_get(port, "/json/version")
	if info is Dictionary and "/" in str(info.get("Browser", "")):
		version = str(info["Browser"]).get_slice("/", 1)
	var ws := WebSocketPeer.new()
	if ws.connect_to_url(target["webSocketDebuggerUrl"]) != OK:
		return
	while ws.get_ready_state() == WebSocketPeer.STATE_CONNECTING and Time.get_ticks_msec() < deadline:
		ws.poll()
		await get_tree().process_frame
	if ws.get_ready_state() != WebSocketPeer.STATE_OPEN:
		push_warning("Phone %s: couldn't connect to DevTools - showing desktop pages" % d.id)
		return
	var major := version.get_slice(".", 0)
	_cdp_send(ws, 1, "Emulation.setUserAgentOverride", {
		"userAgent": ANDROID_UA % version,
		"platform": "Linux armv8l",
		"userAgentMetadata": {
			"brands": [{"brand": "Chromium", "version": major},
				{"brand": "Google Chrome", "version": major},
				{"brand": "Not=A?Brand", "version": "99"}],
			"fullVersion": version,
			"platform": "Android", "platformVersion": "14.0.0",
			"architecture": "", "model": "Pixel 8", "mobile": true}})
	# width / height 0 = the browser's real size; mobile = honour the page's viewport tag
	_cdp_send(ws, 2, "Emulation.setDeviceMetricsOverride", {
		"width": 0, "height": 0, "deviceScaleFactor": 0, "mobile": true})
	_cdp_send(ws, 3, "Emulation.setScrollbarsHidden", {"hidden": true})
	for i in 5:                                  # let the commands go out before the first page
		ws.poll()
		await get_tree().process_frame
	d.cdp = ws


func _cdp_send(ws: WebSocketPeer, id: int, method: String, params: Dictionary) -> void:
	ws.send_text(JSON.stringify({"id": id, "method": method, "params": params}))


func _devtools_get(port: int, path: String):
	var req := HTTPRequest.new()
	req.timeout = 2.0
	add_child(req)
	if req.request("http://127.0.0.1:%d%s" % [port, path]) != OK:
		req.queue_free()
		return null
	var r: Array = await req.request_completed  # [result, code, headers, body]
	req.queue_free()
	if r[0] != HTTPRequest.RESULT_SUCCESS or r[1] != 200:
		return null
	return JSON.parse_string((r[3] as PackedByteArray).get_string_from_utf8())


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


## Same page? (ignores a trailing "/" and the #fragment, which browsers add / change themselves)
static func same_page(a: String, b: String) -> bool:
	if b == "":
		return false
	return a.split("#")[0].trim_suffix("/") == b.split("#")[0].trim_suffix("/")


func page_url(d: Device) -> String:
	if d == null or d.cef == null:
		return ""
	return d.actual_url if d.actual_url != "" else d.cef.url


## Open the same page as the person using the device
func load_shared(d: Device, url: String) -> void:
	if d.cef == null or url == "":
		return
	if same_page(page_url(d), url):
		return
	# Asked for it a moment ago and it's still loading: don't restart the load every 0.5 s.
	# (If an earlier page finished loading after it and won, this asks again.)
	if same_page(d.shared_url, url) and Time.get_ticks_msec() - d.shared_at < 4000:
		return
	d.shared_at = Time.get_ticks_msec()
	d.shared_url = url     # tells url_changed this navigation is from the network, not the user
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
	# If play() is blocked by Chromium's autoplay policy, retry muted then unmute immediately.
	d.cef.eval(("(function(){var v=document.querySelector('video');if(!v)return;"
		+ "if(Math.abs(v.currentTime-%.2f)>1.5)v.currentTime=%.2f;"
		+ "if(%s&&!v.paused){v.pause();return;}"
		+ "if(!%s&&v.paused){var r=v.play();"
		+ "if(r&&r.catch)r.catch(function(){"
		+ "v.muted=true;v.play().then(function(){v.muted=false;}).catch(function(){});});"
		+ "}})();") % [t, t, p, p])


var _title_timer := 0.0

func _process(delta: float) -> void:
	# CefTexture (native C++) consumes Escape before _input sees it; use the Input singleton
	# instead, which is updated independently of event propagation.
	if visible and Input.is_action_just_pressed("ui_cancel"):
		_escape()
		return
	for d: Device in devices.values():
		if d.cdp:
			d.cdp.poll()
			while d.cdp.get_available_packet_count() > 0:
				d.cdp.get_packet()               # DevTools replies: nothing to do with them
			if d.cdp.get_ready_state() == WebSocketPeer.STATE_CLOSED:
				d.cdp = null
		# Push audio each frame if capture is enabled
		if d.cef and d.speaker and d.speaker.playing:
			if d.cef.has_method("is_audio_capture_enabled") and d.cef.is_audio_capture_enabled():
				var pb = d.speaker.get_stream_playback()
				if pb:
					d.cef.push_audio_to_playback(pb)
		var tex: Texture2D = null
		if d.cef:
			tex = d.cef.texture
		if d.rig:
			# Your own phone in your hand hides while you're looking at it full size (it'd be
			# a second copy of the same screen behind the phone window); others still see it.
			d.rig.visible = d.on and not (d.mine and visible and active == d)
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
			if active.is_phone:
				var tm := Time.get_time_dict_from_system()
				phone_clock.text = "%d:%02d" % [tm.hour, tm.minute]
				phone_big_clock.text = phone_clock.text
				_layout_phone()
