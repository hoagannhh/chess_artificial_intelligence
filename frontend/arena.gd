extends Node3D

const AI_ALGORITHMS = ["minimax", "alphabeta", "pvs", "mcts"]
const Piece = preload("res://chess_piece.gd")
var room := preload("res://room.gd").new()
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
var camera_pan := Vector3.ZERO
var camera_drag := 0
var endpoint := "http://127.0.0.1:8765"
var status := Label.new()
var detail := Label.new()
var log_text := RichTextLabel.new()
var claim_button: Button
var undo_button: Button
var resign_button: Button
var draw_button: Button
var notice := Label.new()
var result_dialog := AcceptDialog.new()
var resign_dialog := ConfirmationDialog.new()
var draw_dialog := ConfirmationDialog.new()
var export_dialog := FileDialog.new()
var promotion := AcceptDialog.new()
var reset_dialog := ConfirmationDialog.new()
var pending_moves: Array = []
var play_mode := OptionButton.new()
var human_side := OptionButton.new()
var human_row := HBoxContainer.new()
var ai_rows: Array[HBoxContainer] = []
var ai_step: Button
var play_hint := Label.new()
var ai_running := false
var ai_delay := 0.0
var ai_white := OptionButton.new()
var ai_black := OptionButton.new()
var ai_depth := SpinBox.new()
var ai_toggle: Button
var ai_info := Label.new()
var smoke := false
var capture := false
var capture_black := false
var smoke_phase := 0

func _ready() -> void:
	for arg in OS.get_cmdline_user_args():
		if arg.begins_with("--bridge-port="):
			endpoint = "http://127.0.0.1:" + arg.get_slice("=", 1)
		if arg == "--smoke":
			smoke = true
		if arg == "--capture-black":
			capture_black = true
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
	var dark := Piece.material(Color("786b5c"))
	var frame := Piece.material(Color("625246"))
	var silver := Piece.material(Color("a39680"))
	var border := Piece.material(Color("a89575"))
	Piece.box(self, Vector3(0, -.25, 0), Vector3(8.7, .6, 8.7), frame)
	for square in range(64):
		var pos := position_of(square)
		var row := floori(square / 8.0)
		var mat := silver if (square % 8 + row) % 2 else dark
		Piece.box(self, pos - Vector3(0, .07, 0), Vector3(.985, .14, .985), mat)
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
		Piece.box(self, Vector3(edge, .12, 0), Vector3(.035, .025, 8.25), border)
		Piece.box(self, Vector3(0, .12, edge), Vector3(8.25, .025, .035), border)
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
	add_child(room)
	var environment_node := WorldEnvironment.new()
	var env := Environment.new()
	env.background_mode = Environment.BG_COLOR
	env.background_color = Color("454a4c")
	env.ambient_light_source = Environment.AMBIENT_SOURCE_COLOR
	env.ambient_light_color = Color("e6e3dc")
	env.ambient_light_energy = .28
	env.tonemap_mode = Environment.TONE_MAPPER_FILMIC
	environment_node.environment = env
	add_child(environment_node)
	var sun := DirectionalLight3D.new()
	sun.rotation_degrees = Vector3(-55, -30, 0)
	sun.light_energy = .38
	sun.shadow_enabled = true
	add_child(sun)
	for side in [-1, 1]:
		var lamp := OmniLight3D.new()
		lamp.position = Vector3(side * 5, 3, 0)
		lamp.light_color = Color("ece9e2")
		lamp.light_energy = .12
		lamp.omni_range = 12
		add_child(lamp)
	add_child(camera)
	camera.current = true
	camera.fov = 53
	update_camera()

func update_camera() -> void:
	# Offset the target to leave room for the right-side HUD.
	var target := camera_pan + Vector3(1.65 * cos(yaw), 0, -1.65 * sin(yaw))
	camera.position = target + Vector3(sin(yaw) * cos(pitch), sin(pitch), cos(yaw) * cos(pitch)) * distance
	camera.look_at(target)

func reset_camera(view: int = 0) -> void:
	camera_pan = Vector3.ZERO
	distance = 13.0
	yaw = PI if view == 2 else 0.0
	pitch = 1.55 if view == 3 else .82
	if view == 0:
		yaw = .4
	update_camera()

