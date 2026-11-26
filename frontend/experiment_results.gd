extends AcceptDialog

signal loaded

const AI_NAMES := {"minimax": "Minimax", "alphabeta": "Alpha–Beta", "pvs": "PVS", "mcts": "MCTS",
	"astar_ab": "A* + Alpha–Beta", "expectimax": "Expectimax", "alphabeta_q": "Alpha–Beta + Quiescence",
	"alphazero": "AlphaZero", "alphazero_teacher": "AlphaZero có thầy"}
const RESULT_LABELS := {"1-0": "Trắng thắng (1–0)", "0-1": "Đen thắng (0–1)", "1/2-1/2": "Hòa (½–½)", "*": "Dở dang (*)"}
var http := HTTPRequest.new()
var selector := OptionButton.new()
var message := Label.new()
var tables := VBoxContainer.new()
var tabs := TabContainer.new()
var match_table := Tree.new()
var match_empty := Label.new()
var sources: Array = []

func _ready() -> void:
	title = "Kết quả thực nghiệm AI"
	get_ok_button().text = "Đóng"
	add_child(http)
	http.timeout = 6.0
	http.request_completed.connect(_received)
	var column := VBoxContainer.new()
	column.add_theme_constant_override("separation", 12)
	add_child(column)
	column.add_child(selector)
	selector.item_selected.connect(_display)
	message.autowrap_mode = TextServer.AUTOWRAP_WORD_SMART
	column.add_child(message)
	tabs.size_flags_vertical = Control.SIZE_EXPAND_FILL
	column.add_child(tabs)
	var scroll := ScrollContainer.new()
	tabs.add_child(scroll)
	tabs.set_tab_title(0, "Tổng hợp")
	tables.size_flags_horizontal = Control.SIZE_EXPAND_FILL
	tables.add_theme_constant_override("separation", 10)
	scroll.add_child(tables)
	var games := VBoxContainer.new()
	tabs.add_child(games)
	tabs.set_tab_title(1, "Từng ván")
	games.add_child(match_empty)
	match_empty.text = "Chưa có ván nào trong bảng này."
	games.add_child(match_table)
	match_table.size_flags_vertical = Control.SIZE_EXPAND_FILL
	match_table.hide_root = true
	match_table.columns = 5
	match_table.column_titles_visible = true
	var titles := ["Nguồn", "Ván", "Quân Trắng", "Quân Đen", "Kết quả"]
	for i in titles.size():
		match_table.set_column_title(i, titles[i])
	match_table.set_column_expand(1, false)
	match_table.set_column_custom_minimum_width(1, 48)
	match_table.set_column_expand_ratio(0, 2)
	match_table.set_column_custom_minimum_width(4, 145)

func open_results(endpoint: String) -> void:
	popup_centered_clamped(Vector2i(720, 460))
	refresh(endpoint)

func refresh(endpoint: String) -> void:
	http.cancel_request()
	selector.hide()
	tabs.hide()
	_clear_tables()
	message.text = "Đang tải kết quả…"
	if http.request(endpoint + "/experiments") != OK:
		message.text = "Không thể kết nối với backend. Hãy mở lại bảng để thử lại."

func _received(result: int, code: int, _headers: PackedStringArray, body: PackedByteArray) -> void:
	var data = JSON.parse_string(body.get_string_from_utf8())
	if result != HTTPRequest.RESULT_SUCCESS or code != 200 or not data is Dictionary or not data.has("sources"):
		message.text = "Không tải được bảng kết quả. Hãy kiểm tra kết nối và mở lại bảng."
		return
	sources = data.sources
	var previous := selector.get_item_text(selector.selected) if selector.selected >= 0 else ""
	selector.clear()
	for source in sources:
		selector.add_item(source.name)
		if source.name == previous:
			selector.select(selector.item_count - 1)
	selector.show()
	tabs.show()
	message.text = "" if data.skipped.is_empty() else "Không đọc được giải: " + ", ".join(data.skipped)
	_display(selector.selected)
	loaded.emit()

func _clear_tables() -> void:
	for child in tables.get_children():
		tables.remove_child(child)
		child.queue_free()

func _table(title_text: String, headers: Array) -> GridContainer:
	var title_label := Label.new()
	title_label.text = title_text
	title_label.add_theme_font_size_override("font_size", 19)
	tables.add_child(title_label)
	var grid := GridContainer.new()
	grid.columns = headers.size()
	grid.add_theme_constant_override("h_separation", 12)
	tables.add_child(grid)
	_row(grid, headers, true)
	return grid

func _row(grid: GridContainer, values: Array, header := false) -> void:
	for value in values:
		var cell := Label.new()
		cell.text = str(value)
		cell.size_flags_horizontal = Control.SIZE_EXPAND_FILL
		if header:
			cell.modulate = Color("c6d9bd")
		grid.add_child(cell)

func _display(index: int) -> void:
	_clear_tables()
	var source: Dictionary = sources[index]
	_display_matches(index)
	if int(source.games) == 0:
		var empty := Label.new()
		empty.text = "Chưa có ván nào trong bảng này."
		tables.add_child(empty)
		return
	var totals := _table("Thành tích · %d ván" % int(source.games),
		["AI", "Ván", "Thắng", "Hòa", "Thua", "Dở dang", "Tự đấu"])
	for item in source.standings:
		_row(totals, [AI_NAMES.get(item.algorithm, item.algorithm), int(item.games), int(item.wins),
			int(item.draws), int(item.losses), int(item.unfinished), int(item.self_play)])
	var pairs := _table("Đối đầu từng cặp", ["AI A", "AI B", "A thắng", "Hòa", "B thắng", "Dở dang"])
	for item in source.pairs:
		var a: String = AI_NAMES.get(item.a, item.a)
		var b: String = AI_NAMES.get(item.b, item.b)
		if item.a == item.b:
			a += " (Trắng)"
			b += " (Đen)"
		_row(pairs, [a, b, int(item.a_wins), int(item.draws), int(item.b_wins), int(item.unfinished)])

func _display_matches(index: int) -> void:
	match_table.clear()
	match_empty.visible = int(sources[index].games) == 0
	match_table.visible = not match_empty.visible
	var root := match_table.create_item()
	# The first source is the combined view. Its games are stored in the individual sources.
	for i in range(1, sources.size()):
		if index != 0 and index != i:
			continue
		var source: Dictionary = sources[i]
		for game in source.matches:
			var row := match_table.create_item(root)
			row.set_text(0, source.name)
			row.set_tooltip_text(0, source.name)
			row.set_text(1, str(int(game.number)) if i == 1 else str(game.game_id))
			row.set_tooltip_text(1, str(game.game_id))
			row.set_text(2, AI_NAMES.get(game.white_algorithm, game.white_algorithm))
			row.set_text(3, AI_NAMES.get(game.black_algorithm, game.black_algorithm))
			row.set_text(4, RESULT_LABELS[game.result])
