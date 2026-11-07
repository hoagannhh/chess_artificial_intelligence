# Frontend — Godot

Import `project.godot` bằng Godot 4.5.1 hoặc phiên bản Godot 4 tương thích.

Khi chạy bằng editor: mở BE bằng `python -m backend` từ thư mục gốc, rồi F5. FE mặc định kết nối `127.0.0.1:8765`; có thể nhận `--bridge-port=PORT` qua user arguments.

Chạy cả app bằng `run.bat` ở gốc để launcher tự chọn cổng, mở FE và dọn server khi đóng game.

FE quản lý camera, hiển thị quân, đánh dấu nước đi, nhận thao tác và animation. Danh sách nước hợp lệ và trạng thái ván do BE cung cấp qua HTTP. FE không import mã Python và không tự quyết định kết quả ván.

Bộ quân truyền thống tạo bằng mesh trong `chess_piece.gd`. `arena.gd` quản lý bàn cờ, camera, hộp thoại kết quả/đầu hàng/hòa và xuất PGN. Không cần tải model bên ngoài.

`room.gd` dựng bàn đá/gỗ, nền studio mở và khay quân bị bắt. Không có tường hoặc cửa sổ chắn camera. `display_mecha.gd` dựng hai mẫu mecha trang trí trên đế xoay chậm; mỗi phía người chơi một mô hình. `tea_corner.gd` dựng mỗi bên một tách trà, đĩa lót, thìa, đĩa bánh và sổ tay thấp. Cảnh dùng mesh và noise texture sinh trong project, không cần asset ngoài. Màu quân và ánh sáng chính giữ theo bản đã điều chỉnh để dễ đọc.

Table Finish trong bảng điều khiển cho phép chọn Modern stone / Champagne hoặc Warm walnut. Khay quân bị bắt dùng model kích thước 1:1 với quân trên bàn, xếp hai cột trong khay rộng hơn.
