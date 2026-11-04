extends Node3D

const Robot = preload("res://robot.gd")
var camera := Camera3D.new()
var pieces := Node3D.new()
var markers := Node3D.new()
var http := HTTPRequest.new()
var state: Dictionary = {}
var selected: int = -1
var busy := false
var yaw := 0.40
var pitch := 0.82
var distance := 13.0
var endpoint := "http://127.0.0.1:8765"
var status := Label.new()
var detail := Label.new()
var log_text := RichTextLabel.new()
var claim_button: Button
var promotion := AcceptDialog.new()
var reset_dialog := ConfirmationDialog.new()
var pending_moves: Array = []
var smoke := false
var capture := false
var smoke_phase := 0

func _ready() -> void:
	for arg in OS.get_cmdline_user_args():
		if arg.begins_with("--bridge-port="):
			endpoint = "http://127.0.0.1:" + arg.get_slice("=", 1)
		if arg == "--smoke":
			smoke = true
		if arg == "--capture":
			capture = true
	build_world()
	build_ui()
	add_child(pieces)
	add_child(markers)
	add_child(http)
	http.timeout = 5.0
	http.request_completed.connect(received)
	request_state()

func position_of(square: int) -> Vector3:
	return Vector3(square % 8 - 3.5, .12, 3.5 - floori(square / 8.0))

func build_world() -> void:
	var dark := Robot.material(Color("101b2c"), .65)
	var silver := Robot.material(Color("77879b"), .7)
	var cyan := Robot.material(Color("44d6ff"), .2, true)
	var orange := Robot.material(Color("ff972f"), .2, true)
	Robot.box(self, Vector3(0, -.25, 0), Vector3(8.7, .6, 8.7), dark)
	for square in range(64):
		var pos := position_of(square)
		var row := floori(square / 8.0)
		var mat := silver if (square % 8 + row) % 2 else dark
		Robot.box(self, pos - Vector3(0, .07, 0), Vector3(.985, .14, .985), mat)
		var body := StaticBody3D.new()
		body.set_meta("square", square)
		body.position = pos - Vector3(0, .07, 0)
		var collision := CollisionShape3D.new()
		var shape := BoxShape3D.new()
		shape.size = Vector3(1, .14, 1)
		collision.shape = shape
		body.add_child(collision)
		add_child(body)
	for edge in [-4.2, 4.2]:
		Robot.box(self, Vector3(edge, .12, 0), Vector3(.06, .08, 8.25), orange)
		Robot.box(self, Vector3(0, .12, edge), Vector3(8.25, .08, .06), cyan)
	for i in range(8):
		var label := Label3D.new()
		label.text = "abcdefgh"[i]
		label.position = Vector3(i - 3.5, .13, 4.18)
		label.rotation.x = -PI / 2
		label.font_size = 32
		label.pixel_size = .008
		add_child(label)
		var rank_label := Label3D.new()
		rank_label.text = str(i + 1)
		rank_label.position = Vector3(-4.18, .13, 3.5 - i)
		rank_label.rotation.x = -PI / 2
		rank_label.font_size = 32
		rank_label.pixel_size = .008
		add_child(rank_label)
	Robot.box(self, Vector3(0, -.75, 0), Vector3(200, .2, 200), Robot.material(Color("080e1b"), .25))
	# Distant towers establish depth; meshes are original procedural scenery.
	var rng := RandomNumberGenerator.new()
	rng.seed = 42
	for i in range(24):
		var angle := float(i) * TAU / 24
		var h := rng.randf_range(2.0, 7.0)
		var p := Vector3(cos(angle) * 18, h / 2 - .6, sin(angle) * 18)
		Robot.box(self, p, Vector3(1.3, h, 1.3), dark)
		Robot.box(self, p + Vector3(0, 0, -.66), Vector3(.04, h * .8, .025), cyan if i % 2 else orange)
	var environment_node := WorldEnvironment.new()
	var env := Environment.new()
	env.background_mode = Environment.BG_COLOR
	env.background_color = Color("080e1d")
	env.ambient_light_source = Environment.AMBIENT_SOURCE_COLOR
	env.ambient_light_color = Color("91b3d5")
	env.ambient_light_energy = .65
	env.tonemap_mode = Environment.TONE_MAPPER_FILMIC
	environment_node.environment = env
	add_child(environment_node)
	var sun := DirectionalLight3D.new()
	sun.rotation_degrees = Vector3(-55, -30, 0)
	sun.light_energy = 1.1
	sun.shadow_enabled = true
	add_child(sun)
	for side in [-1, 1]:
		var lamp := OmniLight3D.new()
		lamp.position = Vector3(side * 5, 3, 0)
		lamp.light_color = Color("5ddcff") if side < 0 else Color("ffa351")
		lamp.light_energy = 1.2
		lamp.omni_range = 12
		add_child(lamp)
	add_child(camera)
	camera.current = true
	camera.fov = 53
	update_camera()

