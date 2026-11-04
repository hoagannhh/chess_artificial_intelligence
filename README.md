# Chess App

Ứng dụng cờ vua: **Godot làm giao diện, Python xử lý luật và ván đấu**.
Hiện chơi hai người trên cùng máy; chưa có AI.

## Mở app

Nhấp đúp **run.bat**, hoặc chạy ở thư mục gốc:

```powershell
.\.venv\Scripts\python.exe app.py
```

Launcher tự mở backend, chạy Godot và đóng backend khi thoát game.

## Các thư mục chính

| Thư mục | Nội dung |
|---|---|
| **frontend/** | Dự án Godot đang sử dụng: giao diện, bàn cờ, camera, model |
| **backend/** | Luật, trạng thái ván, xử lý lệnh và API Python |
| **tests/** | Kiểm thử Python và kết nối Godot–Python |
| **docs/** | Hướng dẫn, hợp đồng API và lộ trình |
| **archive/** | Các bản thử cũ và tài nguyên của chúng; không phải app chính |

Các mục kỹ thuật có dấu chấm không cần sửa khi phát triển tính năng: `.venv/` là môi trường Python, `.tools/` chứa Godot portable, `.local/` chứa ảnh kiểm tra sinh tự động, `.git/` là lịch sử Git.

Thư mục gốc chỉ giữ `app.py` (launcher), `run.bat` (mở app), `requirements.txt` (thư viện) và README cùng các file cấu hình.

## Phát triển riêng FE / BE

BE, chạy từ thư mục gốc:

```powershell
.\.venv\Scripts\python.exe -m backend --port 8765
```

FE: mở **frontend/project.godot** trong Godot rồi nhấn F5. FE kết nối backend ở cổng 8765; nhấn Reconnect nếu cần. Khởi động lại BE sẽ tạo ván mới vì chưa có lưu ván.

- [Hướng dẫn giao diện 3D](docs/GODOT_3D.md)
- [Hợp đồng API](docs/API.md)
- [Lộ trình](docs/ROADMAP.md)
- [Backend](backend/README.md)

## Cài trên máy mới

Cài Python 3.12 và Godot 4 tương thích (đã kiểm tra với 4.5.1):

```powershell
py -3.12 -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
.\.venv\Scripts\python.exe app.py --godot "C:/Godot/Godot.exe"
```

Máy hiện tại đã có `.venv` và Godot portable trong `.tools/godot`. Không sao chép `.venv` sang máy khác. Môi trường hiện tại còn dùng Python đi kèm runtime ứng dụng; nếu runtime bị thay thế, cần tạo lại môi trường bằng Python riêng.

## Kiểm thử

BE không cần Pygame:

```powershell
.\.venv\Scripts\python.exe -m unittest discover -s tests -p "test_domain.py" -v
.\.venv\Scripts\python.exe -m unittest discover -s tests -p "test_bridge.py" -v
.\.venv\Scripts\python.exe tests/godot_smoke.py
```

Thêm `--capture` vào smoke test để chụp `.local/output/godot-3d.png`.
Muốn chạy toàn bộ test, gồm UI cũ, cài `archive/pygame/requirements.txt` rồi chạy:

```powershell
.\.venv\Scripts\python.exe -m unittest discover -s tests -p "test_*.py" -v
```

## Phạm vi hiện tại

Bộ luật sử dụng thư viện `chess`; AI sẽ tự triển khai sau. Lần sắp xếp này không thay đổi cách chơi hoặc model. Mục tiêu giao diện tiếp theo là quân cờ truyền thống dễ nhận diện. Model 3D đang dùng vẫn là bộ robot ghép khối.
