extends Node3D
## Procedural, original hard-surface robot set. No external model required.

static func material(color: Color, metal: float = 0.0, glow: bool = false) -> StandardMaterial3D:
	var m := StandardMaterial3D.new()
	m.albedo_color = color
	m.metallic = metal
	m.roughness = 0.55
	if glow:
		m.emission_enabled = true
		m.emission = color
		m.emission_energy_multiplier = 0.7
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
	mesh.radial_segments = 24
	return shape(parent, mesh, pos, mat)

static func build(symbol: String, square: int) -> Node3D:
	var root := Node3D.new()
	var white := symbol == symbol.to_upper()
	var accent := material(Color("51d9ff") if white else Color("ff9b35"), 0.3, true)
	var armor := material(Color("d4e1e9") if white else Color("343e50"), 0.72)
	var dark := material(Color("111a27"), 0.65)
	var joint := material(Color("647487"), 0.85)
	var kind := symbol.to_upper()
	cylinder(root, Vector3(0, .07, 0), .35, .14, dark)
	cylinder(root, Vector3(0, .145, 0), .32, .025, accent)
	cylinder(root, Vector3(0, .18, 0), .29, .045, armor)
	if kind == "R":
		for x in [-.22, .22]:
			box(root, Vector3(x, .32, 0), Vector3(.16, .22, .5), dark)
			for z in [-.17, 0.0, .17]:
				var wheel := cylinder(root, Vector3(x, .32, z), .09, .17, joint)
				wheel.rotation.z = PI / 2
		box(root, Vector3(0, .5, 0), Vector3(.43, .25, .36), armor)
		for x in [-.12, .12]:
			box(root, Vector3(x, .59, -.27), Vector3(.09, .1, .42), dark)
			box(root, Vector3(x, .59, -.49), Vector3(.065, .065, .02), accent)
	elif kind == "N":
		box(root, Vector3(0, .51, 0), Vector3(.28, .23, .45), armor)
		for x in [-.19, .19]:
			for z in [-.18, .18]:
				var leg := box(root, Vector3(x, .34, z), Vector3(.095, .31, .12), joint)
				leg.rotation.z = -.25 if x < 0 else .25
				box(root, Vector3(x, .23, z - .035), Vector3(.14, .08, .18), dark)
		var head := box(root, Vector3(0, .67, -.24), Vector3(.25, .2, .3), armor)
		head.rotation.x = -.25
		box(root, Vector3(0, .69, -.395), Vector3(.2, .035, .025), accent)
	else:
		var tall := .14 if kind in ["K", "Q", "B"] else 0.0
		for x in [-.105, .105]:
			box(root, Vector3(x, .27, -.025), Vector3(.14, .1, .23), dark)
			box(root, Vector3(x, .41 + tall / 2, 0), Vector3(.11, .27 + tall, .13), joint)
		var torso := cylinder(root, Vector3(0, .67 + tall, 0), .19, .29, armor, .24)
		torso.rotation.y = PI / 4
		box(root, Vector3(0, .69 + tall, -.19), Vector3(.12, .08, .04), accent)
		for x in [-.27, .27]:
			box(root, Vector3(x, .73 + tall, 0), Vector3(.16, .14, .2), armor)
			box(root, Vector3(x, .58 + tall, 0), Vector3(.09, .2, .1), joint)
		box(root, Vector3(0, .9 + tall, 0), Vector3(.24, .2, .22), armor)
		box(root, Vector3(0, .92 + tall, -.117), Vector3(.2, .055, .025), dark)
		box(root, Vector3(0, .925 + tall, -.134), Vector3(.16, .022, .012), accent)
		if kind == "P":
			box(root, Vector3(.28, .59, -.11), Vector3(.19, .31, .055), armor)
			box(root, Vector3(.28, .59, -.145), Vector3(.025, .24, .015), accent)
		if kind in ["K", "B"]:
			for x in [-.09, .09]:
				cylinder(root, Vector3(x, 1.2, 0), .035, .32, accent if kind == "K" else armor, .005)
		if kind == "B":
			cylinder(root, Vector3(.33, .78, -.07), .025, .95, joint)
			cylinder(root, Vector3(.33, 1.28, -.07), .08, .1, accent, .015)
		if kind == "Q":
			for x in [-.38, .38]:
				var drone := cylinder(root, Vector3(x, 1.14, 0), .09, .08, armor)
				drone.rotation.z = PI / 2
				box(root, Vector3(x, 1.14, -.08), Vector3(.065, .04, .025), accent)
	var label := Label3D.new()
	label.text = kind
	label.font_size = 32
	label.pixel_size = .006
	label.position = Vector3(0, .25, -.36)
	label.billboard = BaseMaterial3D.BILLBOARD_ENABLED
	root.add_child(label)
	var body := StaticBody3D.new()
	body.set_meta("square", square)
	var collision := CollisionShape3D.new()
	var volume := BoxShape3D.new()
	volume.size = Vector3(.66, 1.35, .66)
	collision.shape = volume
	collision.position.y = .65
	body.add_child(collision)
	root.add_child(body)
	if not white:
		root.rotation.y = PI
	return root
