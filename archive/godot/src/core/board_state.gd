class_name BoardState
extends RefCounted
## Pure board data. No rendering or scene dependencies.
## Index = rank * 8 + file; a1 = 0, h8 = 63.
## Uppercase = white, lowercase = black, empty string = empty square.

var squares: Array[String] = []
var white_to_move: bool = true
var castling_rights: String = "KQkq"
var en_passant_square: int = -1
var halfmove_clock: int = 0
var fullmove_number: int = 1

func _init() -> void:
	squares.resize(64)
	squares.fill("")

static func initial() -> BoardState:
	var state := BoardState.new()
	var back_rank := "RNBQKBNR"
	for file in range(8):
		state.squares[file] = back_rank[file]
		state.squares[8 + file] = "P"
		state.squares[48 + file] = "p"
		state.squares[56 + file] = back_rank[file].to_lower()
	return state
