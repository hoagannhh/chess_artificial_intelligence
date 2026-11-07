extends Node3D
## Quiet studio setting, built from original procedural geometry.
const Piece = preload("res://chess_piece.gd")
var surface_material: StandardMaterial3D
var table_edge_material: StandardMaterial3D
var wood_texture: NoiseTexture2D
var stone_texture: NoiseTexture2D
var captured_root := Node3D.new()

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
	# The board rests directly on the tabletop; props stay outside its footprint.
	Piece.box(self, Vector3(0, -.69, 0), Vector3(15.2, .28, 12.8), surface_material)
	Piece.box(self, Vector3(0, -.85, 0), Vector3(15.24, .045, 12.84), table_edge_material)
	Piece.box(self, Vector3(0, -.96, 0), Vector3(14.8, .18, 12.4), metal)
	for x in [-4.8, 4.8]:
		Piece.box(self, Vector3(x, -2.48, 0), Vector3(.2, 3.0, 7.6), metal)
		Piece.box(self, Vector3(x, -3.97, 0), Vector3(1.5, .08, 8.0), metal)
	set_finish(0)
	Piece.box(self, Vector3(0, -4.12, 0), Vector3(100, .2, 100), Piece.material(Color("555957")))
	Piece.box(self, Vector3(0, -3.99, 0), Vector3(17, .04, 15), Piece.material(Color("69716b")))
	# Open studio: no wall/window geometry anywhere along the orbit path.
	var collectible = preload("res://display_mecha.gd")
	# One model at each player's end, clear of board and capture trays.
	collectible.new().setup(self, Vector3(3.6, -.55, 5.35), false)
	collectible.new().setup(self, Vector3(-3.6, -.55, -5.35), true)
	var tea_service = preload("res://tea_corner.gd")
	var white_tea = tea_service.new()
	white_tea.setup(self, Vector3(.25, -.55, 5.40), false)
	var black_tea = tea_service.new()
	black_tea.setup(self, Vector3(-.25, -.55, -5.40), true)
	black_tea.rotation.y = PI
	# Functional trays for captured pieces: left = White losses, right = Black losses.
	for side in [-1, 1]:
		Piece.box(self, Vector3(side * 5.65, -.49, .25), Vector3(1.95, .12, 7.7), table_edge_material)
		Piece.box(self, Vector3(side * 5.65, -.42, .25), Vector3(1.80, .025, 7.52), felt)
		for edge in [-.94, .94]:
			Piece.box(self, Vector3(side * 5.65 + edge, -.36, .25), Vector3(.045, .16, 7.7), metal)
		var label := Label3D.new()
		label.text = "WHITE / CAPTURED" if side < 0 else "BLACK / CAPTURED"
		label.position = Vector3(side * 5.65, -.37, 4.38)
		label.rotation.x = -PI / 2
		label.font_size = 22
		label.pixel_size = .0035
		label.modulate = Color("d0c6ad")
		add_child(label)
	add_child(captured_root)

func update_captured(captured: Dictionary) -> void:
	for child in captured_root.get_children():
		captured_root.remove_child(child)
		child.queue_free()
	for color in ["white", "black"]:
		var losses: Array = captured.get(color, [])
		for i in range(losses.size()):
			var model: Node3D = Piece.build(str(losses[i]), -1)
			# Decorations must never intercept board picking rays.
			for child in model.get_children():
				if child is StaticBody3D:
					model.remove_child(child)
					child.queue_free()
			model.scale = Vector3.ONE
			model.position = Vector3((-5.65 if color == "white" else 5.65) + (i % 2 - .5) * .82, -.40, 3.35 - floori(i / 2.0) * .88)
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
