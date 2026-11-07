extends Node3D
## Original poseable display mecha, built from mesh primitives.
const P = preload("res://chess_piece.gd")
var figure := Node3D.new()
var rotation_speed := .1

func setup(parent: Node3D, where: Vector3, crimson: bool = false) -> void:
	parent.add_child(self)
	position = where
	var armor := P.material(Color("a8afb1") if not crimson else Color("854e4b"))
	var navy := P.material(Color("3e526c") if not crimson else Color("343f46"))
	var joint := P.material(Color("353e43"), .15)
	var gold := P.material(Color("b49b65"), .35)
	var visor := P.material(Color("78b5ac"), 0, true)
	P.cylinder(self, Vector3(0, .06, 0), .75, .12, joint)
	P.cylinder(self, Vector3(0, .125, 0), .69, .025, gold)
	P.cylinder(self, Vector3(0, .16, 0), .64, .045, navy)
	add_child(figure)
	figure.position.y = .18
	figure.rotation.y = PI - .2 if not crimson else PI + .4
	rotation_speed = .09 if not crimson else -.07
	for side in [-1, 1]:
		var leg := Node3D.new()
		figure.add_child(leg)
		leg.position.x = side * .20
		leg.rotation.z = -side * .09
		P.box(leg, Vector3(0, .09, -.10), Vector3(.29, .18, .45), navy)
		P.box(leg, Vector3(0, .18, -.12), Vector3(.24, .13, .27), armor)
		P.cylinder(leg, Vector3(0, .28, 0), .075, .15, joint)
		P.box(leg, Vector3(0, .47, 0), Vector3(.25, .37, .26), armor)
		P.box(leg, Vector3(0, .52, -.145), Vector3(.13, .20, .035), navy)
		P.ball(leg, Vector3(0, .7, 0), .105, joint)
		P.box(leg, Vector3(0, .89, 0), Vector3(.24, .30, .25), armor)
	P.box(figure, Vector3(0, 1.08, 0), Vector3(.43, .18, .29), navy)
	for side in [-1, 1]:
		var skirt := P.box(figure, Vector3(side * .16, 1.02, -.17), Vector3(.25, .27, .08), armor)
		skirt.rotation.x = -.18
	P.cylinder(figure, Vector3(0, 1.25, 0), .13, .18, joint)
	P.box(figure, Vector3(0, 1.47, 0), Vector3(.56, .37, .32), navy)
	P.box(figure, Vector3(0, 1.57, -.19), Vector3(.44, .15, .12), armor)
	P.box(figure, Vector3(0, 1.43, -.19), Vector3(.17, .18, .09), gold)
	for side in [-1, 1]:
		P.box(figure, Vector3(side * .19, 1.43, -.18), Vector3(.075, .11, .025), joint)
		var arm := Node3D.new()
		arm.position = Vector3(side * .42, 1.59, 0)
		arm.rotation.z = side * .18
		figure.add_child(arm)
		P.ball(arm, Vector3.ZERO, .11, joint)
		P.box(arm, Vector3(0, .02, 0), Vector3(.34, .23, .40), armor)
		P.box(arm, Vector3(0, -.22, 0), Vector3(.17, .25, .20), navy)
		P.ball(arm, Vector3(0, -.37, 0), .09, joint)
		P.box(arm, Vector3(0, -.54, -.03), Vector3(.22, .28, .24), armor)
		P.box(arm, Vector3(0, -.74, -.03), Vector3(.17, .13, .18), joint)
		if side > 0:
			# Forearm-mounted shield with a narrow gold insignia.
			P.box(arm, Vector3(.12, -.47, -.10), Vector3(.12, .65, .40), navy)
			P.box(arm, Vector3(.19, -.47, -.10), Vector3(.018, .40, .05), gold)
		else:
			var blade := P.cylinder(arm, Vector3(0, -.38, -.25), .028, 1.1, gold, .006)
			blade.rotation.x = -.22
	# Backpack and two angled fins give a recognizable model-kit silhouette.
	P.box(figure, Vector3(0, 1.49, .25), Vector3(.40, .34, .19), joint)
	for side in [-1, 1]:
		var fin := P.box(figure, Vector3(side * .29, 1.67, .30), Vector3(.14, .65, .09), navy)
		fin.rotation.z = -side * .37
	P.cylinder(figure, Vector3(0, 1.75, 0), .075, .12, joint)
	P.box(figure, Vector3(0, 1.9, 0), Vector3(.28, .28, .27), armor)
	P.box(figure, Vector3(0, 1.91, -.145), Vector3(.21, .065, .03), joint)
	P.box(figure, Vector3(0, 1.92, -.166), Vector3(.17, .025, .014), visor)
	P.box(figure, Vector3(0, 1.8, -.16), Vector3(.085, .09, .04), navy)
	for side in [-1, 1]:
		var crest := P.box(figure, Vector3(side * .13, 2.1, -.10), Vector3(.035, .35, .035), gold)
		crest.rotation.z = -side * .65
	var plaque := Label3D.new()
	plaque.text = "02 / CRIMSON" if crimson else "01 / AEGIS"
	plaque.font_size = 22
	plaque.pixel_size = .0024
	plaque.position = Vector3(0, .19, .55)
	plaque.rotation.x = -PI / 2
	add_child(plaque)

func _process(delta: float) -> void:
	figure.rotation.y += delta * rotation_speed
