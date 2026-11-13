extends Control
## A read-only view of the same server position as the 3D board.
const FILES := "abcdefgh"
const GLYPHS := {"k": "♚", "q": "♛", "r": "♜", "b": "♝", "n": "♞", "p": "♟"}

var piece_font := SystemFont.new()
var position_state: Dictionary = {}
var selected_square := -1
var flipped := false

func _ready() -> void:
	piece_font.font_names = PackedStringArray(["Segoe UI Symbol", "DejaVu Sans"])
	mouse_filter = Control.MOUSE_FILTER_IGNORE
	resized.connect(queue_redraw)

func show_position(snapshot: Dictionary, selection: int) -> void:
	position_state = snapshot
	selected_square = selection
	queue_redraw()

func set_flipped(value: bool) -> void:
	if value != flipped:
		flipped = value
		queue_redraw()

func cell_of(square: int) -> Vector2:
	var file := square % 8
	var rank := floori(square / 8.0)
	return Vector2(7 - file, rank) if flipped else Vector2(file, 7 - rank)

func _draw() -> void:
	var tile := floorf((minf(size.x, size.y) - 20.0) / 8.0)
	if tile <= 0.0:
		return
	var extent := Vector2.ONE * tile * 8.0
	var origin := ((size - extent) / 2.0 + Vector2(7, -5)).floor()
	var checked := int(position_state.get("check", -1))
	var last := str(position_state.get("last", ""))
	for square in range(64):
		var rank := floori(square / 8.0)
		var file := square % 8
		var square_name := FILES[file] + str(rank + 1)
		var rect := Rect2(origin + cell_of(square) * tile, Vector2.ONE * tile)
		var fill := Color("b29a7e") if (file + rank) % 2 == 0 else Color("e2d0af")
		if last.length() >= 4 and square_name in [last.substr(0, 2), last.substr(2, 2)]:
			fill = fill.lerp(Color("91a36a"), .65)
		if square == checked:
			fill = fill.lerp(Color("bc685d"), .78)
		draw_rect(rect, fill)
		if square == selected_square:
			draw_rect(rect.grow(-1), Color("41674e"), false, 2.0)
	var label_font := get_theme_default_font()
	for i in range(8):
		var file_label := FILES[7 - i if flipped else i]
		var rank_label := str(i + 1 if flipped else 8 - i)
		draw_string(label_font, origin + Vector2(i * tile, extent.y + 14), file_label, HORIZONTAL_ALIGNMENT_CENTER, tile, 12, Color("c2cbc5"))
		draw_string(label_font, origin + Vector2(-17, (i + .5) * tile + 4), rank_label, HORIZONTAL_ALIGNMENT_CENTER, 13, 12, Color("c2cbc5"))
	var font_size := floori(tile * .93)
	var baseline := (tile + piece_font.get_ascent(font_size) - piece_font.get_descent(font_size)) * .5
	for item in position_state.get("pieces", []):
		var symbol := str(item.symbol)
		var glyph := str(GLYPHS.get(symbol.to_lower(), ""))
		var at := origin + cell_of(int(item.square)) * tile + Vector2(0, baseline)
		var white := symbol == symbol.to_upper()
		var fill := Color("fff4da") if white else Color("252c2c")
		var edge := Color("50473c") if white else Color("c6b79e")
		draw_string_outline(piece_font, at, glyph, HORIZONTAL_ALIGNMENT_CENTER, tile, font_size, 2 if white else 1, edge)
		draw_string(piece_font, at, glyph, HORIZONTAL_ALIGNMENT_CENTER, tile, font_size, fill)
