# Lõi cờ vua

`BoardState` lưu bàn cờ khởi đầu và metadata của lượt chơi. `ChessMove` là đối tượng dữ liệu cho nước đi.

Chưa có bộ sinh nước đi, kiểm tra chiếu hoặc xử lý kết thúc ván. Bước tiếp theo: sinh nước đi giả hợp lệ → thực hiện/hoàn tác → lọc nước đi làm vua bị chiếu → luật đặc biệt và hòa.

Lõi không phụ thuộc scene, camera, mô hình hay hoạt ảnh. Lịch sử vị trí để xử lý lặp lại sẽ được bổ sung cùng bộ luật.
