# Lộ trình ứng dụng cờ vua

- [x] Chuyển sang Python + pygame-ce; lưu bộ khung Godot trong archive/godot.
- [x] Bàn cờ 2.5D góc chéo, mặt kim loại, sprite robot hai phe và nền trạm không gian theo concept đã chọn.
- [x] Chọn quân bằng tile hoặc thân sprite, bảng sáu loại quân và hai người chơi cùng máy.
- [x] Kết nối thư viện chess: nước đi hợp lệ, nhập thành, bắt tốt qua đường, phong cấp, chiếu hết và hòa.
- [x] Lịch sử, hoàn tác, đảo bàn cờ, xác nhận chơi lại.
- [x] Kiểm thử controller và tương tác giao diện ở chế độ headless.
- [ ] AI tự viết: hàm đánh giá → Minimax → Alpha–Beta.
- [ ] Tính toán AI không chặn giao diện, lựa chọn bên và độ khó.
- [ ] Lưu/tải ván, âm thanh và cải thiện hình ảnh.
- [x] Godot 3D: robot ghép mesh, camera xoay/zoom, ánh sáng và bridge Python xử lý luật.
- [x] Tách frontend Godot và backend Python, giữ launcher chung và kiểm thử tích hợp.
- [ ] Thay robot bằng quân cờ truyền thống dễ nhận diện.
- [ ] Luồng menu → thiết lập → chơi → kết quả, đầu hàng và đề nghị hòa.
- [ ] Đồng hồ tùy chọn, lưu/tiếp tục ván và PGN.
- [ ] Hoàn thiện app hai người chơi trước khi tích hợp AI.
- [ ] Thực nghiệm so sánh thuật toán và báo cáo.

## Kiến trúc

`frontend` xử lý hiển thị, camera và input. `backend/domain` quản lý ván và luật; `backend/application` xử lý lệnh; `backend/api` cung cấp HTTP JSON. Bản Pygame chuyển vào `archive/pygame` và dùng chung luật backend. AI tương lai phân tích bản sao bàn cờ ở BE; FE chỉ nhận snapshot đã được xác nhận.

## Điều chỉnh proposal

Bản Python đầu dùng thư viện luật thay vì tự viết toàn bộ luật. Ghi rõ phần kế thừa trong báo cáo. Phần AI vẫn tự xây dựng; nếu học phần yêu cầu tự viết cả luật, thay adapter game.py bằng lõi tự viết và bổ sung perft trước khi chuyển.
