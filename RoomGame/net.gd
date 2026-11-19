extends Node
## Multiplayer: hosting / joining (ENet, port 7777), the other players in the room,
## and hug / kiss requests between players. Bob and the lights are synced in main.gd.
##
## Everyone sends their own state ~30 times a second; the host relays it to the others.

signal status_changed(text: String)

const Avatar := preload("res://avatar.gd")
const Hearts := preload("res://hearts.gd")
const PORT := 7777
const MAX_PLAYERS := 8
const SEND_RATE := 30.0

var main: Node                 # main.gd
var online := false
var my_name := "Player"
var my_style := "p2"
var my_color := Color(0.62, 0.86, 0.6)
var remotes := {}              # peer id -> remote_player.gd
var players_root: Node3D
var _send_timer := 0.0
var _status := ""


func _ready() -> void:
	players_root = Node3D.new()
	players_root.name = "Players"
	main.add_child.call_deferred(players_root)
	multiplayer.peer_connected.connect(_on_peer_connected)
	multiplayer.peer_disconnected.connect(_on_peer_disconnected)
	multiplayer.connected_to_server.connect(_on_connected)
	multiplayer.connection_failed.connect(_on_failed)
	multiplayer.server_disconnected.connect(_on_server_gone)


func my_id() -> int:
	return multiplayer.get_unique_id()


## Online AND actually talking to the others (not still "Connecting ..."): only then can we send RPCs
func connected() -> bool:
	return online and multiplayer.multiplayer_peer != null \
		and multiplayer.multiplayer_peer.get_connection_status() == MultiplayerPeer.CONNECTION_CONNECTED \
		and multiplayer.get_peers().size() > 0


func is_host() -> bool:
	return not online or multiplayer.is_server()


func status() -> String:
	return _status


func _set_status(text: String) -> void:
	_status = text
	status_changed.emit(text)


func host() -> String:
	var peer := ENetMultiplayerPeer.new()
	var err := peer.create_server(PORT, MAX_PLAYERS)
	if err != OK:
		return "Couldn't host on port %d (error %d). Is the game already hosting in another window?" % [PORT, err]
	multiplayer.multiplayer_peer = peer
	online = true
	_set_status("Hosting  -  friends join: %s" % ", ".join(local_addresses()))
	return ""


func join(address: String) -> String:
	if address.strip_edges() == "":
		return "Type your friend's Tailscale address first (100.x.x.x)."
	var peer := ENetMultiplayerPeer.new()
	var err := peer.create_client(address.strip_edges().split(" ")[0], PORT)
	if err != OK:
		return "Couldn't connect to %s (error %d)" % [address, err]
	multiplayer.multiplayer_peer = peer
	online = true
	_set_status("Connecting to %s ..." % address)
	return ""


## Tell everyone your (new) name / character / colour
func send_profile() -> void:
	if connected():
		_profile.rpc(my_name, my_style, my_color)


func leave() -> void:
	if multiplayer.multiplayer_peer:
		multiplayer.multiplayer_peer.close()
	multiplayer.multiplayer_peer = OfflineMultiplayerPeer.new()
	online = false
	for id in remotes.keys():
		_remove(id)
	_set_status("")


static func local_addresses() -> PackedStringArray:
	# Tailscale gives every device a 100.64.x.x - 100.127.x.x address that works from anywhere:
	# if there is one, that's the only address worth telling your friend.
	var ts := PackedStringArray()
	for a in IP.get_local_addresses():
		var p := a.split(".")
		if p.size() == 4 and p[0] == "100" and int(p[1]) >= 64 and int(p[1]) <= 127:
			ts.append("%s (Tailscale)" % a)
	if not ts.is_empty():
		return ts
	var out := PackedStringArray()
	for a in IP.get_local_addresses():
		if a.count(".") == 3 and not a.begins_with("127.") and not a.begins_with("169.254."):
			out.append(a)
	if out.is_empty():
		out.append("127.0.0.1")
	return out


# ---------------------------------------------------------------- connection events

