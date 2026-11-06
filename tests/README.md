# Kiểm thử

Chạy từ thư mục gốc:

```powershell
.\.venv\Scripts\python.exe -m unittest discover -s tests -p "test_*.py" -v
.\.venv\Scripts\python.exe tests/godot_smoke.py --capture
```

- `test_domain.py`: nước không hợp lệ, chiếu hết, nhập thành, bắt tốt qua đường, phong cấp và hòa.
- `test_bridge.py`: snapshot và HTTP thật, từ chối browser-origin mutation.
- `test_lifecycle.py`: tự lưu/khôi phục, PGN, đầu hàng/hòa, bảo vệ file hỏng và lịch sử lặp thế cờ.
- `test_python_game.py`: hồi quy UI Pygame lưu trữ; cần cài `archive/pygame/requirements.txt`.
- `godot_smoke.py`: Godot thật chọn/đi/hoàn tác, đầu hàng/hòa/hoàn tác kết quả và xuất PGN. Ảnh và PGN thử ở `.local/output/`.

Test dùng server RAM và thư mục lưu tạm, không sửa ván đang chơi của người dùng. Chạy backend tests riêng bằng mẫu `test_domain.py`, `test_bridge.py`, `test_lifecycle.py` nếu không cài Pygame.
