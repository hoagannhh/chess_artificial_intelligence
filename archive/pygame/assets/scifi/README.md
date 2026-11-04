# Orbital Arena artwork

The user-selected sci-fi concept is the visual reference for this theme.

- `units.png`: ImageGen-created transparent atlas, six columns × two rows. Columns: king, queen, bishop, knight, rook, pawn. Row 1 white/cyan, row 2 black/amber.
- `orbital.png`: ImageGen-created orbital station environment plate.

Original PNGs are retained unchanged. `legacy/pygame/robot_chess/art.py` loads and slices the atlas in memory, trims transparent cell padding, and caches display-sized sprites. No network requests at runtime. File paths resolve from the module, not the shell's working directory.

The board is rendered procedurally with 64 independently selectable tiles, metal seams, fasteners and edge lights. Unit sprites are layered by projected ground position. These are 2D illustrations in a 2.5D scene, not animated 3D meshes.