func orbit_camera(delta: Vector2) -> void:
	yaw = wrapf(yaw - delta.x * .007, -PI, PI)
	pitch = clampf(pitch + delta.y * .006, .15, 1.55)
	update_camera()

func pan_camera(delta: Vector2) -> void:
	var right := Vector3(cos(yaw), 0, -sin(yaw))
	var forward := Vector3(sin(yaw), 0, cos(yaw))
	camera_pan += (-right * delta.x - forward * delta.y) * distance * .0015
	camera_pan.x = clampf(camera_pan.x, -5.0, 5.0)
	camera_pan.z = clampf(camera_pan.z, -5.0, 5.0)
	update_camera()

func camera_modal_open() -> bool:
	return promotion.visible or reset_dialog.visible or resign_dialog.visible or draw_dialog.visible or result_dialog.visible or export_dialog.visible

# Continue an already-started drag over the HUD and always catch its release.
# Starting a drag is handled by _unhandled_input so UI controls stay usable.
func _input(event: InputEvent) -> void:
	if camera_modal_open():
		camera_drag = 0
		return
	if event is InputEventMouseButton and not event.pressed:
		if event.button_index in [MOUSE_BUTTON_RIGHT, MOUSE_BUTTON_MIDDLE]:
			camera_drag = 0
	if event is InputEventMouseMotion and camera_drag != 0:
		if not Input.is_mouse_button_pressed(MOUSE_BUTTON_RIGHT) and not Input.is_mouse_button_pressed(MOUSE_BUTTON_MIDDLE):
			camera_drag = 0
			return
		if camera_drag == 2 or event.shift_pressed:
			pan_camera(event.relative)
		else:
			orbit_camera(event.relative)
		get_viewport().set_input_as_handled()

func _notification(what: int) -> void:
	if what == NOTIFICATION_APPLICATION_FOCUS_OUT:
		camera_drag = 0

