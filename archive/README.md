# Các bản thử đã lưu trữ

Không dùng thư mục này để phát triển app chính. App chính nằm ở `frontend/` và `backend/`.

- `godot/`: scaffold Godot ban đầu.
- `pygame/`: UI 2.5D cũ, mã nguồn và ảnh sci-fi của bản đó. Luật được import từ backend hiện tại, không có bản sao luật riêng.

Để chạy Pygame cũ, từ thư mục gốc:

```powershell
.\.venv\Scripts\python.exe -m pip install -r archive/pygame/requirements.txt
.\.venv\Scripts\python.exe archive/pygame/main.py
```

Hoặc nhấp `archive/pygame/run.bat`. Tài nguyên ảnh nằm tại `archive/pygame/assets/`.
