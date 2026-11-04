class_name BoardView
extends Node3D
## Disposable placeholder meshes; replace with robot assets later.

func display(state: BoardState) -> void:
	for child in get_children():
		remove_child(child)
		child.queue_free()
	for rank in range(8):
		for file in range(8):
			var square := BoxMesh.new()
			square.size = Vector3(0.98, 0.16, 0.98)
			var color := Color("273747") if (rank + file) % 2 == 0 else Color("aebdcb")
			add_mesh(square, Vector3(file - 3.5, 0, 3.5 - rank), color)
			var piece := state.squares[rank * 8 + file]
			if piece != "":
				add_piece(piece, Vector3(file - 3.5, 0.08, 3.5 - rank))

func add_piece(piece: String, origin: Vector3) -> void:
	var heights := {"P": 0.45, "N": 0.65, "B": 0.8, "R": 0.6, "Q": 0.95, "K": 1.1}
	var height: float = heights[piece.to_upper()]
	var color := Color("53d9ef") if piece == piece.to_upper() else Color("ff9745")
	var body := CylinderMesh.new()
	body.top_radius = 0.18
	body.bottom_radius = 0.28
	body.height = height
	add_mesh(body, origin + Vector3(0, height / 2, 0), color)
	var label := Label3D.new()
	label.text = piece.to_upper()
	label.font_size = 64
	label.pixel_size = 0.006
	label.position = origin + Vector3(0, height + 0.2, 0)
	label.billboard = BaseMaterial3D.BILLBOARD_ENABLED
	add_child(label)

func add_mesh(mesh: Mesh, position_3d: Vector3, color: Color) -> void:
	var instance := MeshInstance3D.new()
	instance.mesh = mesh
	instance.position = position_3d
	var material := StandardMaterial3D.new()
	material.albedo_color = color
	material.roughness = 0.65
	instance.material_override = material
	add_child(instance)