func button(parent: Node, title: String, action: Callable) -> Button:
	var b := Button.new()
	b.text = title
	b.custom_minimum_size.y = 36
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
	style.bg_color = Color("303737")
	style.border_color = Color("656d68")
	style.set_border_width_all(1)
	style.set_corner_radius_all(12)
	style.content_margin_left = 18
	style.content_margin_right = 18
	style.content_margin_top = 18
	style.content_margin_bottom = 18
	panel.add_theme_stylebox_override("panel", style)
	layer.add_child(panel)
	var scroll := ScrollContainer.new()
	scroll.horizontal_scroll_mode = ScrollContainer.SCROLL_MODE_DISABLED
	panel.add_child(scroll)
	var column := VBoxContainer.new()
	column.size_flags_horizontal = Control.SIZE_EXPAND_FILL
	column.size_flags_vertical = Control.SIZE_EXPAND_FILL
	column.add_theme_constant_override("separation", 8)
	scroll.add_child(column)
	var title := Label.new()
	title.text = "CHESS STUDIO\nLOCAL / 3D"
	title.add_theme_font_size_override("font_size", 25)
	column.add_child(title)
	status.text = "CONNECTING..."
	status.add_theme_color_override("font_color", Color("cfdbc9"))
	status.add_theme_font_size_override("font_size", 20)
	column.add_child(status)
	detail.autowrap_mode = TextServer.AUTOWRAP_WORD_SMART
	detail.custom_minimum_size.y = 44
	column.add_child(detail)
	log_text.size_flags_vertical = Control.SIZE_EXPAND_FILL
	log_text.custom_minimum_size.y = 100
	log_text.scroll_following = true
	column.add_child(log_text)
	var ai_title := Label.new()
	ai_title.text = "PLAY MODE"
	column.add_child(ai_title)
	for mode_name in ["Human vs Human", "Human vs AI", "AI vs AI"]:
		play_mode.add_item(mode_name)
	column.add_child(play_mode)
	play_mode.item_selected.connect(func(_index): change_mode())
	column.add_child(human_row)
	var human_label := Label.new()
	human_label.text = "You play"
	human_row.add_child(human_label)
	human_side.add_item("White")
	human_side.add_item("Black")
	human_side.size_flags_horizontal = Control.SIZE_EXPAND_FILL
	human_row.add_child(human_side)
	human_side.item_selected.connect(func(_index): change_mode())
	play_hint.autowrap_mode = TextServer.AUTOWRAP_WORD_SMART
	play_hint.add_theme_font_size_override("font_size", 13)
	column.add_child(play_hint)
	for side in ["White", "Black"]:
		var row := HBoxContainer.new()
		ai_rows.append(row)
		column.add_child(row)
		var label := Label.new()
		label.text = side
		label.custom_minimum_size.x = 55
		row.add_child(label)
		var choice: OptionButton = ai_white if side == "White" else ai_black
		choice.add_item("Minimax")
		choice.add_item("Alpha-Beta")
		choice.add_item("PVS / NegaScout")
		choice.add_item("MCTS")
		choice.select(0 if side == "White" else 1)
		choice.size_flags_horizontal = Control.SIZE_EXPAND_FILL
		row.add_child(choice)
	var depth_row := HBoxContainer.new()
	column.add_child(depth_row)
	var depth_label := Label.new()
	depth_label.text = "Level 1-5 (1s / move)"
	depth_label.tooltip_text = "Minimax / Alpha-Beta / PVS: search depth. MCTS: rollout limit = level x 8 plies."
	depth_label.size_flags_horizontal = Control.SIZE_EXPAND_FILL
	depth_row.add_child(depth_label)
	ai_depth.min_value = 1
	ai_depth.max_value = 5
	ai_depth.step = 1
	ai_depth.value = 3
	depth_row.add_child(ai_depth)
	var ai_row := HBoxContainer.new()
	column.add_child(ai_row)
	ai_toggle = button(ai_row, "START AI", func():
		ai_running = not ai_running
		ai_toggle.text = "PAUSE AI" if ai_running else "START AI")
	ai_toggle.size_flags_horizontal = Control.SIZE_EXPAND_FILL
	ai_step = button(ai_row, "ONE MOVE", func():
		stop_ai()
		request_ai_move())
	ai_info.autowrap_mode = TextServer.AUTOWRAP_WORD_SMART
	ai_info.add_theme_font_size_override("font_size", 12)
	ai_info.text = "Start from this position. Pause after current move."
	column.add_child(ai_info)
	button(column, "NEW GAME", func(): reset_dialog.popup_centered())
	undo_button = button(column, "UNDO", undo_player_turn)
	claim_button = button(column, "CLAIM DRAW", func(): send_action({"action": "claim"}))
	var ending_row := HBoxContainer.new()
	column.add_child(ending_row)
	resign_button = button(ending_row, "RESIGN", func():
		resign_dialog.dialog_text = "Does %s resign this game?" % str(state.get("turn", "white")).to_upper()
		resign_dialog.popup_centered())
	draw_button = button(ending_row, "AGREE DRAW", func(): draw_dialog.popup_centered())
	resign_button.size_flags_horizontal = Control.SIZE_EXPAND_FILL
	draw_button.size_flags_horizontal = Control.SIZE_EXPAND_FILL
	button(column, "EXPORT PGN", func():
		if not state.is_empty():
			export_dialog.popup_centered_ratio(.65))
	button(column, "FLIP CAMERA", func(): yaw += PI; update_camera())
	var views := HBoxContainer.new()
	column.add_child(views)
	for view in [1, 2, 3]:
		var view_button := button(views, {1: "WHITE", 2: "BLACK", 3: "TOP"}[view], reset_camera.bind(view))
		view_button.size_flags_horizontal = Control.SIZE_EXPAND_FILL
	button(column, "RESET CAMERA", reset_camera)
	var finish_label := Label.new()
	finish_label.text = "TABLE FINISH"
	column.add_child(finish_label)
	var finish_choice := OptionButton.new()
	finish_choice.add_item("Modern stone / Champagne")
	finish_choice.add_item("Warm walnut")
	finish_choice.item_selected.connect(room.set_finish)
	column.add_child(finish_choice)
	button(column, "RECONNECT", request_state)
	var help := Label.new()
	help.text = "Left click: select / move\nRight drag: orbit | Wheel: zoom\nMiddle / Shift+right drag: pan\n1/2/3: White/Black/Top | R: reset\nEsc: cancel selection\nWhite = ivory / Black = charcoal"
	help.add_theme_font_size_override("font_size", 13)
	column.add_child(help)
	notice.autowrap_mode = TextServer.AUTOWRAP_WORD_SMART
	notice.add_theme_font_size_override("font_size", 12)
	notice.add_theme_color_override("font_color", Color("a7b7c9"))
	column.add_child(notice)
	result_dialog.title = "Game over"
	result_dialog.get_ok_button().text = "Review board"
	layer.add_child(result_dialog)
	resign_dialog.title = "Confirm resignation"
	resign_dialog.confirmed.connect(func(): send_action({"action": "resign"}))
	layer.add_child(resign_dialog)
	draw_dialog.title = "Draw by agreement"
	draw_dialog.dialog_text = "Both players must agree to end this game as a draw.\nDo both players agree?"
	draw_dialog.confirmed.connect(func(): send_action({"action": "agree_draw"}))
	layer.add_child(draw_dialog)
	export_dialog.title = "Export game as PGN"
	export_dialog.file_mode = FileDialog.FILE_MODE_SAVE_FILE
	export_dialog.access = FileDialog.ACCESS_FILESYSTEM
	export_dialog.filters = PackedStringArray(["*.pgn ; Chess game"])
	export_dialog.current_file = "chess-game.pgn"
	export_dialog.file_selected.connect(export_pgn)
	layer.add_child(export_dialog)
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

