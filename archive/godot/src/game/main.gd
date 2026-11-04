extends Node3D
## Composition root: connects domain state, presentation and UI.

func _ready() -> void:
	var board := BoardView.new()
	add_child(board)
	board.display(BoardState.initial())
	var camera := Camera3D.new()
	add_child(camera)
	camera.position = Vector3(7, 11, 10)
	camera.look_at(Vector3.ZERO)
	camera.projection = Camera3D.PROJECTION_ORTHOGONAL
	camera.size = 13.5
	camera.current = true
	var light := DirectionalLight3D.new()
	light.rotation_degrees = Vector3(-55, -25, 0)
	light.light_energy = 1.3
	add_child(light)
	var environment_node := WorldEnvironment.new()
	var environment := Environment.new()
	environment.background_mode = Environment.BG_COLOR
	environment.background_color = Color("0b1220")
	environment.ambient_light_source = Environment.AMBIENT_SOURCE_COLOR
	environment.ambient_light_color = Color("b8cee5")
	environment.ambient_light_energy = 0.65
	environment_node.environment = environment
	add_child(environment_node)
	var hud := CanvasLayer.new()
	add_child(hud)
	var label := Label.new()
	label.position = Vector2(24, 20)
	label.text = "ROBOT CHESS | Project scaffold\n3D preview only - rules and AI not implemented\nP Pawn / N Knight / B Bishop / R Rook / Q Queen / K King"
	label.add_theme_font_size_override("font_size", 20)
	hud.add_child(label)
