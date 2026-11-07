extends Node3D
## Original procedural Staunton-inspired pieces, generated without external assets.

static func material(color: Color, metal: float = 0.0, glow: bool = false) -> StandardMaterial3D:
	var m := StandardMaterial3D.new()
	m.albedo_color = color
	m.metallic = metal
	m.roughness = 0.82
	m.metallic_specular = 0.22
	if glow:
		m.emission_enabled = true
		m.emission = color
		m.emission_energy_multiplier = 0.4
	return m

static func shape(parent: Node3D, mesh: Mesh, pos: Vector3, mat: Material) -> MeshInstance3D:
	var node := MeshInstance3D.new()
	node.mesh = mesh
	node.position = pos
	node.material_override = mat
	parent.add_child(node)
	return node

static func box(parent: Node3D, pos: Vector3, size: Vector3, mat: Material) -> MeshInstance3D:
	var mesh := BoxMesh.new()
	mesh.size = size
	return shape(parent, mesh, pos, mat)

static func cylinder(parent: Node3D, pos: Vector3, radius: float, height: float, mat: Material, top: float = -1.0) -> MeshInstance3D:
	var mesh := CylinderMesh.new()
	mesh.bottom_radius = radius
	mesh.top_radius = radius if top < 0 else top
	mesh.height = height
	mesh.radial_segments = 48
	return shape(parent, mesh, pos, mat)

static func ball(parent: Node3D, pos: Vector3, radius: float, mat: Material, stretch: float = 1.0) -> MeshInstance3D:
	var mesh := SphereMesh.new()
	mesh.radius = radius
	mesh.height = radius * 2.0
	var node := shape(parent, mesh, pos, mat)
	node.scale.y = stretch
	return node

static func build(symbol: String, square: int) -> Node3D:
	var root := Node3D.new()
	var white := symbol == symbol.to_upper()
	var body_mat := material(Color("b5babc") if white else Color("45494b"), .0)
	var trim := material(Color("69747a") if white else Color("737878"), .08)
	var eye := material(Color("263448") if white else Color("e6cf98"))
	var kind := symbol.to_upper()
	var height: float = {"P": .48, "R": .58, "N": .57, "B": .7, "Q": .79, "K": .88}[kind]
	cylinder(root, Vector3(0, .065, 0), .34, .13, body_mat, .32)
	cylinder(root, Vector3(0, .14, 0), .31, .035, trim)
	cylinder(root, Vector3(0, .20, 0), .29, .09, body_mat, .23)
	cylinder(root, Vector3(0, (.25 + height) / 2, 0), .22, height - .25, body_mat, .12)
	cylinder(root, Vector3(0, height, 0), .20, .07, body_mat, .18)
	match kind:
		"P":
			ball(root, Vector3(0, height + .18, 0), .17, body_mat)
		"R":
			cylinder(root, Vector3(0, .69, 0), .23, .19, body_mat)
			for i in range(6):
				var a := i * TAU / 6.0
				var tooth := box(root, Vector3(cos(a) * .18, .84, sin(a) * .18), Vector3(.14, .15, .14), body_mat)
				tooth.rotation.y = -a
		"N":
			var neck := ball(root, Vector3(0, .70, .025), .18, body_mat, 1.65)
			neck.rotation.x = -.32
			var head := ball(root, Vector3(0, .91, -.10), .17, body_mat)
			head.scale = Vector3(.8, 1.0, 1.3)
			var muzzle := ball(root, Vector3(0, .84, -.26), .12, body_mat)
			muzzle.scale = Vector3(.95, .85, 1.3)
			for x in [-.085, .085]:
				cylinder(root, Vector3(x, 1.08, -.035), .055, .19, body_mat, .012)
				ball(root, Vector3(x * 1.55, .94, -.15), .027, eye)
			for i in range(5):
				box(root, Vector3(0, .58 + i * .08, .16 - i * .025), Vector3(.09, .11, .085), trim)
		"B":
			ball(root, Vector3(0, .88, 0), .17, body_mat, 1.4)
			var cut := box(root, Vector3(0, .97, -.14), Vector3(.035, .22, .025), eye)
			cut.rotation.z = -.45
			ball(root, Vector3(0, 1.13, 0), .055, trim)
		"Q":
			cylinder(root, Vector3(0, .91, 0), .13, .22, body_mat, .25)
			for i in range(8):
				var a := i * TAU / 8.0
				ball(root, Vector3(cos(a) * .21, 1.06, sin(a) * .21), .055, trim if white else body_mat)
			ball(root, Vector3(0, 1.10, 0), .085, trim)
		"K":
			ball(root, Vector3(0, 1.01, 0), .16, body_mat, .75)
			box(root, Vector3(0, 1.24, 0), Vector3(.09, .32, .09), trim if white else body_mat)
			box(root, Vector3(0, 1.27, 0), Vector3(.28, .085, .09), trim if white else body_mat)
	if white:
		# A thin inverted hull keeps light pieces distinct on both square colors.
		var edge := StandardMaterial3D.new()
		edge.albedo_color = Color("505b60")
		edge.shading_mode = BaseMaterial3D.SHADING_MODE_UNSHADED
		edge.cull_mode = BaseMaterial3D.CULL_FRONT
		edge.grow = true
		edge.grow_amount = .007
		for part in root.get_children():
			if part is MeshInstance3D:
				var outline := MeshInstance3D.new()
				outline.mesh = part.mesh
				outline.transform = part.transform
				outline.material_override = edge
				outline.cast_shadow = GeometryInstance3D.SHADOW_CASTING_SETTING_OFF
				root.add_child(outline)
	var body := StaticBody3D.new()
	body.set_meta("square", square)
	var collision := CollisionShape3D.new()
	var volume := CylinderShape3D.new()
	volume.radius = .33
	volume.height = {"P": .82, "R": .95, "N": 1.19, "B": 1.2, "Q": 1.2, "K": 1.42}[kind]
	collision.shape = volume
	collision.position.y = volume.height / 2
	body.add_child(collision)
	root.add_child(body)
	if not white:
		root.rotation.y = PI
	return root