func human_color() -> String:
	return "white" if human_side.selected == 0 else "black"

func is_ai_turn() -> bool:
	return not state.is_empty() and (play_mode.selected == 2 or (play_mode.selected == 1 and state.turn != human_color()))

func change_mode() -> void:
	stop_ai()
	selected = -1
	show_markers()
	if play_mode.selected == 1:
		ai_running = true
		ai_toggle.text = "PAUSE AI"
		reset_camera(1 if human_side.selected == 0 else 2)
	ai_delay = .45
	update_play_controls()

func update_play_controls() -> void:
	play_mode.disabled = busy
	human_side.disabled = busy
	ai_white.disabled = busy
	ai_black.disabled = busy
	human_row.visible = play_mode.selected == 1
	for i in range(ai_rows.size()):
		ai_rows[i].visible = play_mode.selected == 2 or (play_mode.selected == 1 and i != human_side.selected)
	ai_toggle.disabled = play_mode.selected == 0 or state.is_empty() or bool(state.get("finished", false))
	ai_step.disabled = busy or not is_ai_turn() or bool(state.get("finished", false))
	if play_mode.selected == 0:
		play_hint.text = "Two players on this computer."
	elif play_mode.selected == 1:
		play_hint.text = "You: %s | AI: %s\n%s" % [human_color().to_upper(), "BLACK" if human_side.selected == 0 else "WHITE", "AI turn" if is_ai_turn() else "Your turn"]
		if not ai_running and not bool(state.get("finished", false)):
			play_hint.text += " — AI paused"
	else:
		play_hint.text = "AI vs AI — Start to continue this position."
	if not state.is_empty():
		resign_button.disabled = busy or state.finished or (play_mode.selected == 1 and is_ai_turn())
		claim_button.disabled = busy or not state.claimable or (play_mode.selected == 1 and is_ai_turn())
		draw_button.disabled = busy or state.finished or play_mode.selected == 1
		undo_button.disabled = busy or not state.can_undo

func undo_player_turn() -> void:
	var count := 1
	if play_mode.selected == 1 and not state.is_empty() and state.turn == human_color() and state.history.size() >= 2:
		count = 2
	send_action({"action": "undo", "count": count})

func stop_ai() -> void:
	ai_running = false
	ai_toggle.text = "START AI"

func request_ai_move() -> void:
	if busy or state.is_empty() or state.finished or not is_ai_turn() or camera_modal_open():
		return
	var choice: OptionButton = ai_white if state.turn == "white" else ai_black
	ai_info.text = str(state.turn).to_upper() + " thinking..."
	send_action({"action": "ai_move", "algorithm": AI_ALGORITHMS[choice.selected], "depth": int(ai_depth.value), "time_limit_ms": 1000})

func _process(delta: float) -> void:
	update_play_controls()
	ai_delay = maxf(0.0, ai_delay - delta)
	if ai_running and not busy and ai_delay <= 0:
		request_ai_move()

func request_state() -> void:
	if busy:
		return
	busy = true
	var error := http.request(endpoint + "/state")
	if error != OK:
		busy = false
		detail.text = "Cannot start request. Use run.bat."

