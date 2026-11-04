# Giao diện Godot 3D

## Chạy

Nhấp đúp `run.bat` ở thư mục gốc hoặc chạy:

```powershell
.\.venv\Scripts\python.exe app.py
```

Launcher mở server luật Python trên một cổng localhost còn trống, truyền cổng cho Godot và đóng server khi cửa sổ game kết thúc. Hai người chơi cùng máy; chưa có AI. 

Godot portable 4.5.1 từ bản phát hành chính thức đã tải vào `.tools/godot` trên máy hiện tại, không đưa vào Git. Khi chuyển máy, cài thư viện Python như README và chỉ định Godot riêng:

```powershell
.\.venv\Scripts\python.exe app.py --godot "C:/Godot/Godot.exe"
```

Nguồn engine: https://github.com/godotengine/godot-builds/releases/tag/4.5.1-stable

## Điều khiển

- Chuột trái: chọn quân hoặc ô đích có chấm sáng.
- Giữ chuột phải và kéo trên vùng bàn cờ: xoay camera, đổi góc cao/thấp.
- Cuộn chuột trên bàn: zoom.
- Flip Camera: nhìn từ phía đối diện; Reset Camera: trở về góc mặc định.
- Esc: bỏ chọn. New Game có xác nhận trước khi xóa ván hiện tại.
- Phong cấp: chọn Queen, Rook, Bishop hoặc Knight; Cancel để quay lại.
- Undo: hoàn tác một nước. Claim Draw chỉ mở khi đủ điều kiện.

## Chạy từ Godot Editor

Import `frontend/project.godot`. Trước khi nhấn F5, mở terminal chạy:

```powershell
.\.venv\Scripts\python.exe -m backend
```

Server mặc định là `127.0.0.1:8765`. Nếu chưa chạy, giao diện báo Offline; mở server rồi nhấn Reconnect. Đóng server bằng Ctrl+C khi kết thúc. Khởi động lại server sẽ bắt đầu ván mới.

## Cấu trúc

- `frontend/arena.gd`: bàn cờ, camera, ánh sáng, UI, chọn quân bằng raycast, kết nối HTTP và chuyển động quân.
- `frontend/robot.gd`: sáu loại robot 3D ghép mesh nguyên thủy, vật liệu, đế và collider.
- `backend/api/server.py`: API `/state`, `/action`; mọi nước đi được kiểm tra ở Python.
- `app.py`: quản lý vòng đời server và tiến trình Godot.

Model 3D được tạo bằng code trong dự án, chưa có độ chi tiết như ảnh concept. Renderer Compatibility có bóng đổ, vật liệu và màu emissive; chưa có bloom hậu kỳ, animation xương, hiệu ứng bắt quân hoặc âm thanh. Ván chưa được lưu ra ổ đĩa. Bản Pygame 2.5D vẫn chạy riêng bằng `archive/pygame/run.bat`.

## Kiểm tra

```powershell
.\.venv\Scripts\python.exe -m unittest discover -s tests -p "test_*.py" -v
.\.venv\Scripts\python.exe tests/godot_smoke.py
.\.venv\Scripts\python.exe tests/godot_smoke.py --capture
```

Smoke test dùng Godot portable trong `.tools`, khởi tạo ván, chọn e2, đi e4 rồi hoàn tác qua HTTP thật. Chế độ capture mở cửa sổ ngắn, ghi `.local/output/godot-3d.png` và thoát. Cần cho phép kết nối localhost trong môi trường chạy kiểm thử.

