# Giao diện Godot 3D

## Chạy

Nhấp đúp `run.bat` ở thư mục gốc hoặc chạy:

```powershell
.\.venv\Scripts\python.exe app.py
```

Launcher mở server luật Python trên một cổng localhost còn trống, truyền cổng cho Godot và đóng server khi cửa sổ game kết thúc. Có chế độ hai người, người đấu AI và AI đấu AI.

Godot portable 4.5.1 từ bản phát hành chính thức đã tải vào `.tools/godot` trên máy hiện tại, không đưa vào Git. Khi chuyển máy, cài thư viện Python như README và chỉ định Godot riêng:

```powershell
.\.venv\Scripts\python.exe app.py --godot "C:/Godot/Godot.exe"
```

Nguồn engine: https://github.com/godotengine/godot-builds/releases/tag/4.5.1-stable

## Điều khiển

- Chuột trái: chọn quân hoặc ô đích có chấm sáng.
- Giữ chuột phải và kéo trên vùng bàn cờ: xoay camera, đổi góc cao/thấp.
- Cuộn chuột trên bàn: zoom gần/xa.
- Giữ chuột giữa hoặc Shift + chuột phải rồi kéo: dịch chuyển góc nhìn.
- Phím 1/2/3: nhìn từ bên Trắng/Đen/trên cao. R: đặt lại camera.
- Có thể xoay tròn 360°, hạ góc sát bàn hoặc nâng gần thẳng đứng; kéo tiếp qua bảng điều khiển vẫn giữ thao tác camera.
- Flip Camera: nhìn từ phía đối diện; Reset Camera: trở về góc mặc định.
- Esc: bỏ chọn. New Game có xác nhận trước khi xóa ván hiện tại.
- Phong cấp: chọn Queen, Rook, Bishop hoặc Knight; Cancel để quay lại.
- Undo: hoàn tác một nước, hoặc hủy quyết định hòa/đầu hàng vừa thực hiện. Claim Draw chỉ mở khi đủ điều kiện.
- Resign: người đến lượt đầu hàng, có xác nhận. Agree Draw: hai người xác nhận đồng ý hòa.
- Export PGN: chọn vị trí lưu file PGN. Mở lại app tự khôi phục ván đang chơi.

## Chạy từ Godot Editor

Import `frontend/project.godot`. Trước khi nhấn F5, mở terminal chạy:

```powershell
.\.venv\Scripts\python.exe -m backend
```

Server mặc định là `127.0.0.1:8765`. Nếu chưa chạy, giao diện báo Offline; mở server rồi nhấn Reconnect. Đóng server bằng Ctrl+C khi kết thúc. Khởi động lại server khôi phục ván tự lưu.

## Cấu trúc

- `frontend/arena.gd`: bàn cờ, camera, ánh sáng, UI, chọn quân bằng raycast, kết nối HTTP và chuyển động quân.
- `frontend/chess_piece.gd`: sáu quân cờ truyền thống dựng bằng mesh, vật liệu và collider.
- `backend/api/server.py`: API `/state`, `/action`; mọi nước đi được kiểm tra ở Python.
- `app.py`: quản lý vòng đời server và tiến trình Godot.

Model 3D được tạo bằng code trong dự án, chưa có độ chi tiết như ảnh concept. Renderer Compatibility có bóng đổ, vật liệu và màu emissive; chưa có bloom hậu kỳ, animation xương, hiệu ứng bắt quân hoặc âm thanh. Ván tự lưu ở `.local/saves/current.json`. Nút Export PGN xuất lịch sử và kết quả ra file. Bản Pygame 2.5D vẫn chạy riêng bằng `archive/pygame/run.bat`.

## Kiểm tra

```powershell
.\.venv\Scripts\python.exe -m unittest discover -s tests -p "test_*.py" -v
.\.venv\Scripts\python.exe tests/godot_smoke.py
.\.venv\Scripts\python.exe tests/godot_smoke.py --capture
```

Smoke test dùng Godot portable trong `.tools`, khởi tạo ván, chọn e2, đi e4, hoàn tác, đầu hàng, hòa, hoàn tác kết quả và xuất PGN qua HTTP thật. Chế độ capture mở cửa sổ ngắn, ghi `.local/output/godot-3d.png` và thoát. Cần cho phép kết nối localhost trong môi trường chạy kiểm thử.

Chạy `tests/godot_smoke.py --capture --black-view` để chụp góc nhìn Đen ra `.local/output/godot-black-view.png`. Cảnh studio mở không có tường/cửa sổ; decor mecha nằm ngoài vùng bàn cờ và không có collider.