func send_action(data: Dictionary) -> void:
	if play_mode.selected == 1 and data.get("action") in ["move", "reset"]:
		ai_running = true
		ai_toggle.text = "PAUSE AI"
	elif data.get("action") != "ai_move":
		stop_ai()
	if busy:
		notice.text = "Wait for the current move, then try again."
		return
	busy = true
	selected = -1
	show_markers()
	var error := http.request(endpoint + "/action", ["Content-Type: application/json"], HTTPClient.METHOD_POST, JSON.stringify(data))
	if error != OK:
		busy = false
		stop_ai()
		detail.text = "Request failed. Please reconnect."

func received(result: int, code: int, _headers: PackedStringArray, body: PackedByteArray) -> void:
	busy = false
	if result != HTTPRequest.RESULT_SUCCESS:
		stop_ai()
		status.text = "OFFLINE"
		detail.text = "Start run.bat or Python bridge, then Reconnect."
		return
	var parsed = JSON.parse_string(body.get_string_from_utf8())
	if not parsed is Dictionary:
		stop_ai()
		detail.text = "Invalid server response."
		return
	if code != 200:
		stop_ai()
		detail.text = str(parsed.get("error", "Request rejected"))
		return
	var newly_finished: bool = bool(parsed.finished) and (state.is_empty() or not bool(state.get("finished", false)))
	var animate: bool = not state.is_empty() and parsed.history.size() == state.history.size() + 1
	state = parsed
	ai_delay = .45
	if state.finished:
		stop_ai()
	var stats = state.get("ai_stats")
	if stats is Dictionary:
		if stats.algorithm == "mcts":
			var reward_text := "n/a" if stats.mean_reward == null else "%.3f" % float(stats.mean_reward)
			ai_info.text = "%s / MCTS\n%d simulations | %d tree nodes\nRollout limit: %d plies\n%.0f ms | tree depth %d\nWhite reward [-1,1]: %s" % [stats.side, stats.iterations, stats.nodes, stats.rollout_limit, stats.elapsed_ms, stats.tree_depth, reward_text]
		else:
			ai_info.text = "%s / %s\nDepth %d/%d | %d nodes\n%.0f ms | %d cutoffs\n%d re-searches | White: %.2f%s" % [stats.side, stats.algorithm, stats.depth, stats.requested_depth, stats.nodes, stats.elapsed_ms, stats.cutoffs, stats.researches, float(stats.score) / 100.0, "\nTime limit reached" if stats.timed_out else ""]
	if not stats is Dictionary:
		ai_info.text = "Start from this position. Pause after current move."
	status.text = state.title
	detail.text = state.detail
	claim_button.disabled = not state.claimable
	undo_button.disabled = not state.can_undo
	resign_button.disabled = state.finished
	draw_button.disabled = state.finished
	notice.text = state.get("notice", "")
	if newly_finished and not smoke:
		result_dialog.dialog_text = "%s\n%s\nResult: %s" % [state.title, state.detail, state.result]
		result_dialog.popup_centered(Vector2i(380, 180))
	log_text.text = "MOVE HISTORY\n\n"
	var history: Array = state.history
	for i in range(0, history.size(), 2):
		log_text.text += "%d.  %s   %s\n" % [i / 2 + 1, history[i], history[i + 1] if i + 1 < history.size() else ""]
	for child in pieces.get_children():
		pieces.remove_child(child)
		child.queue_free()
	for item in state.pieces:
		var piece_node: Node3D = Piece.build(item.symbol, int(item.square))
		piece_node.position = position_of(int(item.square))
		pieces.add_child(piece_node)
		if animate and str(state.last).length() >= 4 and int(item.square) == square_index(str(state.last).substr(2, 2)):
			var destination := piece_node.position
			piece_node.position = position_of(square_index(str(state.last).substr(0, 2)))
			var tween := piece_node.create_tween()
			tween.tween_property(piece_node, "position", destination, .25).set_trans(Tween.TRANS_QUAD).set_ease(Tween.EASE_IN_OUT)
	room.update_captured(state.get("captured", {}))
	show_markers()
	if smoke:
		print("BRIDGE_OK pieces=", pieces.get_child_count(), " legal=", state.legal.size())
		if smoke_phase == 0:
			for view in [1, 2, 3]:
				reset_camera(view)
				orbit_camera(Vector2(45, -15))
				pan_camera(Vector2(30, -20))
				camera.force_update_transform()
				var screen_point := camera.unproject_position(position_of(28))
				var ray_origin := camera.project_ray_origin(screen_point)
				var query := PhysicsRayQueryParameters3D.create(ray_origin, ray_origin + camera.project_ray_normal(screen_point) * 100)
				var hit := get_world_3d().direct_space_state.intersect_ray(query)
				assert(not hit.is_empty() and int(hit.collider.get_meta("square", -1)) == 28)
			reset_camera()
			print("CAMERA_OK orbit/pan/presets/picking")
			smoke_phase = 1
			select_square(12)
			select_square(28)
			return
		elif smoke_phase == 1:
			assert(state.last == "e2e4" and state.turn == "black")
			smoke_phase = 2
			send_action({"action": "undo"})
			return
		elif smoke_phase == 2:
			assert(state.history.is_empty() and state.turn == "white")
			smoke_phase = 3
			send_action({"action": "resign"})
			return
		elif smoke_phase == 3:
			assert(state.finished and state.result == "0-1" and resign_button.disabled)
			smoke_phase = 4
			send_action({"action": "undo"})
			return
		elif smoke_phase == 4:
			assert(not state.finished)
			smoke_phase = 5
			send_action({"action": "agree_draw"})
			return
		elif smoke_phase == 5:
			assert(state.finished and state.result == "1/2-1/2")
			smoke_phase = 6
			send_action({"action": "undo"})
			return
		elif smoke_phase == 6:
			play_mode.select(2)
			ai_depth.value = 1
			ai_white.select(0)
			ai_black.select(1)
			ai_running = true
			smoke_phase = 7
			return
		elif smoke_phase == 7:
			assert(state.history.size() == 1 and state.ai_stats.algorithm == "minimax")
			smoke_phase = 8
			return
		elif smoke_phase == 8:
			assert(state.history.size() == 2 and state.ai_stats.algorithm == "alphabeta")
			ai_white.select(2)
			ai_black.select(3)
			smoke_phase = 9
			return
		elif smoke_phase == 9:
			assert(state.history.size() == 3 and state.ai_stats.algorithm == "pvs")
			smoke_phase = 10
			return
		elif smoke_phase == 10:
			assert(state.history.size() == 4 and state.ai_stats.algorithm == "mcts")
			stop_ai()
			print("AI_MATCH_OK minimax/alphabeta/pvs/mcts/autoplay/pause")
			smoke_phase = 11
			send_action({"action": "undo"})
			return
		elif smoke_phase in [11, 12, 13]:
			smoke_phase += 1
			send_action({"action": "undo"})
			return
		elif smoke_phase == 14:
			assert(state.history.is_empty())
			play_mode.select(1)
			human_side.select(0)
			ai_black.select(1)
			change_mode()
			smoke_phase = 15
			select_square(12)
			select_square(28)
			return
		elif smoke_phase == 15:
			assert(state.history.size() == 1 and is_ai_turn())
			select_square(52)
			assert(selected == -1)
			smoke_phase = 16
			return
		elif smoke_phase == 16:
			assert(state.history.size() == 2 and state.turn == "white")
			smoke_phase = 17
			undo_player_turn()
			return
		elif smoke_phase == 17:
			assert(state.history.is_empty() and not ai_running)
			human_side.select(1)
			change_mode()
			smoke_phase = 18
			return
		elif smoke_phase == 18:
			assert(state.history.size() == 1 and state.turn == "black" and not is_ai_turn())
			var move_text := str(state.legal[0])
			smoke_phase = 19
			select_square(square_index(move_text.substr(0, 2)))
			select_square(square_index(move_text.substr(2, 2)))
			return
		elif smoke_phase == 19:
			assert(state.history.size() == 2 and state.turn == "white")
			smoke_phase = 20
			return
		elif smoke_phase == 20:
			assert(state.history.size() == 3 and state.turn == "black")
			smoke_phase = 21
			undo_player_turn()
			return
		elif smoke_phase == 21:
			assert(state.history.size() == 1 and not ai_running and state.turn == "black")
			print("HUMAN_AI_OK white/black/turn-lock/auto-reply/undo-pair")
			play_mode.select(0)
			change_mode()
			reset_camera()
			smoke_phase = 22
			send_action({"action": "reset"})
			return
		else:
			assert(not state.finished and state.history.is_empty())
			var export_path := ProjectSettings.globalize_path("res://../.local/output/smoke-game.pgn")
			DirAccess.make_dir_recursive_absolute(export_path.get_base_dir())
			export_pgn(export_path)
			assert(FileAccess.get_file_as_string(export_path).contains('[Result "*"]'))
			print("GODOT_FLOW_OK select/move/undo/resign/draw/export")
			if not capture:
				get_tree().quit()
	if capture:
		capture = false
		if capture_black:
			reset_camera(2)
		await get_tree().create_timer(0.8).timeout
		await RenderingServer.frame_post_draw
		var image := get_viewport().get_texture().get_image()
		var path := ProjectSettings.globalize_path("res://../.local/output/godot-black-view.png" if capture_black else "res://../.local/output/godot-3d.png")
		DirAccess.make_dir_recursive_absolute(path.get_base_dir())
		image.save_png(path)
		print("CAPTURE_OK ", path)
		get_tree().quit()

