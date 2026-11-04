class_name ChessMove
extends RefCounted
## Value object; validation belongs to the rules module.

var from_square: int
var to_square: int
var promotion: String

func _init(origin: int, destination: int, promote_to: String = "") -> void:
	from_square = origin
	to_square = destination
	promotion = promote_to