func update_camera() -> void:
	# Offset the target to leave room for the right-side HUD.
	var target := Vector3(1.65 * cos(yaw), 0, -1.65 * sin(yaw))
	camera.position = target + Vector3(sin(yaw) * cos(pitch), sin(pitch), cos(yaw) * cos(pitch)) * distance
	camera.look_at(target)

func button(parent: Node, title: String, action: Callable) -> Button:
	var b := Button.new()
	b.text = title
	b.custom_minimum_size.y = 42
	b.pressed.connect(action)
	parent.add_child(b)
	return b

func build_ui() -> void:
	var layer := CanvasLayer.new()
	add_child(layer)
	var panel := PanelContainer.new()
	panel.set_anchors_and_offsets_preset(Control.PRESET_RIGHT_WIDE)
	panel.offset_left = -310
	panel.offset_right = -20
	panel.offset_top = 20
	panel.offset_bottom = -20
	var style := StyleBoxFlat.new()
	style.bg_color = Color(.035, .065, .10, .96)
	style.border_color = Color("32596d")
	style.set_border_width_all(1)
	style.set_corner_radius_all(12)
	style.content_margin_left = 18
	style.content_margin_right = 18
	style.content_margin_top = 18
	style.content_margin_bottom = 18
	panel.add_theme_stylebox_override("panel", style)
	layer.add_child(panel)
	var column := VBoxContainer.new()
	column.add_theme_constant_override("separation", 12)
	panel.add_child(column)
	var title := Label.new()
	title.text = "ROBOT CHESS\nORBITAL / 3D"
	title.add_theme_font_size_override("font_size", 25)
	column.add_child(title)
	status.text = "CONNECTING..."
	status.add_theme_color_override("font_color", Color("5bdfff"))
	status.add_theme_font_size_override("font_size", 20)
	column.add_child(status)
	detail.autowrap_mode = TextServer.AUTOWRAP_WORD_SMART
	detail.custom_minimum_size.y = 62
	column.add_child(detail)
	log_text.size_flags_vertical = Control.SIZE_EXPAND_FILL
	log_text.custom_minimum_size.y = 100
	log_text.scroll_following = true
	column.add_child(log_text)
	button(column, "NEW GAME", func(): reset_dialog.popup_centered())
	button(column, "UNDO", func(): send_action({"action": "undo"}))
	claim_button = button(column, "CLAIM DRAW", func(): send_action({"action": "claim"}))
	button(column, "FLIP CAMERA", func(): yaw += PI; update_camera())
	button(column, "RESET CAMERA", func(): yaw = .4; pitch = .82; distance = 13; update_camera())
	button(column, "RECONNECT", request_state)
	var help := Label.new()
	help.text = "Left click: select / move\nRight drag: orbit   |   Wheel: zoom\nEsc: cancel selection\nWhite = cyan / Black = orange\nLocal two-player mode"
	help.add_theme_font_size_override("font_size", 13)
	column.add_child(help)
	reset_dialog.dialog_text = "Clear the current game and start again?"
	reset_dialog.confirmed.connect(func(): send_action({"action": "reset"}))
	layer.add_child(reset_dialog)
	promotion.title = "Choose promotion"
	layer.add_child(promotion)
	promotion.get_ok_button().text = "Cancel"
	var choices := HBoxContainer.new()
	promotion.add_child(choices)
	for kind in ["q", "r", "b", "n"]:
		button(choices, {"q": "Queen", "r": "Rook", "b": "Bishop", "n": "Knight"}[kind], promote.bind(kind))

func request_state() -> void:
	if busy:
		return
	busy = true
	var error := http.request(endpoint + "/state")
	if error != OK:
		busy = false
		detail.text = "Cannot start request. Use run.bat."

func send_action(data: Dictionary) -> void:
	if busy:
		return
	busy = true
	selected = -1
	var error := http.request(endpoint + "/action", ["Content-Type: application/json"], HTTPClient.METHOD_POST, JSON.stringify(data))
	if error != OK:
		busy = false
		detail.text = "Request failed. Please reconnect."