func square_name(square: int) -> String:
	return "abcdefgh"[square % 8] + str(floori(square / 8.0) + 1)

func square_index(name_text: String) -> int:
	return "abcdefgh".find(name_text[0]) + (int(name_text[1]) - 1) * 8

func outline_square(square: int, mat: Material) -> void:
	var center := position_of(square) + Vector3(0, .025, 0)
	for edge in [-.45, .45]:
		Piece.box(markers, center + Vector3(edge, 0, 0), Vector3(.035, .012, .93), mat)
		Piece.box(markers, center + Vector3(0, 0, edge), Vector3(.93, .012, .035), mat)

func show_markers() -> void:
	for child in markers.get_children():
		markers.remove_child(child)
		child.queue_free()
	if state.is_empty():
		return
	if int(state.check) >= 0:
		outline_square(int(state.check), Piece.material(Color("b65c52")))
	if str(state.last).length() >= 4:
		var last_mat := Piece.material(Color("546f65"), .0)
		for name_text in [str(state.last).substr(0, 2), str(state.last).substr(2, 2)]:
			outline_square(square_index(name_text), last_mat)
	if selected < 0:
		return
	var mat := Piece.material(Color("668e79"))
	outline_square(selected, mat)
	var seen: Array = []
	for move in state.legal:
		if move.substr(0, 2) == square_name(selected):
			var destination := square_index(move.substr(2, 2))
			if destination not in seen:
				seen.append(destination)
				Piece.cylinder(markers, position_of(destination) + Vector3(0, .02, 0), .16, .025, mat)

