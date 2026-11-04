# AI chơi cờ — chưa triển khai

Phụ thuộc duy nhất vào dữ liệu và bộ luật trong `src/core`.

Các module dự kiến:
- `evaluation.gd`: đánh giá lực lượng và vị trí quân.
- `minimax.gd`: bản tham chiếu để so sánh.
- `alpha_beta.gd`: tìm kiếm có cắt tỉa.
- `search_result.gd`: nước đi, điểm, số node, độ sâu và thời gian.

Chỉ bắt đầu AI sau khi bộ luật và thao tác thực hiện/hoàn tác vượt kiểm thử. Không cho AI sửa trực tiếp scene. Tìm kiếm sẽ chạy ngoài luồng giao diện trên bản sao trạng thái.
