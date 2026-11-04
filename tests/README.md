# Kiểm thử Python

Chạy từ thư mục gốc: `.venv\Scripts\python.exe -m unittest discover -s tests -p "test_python*.py" -v`.

Bộ test hiện tại kiểm tra controller và input/render headless. Bộ luật do thư viện chess cung cấp; test tập trung vào tích hợp và tính nhất quán lịch sử/hoàn tác.

Khi có AI: thêm kiểm thử Minimax và Alpha–Beta cùng điểm ở cùng độ sâu, giữ nguyên trạng thái sau tìm kiếm, giới hạn thời gian và lựa chọn nước đi hợp lệ.