func received(result: int, code: int, _headers: PackedStringArray, body: PackedByteArray) -> void:
	busy = false
	if result != HTTPRequest.RESULT_SUCCESS:
		status.text = "OFFLINE"
		detail.text = "Start run.bat or Python bridge, then Reconnect."
		return
	var parsed = JSON.parse_string(body.get_string_from_utf8())
	if not parsed is Dictionary:
		detail.text = "Invalid server response."
		return
	if code != 200:
		detail.text = str(parsed.get("error", "Request rejected"))
		return
	var animate: bool = not state.is_empty() and parsed.history.size() == state.history.size() + 1
	state = parsed
	status.text = state.title
	detail.text = state.detail
	claim_button.disabled = not state.claimable
	log_text.text = "MOVE HISTORY\n\n"
	var history: Array = state.history
	for i in range(0, history.size(), 2):
		log_text.text += "%d.  %s   %s\n" % [i / 2 + 1, history[i], history[i + 1] if i + 1 < history.size() else ""]
	for child in pieces.get_children():
		pieces.remove_child(child)
		child.queue_free()
	for item in state.pieces:
		var robot: Node3D = Robot.build(item.symbol, int(item.square))
		robot.position = position_of(int(item.square))
		pieces.add_child(robot)
		if animate and str(state.last).length() >= 4 and int(item.square) == square_index(str(state.last).substr(2, 2)):
			var destination := robot.position
			robot.position = position_of(square_index(str(state.last).substr(0, 2)))
			var tween := robot.create_tween()
			tween.tween_property(robot, "position", destination, .25).set_trans(Tween.TRANS_QUAD).set_ease(Tween.EASE_IN_OUT)
	show_markers()
	if smoke:
		print("BRIDGE_OK pieces=", pieces.get_child_count(), " legal=", state.legal.size())
		if smoke_phase == 0:
			smoke_phase = 1
			select_square(12)
			select_square(28)
			return
		elif smoke_phase == 1:
			assert(state.last == "e2e4" and state.turn == "black")
			smoke_phase = 2
			send_action({"action": "undo"})
			return
		else:
			assert(state.history.is_empty() and state.turn == "white")
			print("GODOT_FLOW_OK select/move/undo")
			if not capture:
				get_tree().quit()
	if capture:
		capture = false
		await get_tree().create_timer(0.8).timeout
		await RenderingServer.frame_post_draw
		var image := get_viewport().get_texture().get_image()
		var path := ProjectSettings.globalize_path("res://../.local/output/godot-3d.png")
		DirAccess.make_dir_recursive_absolute(path.get_base_dir())
		image.save_png(path)
		print("CAPTURE_OK ", path)
		get_tree().quit()

func square_name(square: int) -> String:
	return "abcdefgh"[square % 8] + str(floori(square / 8.0) + 1)

func square_index(name_text: String) -> int:
	return "abcdefgh".find(name_text[0]) + (int(name_text[1]) - 1) * 8

func show_markers() -> void:
	for child in markers.get_children():
		markers.remove_child(child)
		child.queue_free()
	if state.is_empty():
		return
	if int(state.check) >= 0:
		Robot.box(markers, position_of(int(state.check)), Vector3(.94, .018, .94), Robot.material(Color("c53247")))
	if selected < 0:
		return
	var mat := Robot.material(Color("43d9ff"), .1, true)
	Robot.cylinder(markers, position_of(selected) + Vector3(0, .02, 0), .42, .015, mat)
	var seen: Array = []
	for move in state.legal:
		if move.substr(0, 2) == square_name(selected):
			var destination := square_index(move.substr(2, 2))
			if destination not in seen:
				seen.append(destination)
				Robot.cylinder(markers, position_of(destination) + Vector3(0, .02, 0), .16, .025, mat)

func select_square(square: int) -> void:
	if busy or state.is_empty() or state.finished:
		return
	if selected == square:
		selected = -1
		show_markers()
		return
	if selected >= 0:
		var prefix := square_name(selected) + square_name(square)
		pending_moves = state.legal.filter(func(m): return m.begins_with(prefix))
		if not pending_moves.is_empty():
			if str(pending_moves[0]).length() > 4:
				promotion.popup_centered(Vector2i(390, 110))
			else:
				send_action({"action": "move", "move": pending_moves[0]})
			return
	selected = -1
	for item in state.pieces:
		if int(item.square) == square and ((item.symbol == item.symbol.to_upper()) == (state.turn == "white")):
			selected = square
	show_markers()

func promote(kind: String) -> void:
	for move in pending_moves:
		if move.ends_with(kind):
			promotion.hide()
			send_action({"action": "move", "move": move})
			return

func _unhandled_input(event: InputEvent) -> void:
	if promotion.visible or reset_dialog.visible:
		return
	if event is InputEventMouseMotion and Input.is_mouse_button_pressed(MOUSE_BUTTON_RIGHT):
		yaw -= event.relative.x * .007
		pitch = clampf(pitch + event.relative.y * .006, .35, 1.4)
		update_camera()
	if event is InputEventMouseButton and event.pressed:
		if event.button_index == MOUSE_BUTTON_WHEEL_UP:
			distance = maxf(9, distance - .7)
			update_camera()
		elif event.button_index == MOUSE_BUTTON_WHEEL_DOWN:
			distance = minf(21, distance + .7)
			update_camera()
		elif event.button_index == MOUSE_BUTTON_LEFT:
			var origin := camera.project_ray_origin(event.position)
			var ray := PhysicsRayQueryParameters3D.create(origin, origin + camera.project_ray_normal(event.position) * 100)
			var hit := get_world_3d().direct_space_state.intersect_ray(ray)
			if not hit.is_empty() and hit.collider.has_meta("square"):
				select_square(int(hit.collider.get_meta("square")))
	if event is InputEventKey and event.pressed and event.keycode == KEY_ESCAPE:
		selected = -1
		show_markers()
