extends Node3D
## Small tea service with visible tea, ceramic rim and a biscuit plate.
const P = preload("res://chess_piece.gd")

func setup(parent: Node3D, where: Vector3, dark_ceramic: bool = false) -> void:
	parent.add_child(self)
	position = where
	var ceramic := P.material(Color("7e9894") if dark_ceramic else Color("c2b7a0"))
	var rim := P.material(Color("a98f63"), .2)
	var tea := P.material(Color("73542d"))
	tea.roughness = .3
	var coaster := P.material(Color("645647"))
	P.cylinder(self, Vector3(0, .025, 0), .63, .05, coaster)
	P.cylinder(self, Vector3(0, .07, 0), .55, .05, ceramic)
	P.cylinder(self, Vector3(0, .11, 0), .27, .05, ceramic)
	var cup := CylinderMesh.new()
	cup.bottom_radius = .27
	cup.top_radius = .36
	cup.height = .48
	cup.radial_segments = 48
	cup.cap_top = false
	var cup_material := ceramic.duplicate() as StandardMaterial3D
	cup_material.cull_mode = BaseMaterial3D.CULL_DISABLED
	P.shape(self, cup, Vector3(0, .36, 0), cup_material)
	P.cylinder(self, Vector3(0, .54, 0), .335, .012, tea)
	var lip := TorusMesh.new()
	lip.inner_radius = .335
	lip.outer_radius = .367
	P.shape(self, lip, Vector3(0, .60, 0), rim)
	var handle := TorusMesh.new()
	handle.inner_radius = .12
	handle.outer_radius = .19
	var handle_node := P.shape(self, handle, Vector3(.43, .36, 0), ceramic)
	handle_node.rotation.x = PI / 2
	# Spoon and a separate small plate of biscuits.
	P.box(self, Vector3(.28, .12, .30), Vector3(.035, .025, .36), rim)
	var spoon := P.ball(self, Vector3(.28, .12, .48), .075, rim)
	spoon.scale = Vector3(.7, .18, 1.0)
	P.cylinder(self, Vector3(-1.10, .05, .02), .4, .05, ceramic)
	for i in range(2):
		P.cylinder(self, Vector3(-1.20 + i * .22, .11 + i * .035, .02), .17, .065, P.material(Color("a38657")))
		for dot in range(4):
			var angle := dot * TAU / 4
			P.ball(self, Vector3(-1.20 + i * .22 + cos(angle) * .085, .15 + i * .035, .02 + sin(angle) * .085), .018, P.material(Color("62503d")))
	# A closed linen notebook stays low so it cannot hide the back rank.
	P.box(self, Vector3(1.15, .07, 0), Vector3(.72, .12, .98), P.material(Color("6d7c77") if dark_ceramic else Color("96836f")))
	P.box(self, Vector3(1.15, .07, .015), Vector3(.65, .07, .91), P.material(Color("b4ae9d")))
	P.box(self, Vector3(1.34, .14, 0), Vector3(.025, .015, .96), rim)