func _on_peer_connected(id: int) -> void:
	_profile.rpc_id(id, my_name, my_style, my_color)
	main.send_my_phone_to(id)
	if multiplayer.is_server():
		main.send_world_to(id)
	_update_count()


func _on_peer_disconnected(id: int) -> void:
	main._party_driver_left(id)
	_remove(id)
	if multiplayer.is_server():
		main.on_player_left(id)
	_update_count()


func _on_connected() -> void:
	main.on_joined_host()
	_update_count()


func _on_failed() -> void:
	leave()
	main.on_connection_lost("Couldn't connect. Check: correct address? friend clicked Host? Tailscale on for both? On Mac: System Settings → Network → Firewall → allow the game. On Windows: Windows Firewall → allow the game (Private AND Public).")


func _on_server_gone() -> void:
	leave()
	main.on_connection_lost("The host left the game.")


func _update_count() -> void:
	if not online:
		return
	var n := remotes.size() + 1
	if multiplayer.is_server():
		_set_status("Hosting (%d in the room)  -  friends join: %s" % [n, ", ".join(local_addresses())])
	else:
		_set_status("Online (%d in the room)" % n)


func _remove(id: int) -> void:
	if remotes.has(id):
		main.on_remote_removed(id)
		remotes[id].queue_free()
		remotes.erase(id)


# ---------------------------------------------------------------- player state

@rpc("any_peer", "call_remote", "reliable")
func _profile(player_name: String, style: String, color: Color) -> void:
	var id := multiplayer.get_remote_sender_id()
	if not remotes.has(id):
		var rp: Node3D = preload("res://remote_player.gd").new()
		players_root.add_child(rp)
		remotes[id] = rp
	remotes[id].setup(id, player_name.substr(0, 20), style if style in Avatar.STYLES else "p2", color)
	main.on_remote_profile(id, remotes[id])
	_update_count()


@rpc("any_peer", "call_remote", "unreliable_ordered")
func _state(s: Array) -> void:
	var id := multiplayer.get_remote_sender_id()
	if remotes.has(id) and s.size() == 8:
		remotes[id].apply_state(s)


func avatar_for(id: int) -> Avatar:
	if id == my_id():
		return main.my_avatar
	if remotes.has(id):
		return remotes[id].avatar
	return null


func name_for(id: int) -> String:
	return remotes[id].display_name if remotes.has(id) else "them"


func _process(_delta: float) -> void:
	# Who is everyone hugging / holding (so their arms reach the right thing)
	for id in remotes:
		var rp = remotes[id]
		if rp.avatar == null:
			continue
		rp.avatar.partner = avatar_for(rp.partner_id) if rp.partner_id != 0 else null
		rp.avatar.hold_node = main.bear if main.bob_holder == id else null


func _physics_process(delta: float) -> void:
	if not connected():
		return
	_send_timer += delta
	if _send_timer >= 1.0 / SEND_RATE:
		_send_timer = 0.0
		_state.rpc(main.local_state())


## Ids of the other players lying in bed
func lying_ids() -> Array:
	var ids := []
	for id in remotes:
		if remotes[id].mode == Avatar.Mode.LIE and remotes[id].avatar:
			ids.append(id)
	return ids


func anyone_lying() -> bool:
	for id in remotes:
		if remotes[id].mode == Avatar.Mode.LIE:
			return true
	return false


# ---------------------------------------------------------------- hugs and kisses

func request_interaction(target: int, kind: int) -> void:
	_interaction_request.rpc_id(target, kind)


@rpc("any_peer", "call_remote", "reliable")
func _interaction_request(kind: int) -> void:
	var from := multiplayer.get_remote_sender_id()
	if not main.begin_interaction(kind, from, false):
		_interaction_declined.rpc_id(from)


@rpc("any_peer", "call_remote", "reliable")
func _interaction_declined() -> void:
	main.end_interaction("%s is busy right now" % name_for(multiplayer.get_remote_sender_id()))


@rpc("any_peer", "call_local", "reliable")
func hearts(at: Vector3, seconds: float) -> void:
	Hearts.burst(main, at, seconds)