func select_square(square: int) -> void:
	if busy or state.is_empty() or state.finished or (play_mode.selected == 2 and ai_running) or (play_mode.selected == 1 and is_ai_turn()):
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
	if camera_modal_open():
		return
	if event is InputEventMouseButton and event.pressed:
		if event.button_index == MOUSE_BUTTON_RIGHT:
			camera_drag = 2 if event.shift_pressed else 1
		elif event.button_index == MOUSE_BUTTON_MIDDLE:
			camera_drag = 2
		elif event.button_index == MOUSE_BUTTON_WHEEL_UP:
			distance = maxf(6, distance / 1.1)
			update_camera()
		elif event.button_index == MOUSE_BUTTON_WHEEL_DOWN:
			distance = minf(26, distance * 1.1)
			update_camera()
		elif event.button_index == MOUSE_BUTTON_LEFT and camera_drag == 0:
			var origin := camera.project_ray_origin(event.position)
			var ray := PhysicsRayQueryParameters3D.create(origin, origin + camera.project_ray_normal(event.position) * 100)
			var hit := get_world_3d().direct_space_state.intersect_ray(ray)
			if not hit.is_empty() and hit.collider.has_meta("square"):
				select_square(int(hit.collider.get_meta("square")))
	if event is InputEventKey and event.pressed and not event.echo:
		match event.keycode:
			KEY_1: reset_camera(1)
			KEY_2: reset_camera(2)
			KEY_3: reset_camera(3)
			KEY_R: reset_camera()
			KEY_ESCAPE:
				selected = -1
				camera_drag = 0
				show_markers()

func export_pgn(path: String) -> void:
	if not path.to_lower().ends_with(".pgn"):
		path += ".pgn"
	var file := FileAccess.open(path, FileAccess.WRITE)
	if file == null:
		notice.text = "Export failed: cannot write this file."
		return
	file.store_string(str(state.get("pgn", "")) + "\n")
	file.close()
	notice.text = "PGN exported: " + path.get_file()
