extends Node3D
## Quiet studio setting, built from original procedural geometry.
const Piece = preload("res://chess_piece.gd")
var surface_material: StandardMaterial3D
var table_edge_material: StandardMaterial3D
var wood_texture: NoiseTexture2D
var stone_texture: NoiseTexture2D
var captured_root := Node3D.new()
var clock_faces: Array[Node3D] = []
var clock_digits: Dictionary[String, Label3D] = {}

func _ready() -> void:
	var wood := Piece.material(Color("655346"))
	var noise := FastNoiseLite.new()
	noise.frequency = .025
	noise.fractal_octaves = 3
	var grain := NoiseTexture2D.new()
	grain.width = 512
	grain.height = 512
	grain.noise = noise
	var shades := Gradient.new()
	shades.set_color(0, Color("a5a09a"))
	shades.set_color(1, Color("eeebe5"))
	grain.color_ramp = shades
	wood.albedo_texture = grain
	wood.uv1_scale = Vector3(1, 14, 1)
	wood_texture = grain
	var stone_noise := FastNoiseLite.new()
	stone_noise.frequency = .012
	stone_noise.fractal_octaves = 4
	stone_noise.domain_warp_enabled = true
	stone_noise.domain_warp_amplitude = 24.0
	stone_texture = NoiseTexture2D.new()
	stone_texture.width = 1024
	stone_texture.height = 1024
	stone_texture.noise = stone_noise
	var veins := Gradient.new()
	veins.colors = PackedColorArray([Color("555b5d"), Color("686f70"), Color("989c97"), Color("686f70"), Color("555b5d")])
	veins.offsets = PackedFloat32Array([0.0, .47, .495, .52, 1.0])
	stone_texture.color_ramp = veins
	surface_material = Piece.material(Color.WHITE)
	table_edge_material = Piece.material(Color("a38d69"), .45)
	var metal := Piece.material(Color("3e4849"))
	var felt := Piece.material(Color("66665f"))
	# The board rests directly on the tabletop.
	Piece.box(self, Vector3(0, -.69, 0), Vector3(15.2, .28, 12.8), surface_material)
	Piece.box(self, Vector3(0, -.85, 0), Vector3(15.24, .045, 12.84), table_edge_material)
	Piece.box(self, Vector3(0, -.96, 0), Vector3(14.8, .18, 12.4), metal)
	for x in [-4.8, 4.8]:
		Piece.box(self, Vector3(x, -2.48, 0), Vector3(.2, 3.0, 7.6), metal)
		Piece.box(self, Vector3(x, -3.97, 0), Vector3(1.5, .08, 8.0), metal)
	set_finish(0)
	Piece.box(self, Vector3(0, -4.12, 0), Vector3(100, .2, 100), Piece.material(Color("555957")))
	Piece.box(self, Vector3(0, -3.99, 0), Vector3(17, .04, 15), Piece.material(Color("69716b")))
	# Captures start at the end of the player who took them.
	for side in [-1, 1]:
		Piece.box(self, Vector3(side * 5.65, -.49, .25), Vector3(1.95, .12, 7.7), table_edge_material)
		Piece.box(self, Vector3(side * 5.65, -.42, .25), Vector3(1.80, .025, 7.52), felt)
		for edge in [-.94, .94]:
			Piece.box(self, Vector3(side * 5.65 + edge, -.36, .25), Vector3(.045, .16, 7.7), metal)
		var label := Label3D.new()
		label.text = "BLACK CAPTURES" if side < 0 else "WHITE CAPTURES"
		label.position = Vector3(side * 5.65, -.37, 4.38 * side)
		label.rotation = Vector3(-PI / 2, PI if side < 0 else 0.0, 0)
		label.font_size = 22
		label.pixel_size = .0035
		label.modulate = Color("d0c6ad")
		add_child(label)
	add_child(captured_root)
	build_promotion_sets(metal)
	build_table_clocks(metal)

