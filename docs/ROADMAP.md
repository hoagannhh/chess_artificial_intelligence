# Lộ trình ứng dụng cờ vua

## Đã có

- [x] Frontend Godot 3D và backend Python, launcher chung.
- [x] Quân cờ truyền thống dễ phân biệt, camera xoay/zoom/đảo phía.
- [x] Hai người cùng máy, toàn bộ nước hợp lệ do thư viện chess kiểm tra.
- [x] Nhập thành, bắt tốt qua đường, phong cấp, chiếu hết và hòa theo luật.
- [x] Lịch sử SAN, đánh dấu nước cuối, hoàn tác và xác nhận chơi lại.
- [x] Đầu hàng, hòa theo thỏa thuận và hộp thoại kết quả.
- [x] Tự lưu/khôi phục ván, giữ lịch sử lặp lại thế cờ, xuất PGN.
- [x] Kiểm thử domain, HTTP, lưu ván và luồng chơi trong Godot.

## Tiếp theo

- [ ] Menu thiết lập, đồng hồ tùy chọn và âm thanh.
- [ ] Nhập PGN, quản lý nhiều ván lưu.
- [ ] AI tự viết: hàm đánh giá → Minimax → Alpha–Beta.
- [ ] AI chạy nền, lựa chọn bên và độ khó.
- [ ] Thực nghiệm so sánh thuật toán và báo cáo môn học.

## Kiến trúc

`frontend` xử lý hiển thị và thao tác. `backend/domain` quản lý luật và ván; `backend/application` xử lý lệnh, lưu ván và PGN; `backend/api` cung cấp HTTP JSON. Bản Pygame và model robot cũ nằm trong `archive/`. AI tương lai phân tích bản sao bàn cờ ở BE; FE nhận snapshot đã xác nhận.

Phần luật kế thừa từ python-chess cần ghi rõ trong báo cáo. Phần AI sẽ tự triển khai.