func build_table_clocks(case_material: Material) -> void:
	var lcd := Piece.material(Color("202929"))
	var digits_font := SystemFont.new()
	digits_font.font_names = PackedStringArray(["Consolas", "DejaVu Sans Mono"])
	for side in ["white", "black"]:
		var end := 1.0 if side == "white" else -1.0
		var clock_case := Node3D.new()
		clock_case.position = Vector3(5.7 * end, -.55, 4.78 * end)
		add_child(clock_case)
		Piece.box(clock_case, Vector3(0, .085, 0), Vector3(1.76, .17, .98), case_material)
		Piece.box(clock_case, Vector3(0, .178, 0), Vector3(1.70, .03, .93), table_edge_material)
		Piece.box(clock_case, Vector3(0, .231, 0), Vector3(1.65, .08, .89), case_material)
		var clock_face := Node3D.new()
		clock_face.position.y = .28
		clock_case.add_child(clock_face)
		clock_faces.append(clock_face)
		Piece.box(clock_face, Vector3.ZERO, Vector3(1.50, .018, .81), lcd)
		var name_label := Label3D.new()
		name_label.text = side.to_upper()
		name_label.font_size = 24
		name_label.outline_size = 3
		name_label.pixel_size = .007
		name_label.position = Vector3(0, .018, -.27)
		name_label.rotation.x = -PI / 2
		name_label.modulate = Color("b2bfba")
		clock_face.add_child(name_label)
		var digits := Label3D.new()
		digits.text = "—"
		digits.font = digits_font
		digits.font_size = 48
		digits.outline_size = 3
		digits.pixel_size = .008
		digits.position = Vector3(0, .018, .11)
		digits.rotation.x = -PI / 2
		digits.modulate = Color("b2bfba")
		clock_face.add_child(digits)
		clock_digits[side] = digits

func set_clock_side(side: String, display: String, color: Color) -> void:
	var digits := clock_digits[side]
	digits.text = display
	digits.modulate = color

func set_clock_flipped(flipped: bool) -> void:
	for face in clock_faces:
		face.rotation.y = PI if flipped else 0.0

func display_piece(symbol: String) -> Node3D:
	var model := Piece.build(symbol, -1)
	for child in model.get_children():
		if child is StaticBody3D:
			model.remove_child(child)
			child.queue_free()
	return model

func build_promotion_sets(base: Material) -> void:
	for side in [-1, 1]:
		Piece.box(self, Vector3(0, -.49, side * 5.25), Vector3(3.6, .12, .91), base)
		Piece.box(self, Vector3(0, -.42, side * 5.25), Vector3(3.53, .025, .85), table_edge_material)
		var kinds := "QRBN" if side > 0 else "qrbn"
		for i in range(kinds.length()):
			var model := display_piece(kinds[i])
			model.scale = Vector3.ONE * .76
			model.position = Vector3((i - 1.5) * .87 * side, -.405, side * 5.25)
			add_child(model)
		var label := Label3D.new()
		label.text = "PROMOTION"
		label.font_size = 22
		label.pixel_size = .0045
		label.position = Vector3(0, -.535, side * 5.89)
		label.rotation = Vector3(-PI / 2, PI if side < 0 else 0.0, 0)
		label.modulate = Color("d0c6ad")
		add_child(label)

func update_captured(captured: Dictionary) -> void:
	for child in captured_root.get_children():
		captured_root.remove_child(child)
		child.queue_free()
	for color in ["white", "black"]:
		var losses: Array = captured.get(color, [])
		for i in range(losses.size()):
			var model := display_piece(str(losses[i]))
			var end := -1.0 if color == "white" else 1.0
			model.position = Vector3(end * 5.65 + (i % 2 - .5) * .82, -.40, end * (3.35 - floori(i / 2.0) * .88))
			captured_root.add_child(model)

func set_finish(index: int) -> void:
	if index == 0:
		surface_material.albedo_color = Color("8b9090")
		surface_material.albedo_texture = stone_texture
		surface_material.uv1_scale = Vector3(1.4, 1.4, 1)
		surface_material.roughness = .48
		table_edge_material.albedo_color = Color("a38d69")
	else:
		surface_material.albedo_color = Color("655346")
		surface_material.albedo_texture = wood_texture
		surface_material.uv1_scale = Vector3(1, 14, 1)
		surface_material.roughness = .82
		table_edge_material.albedo_color = Color("8e7961")
