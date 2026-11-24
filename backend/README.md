# Backend — Python

Chạy từ thư mục gốc repository:

```powershell
.\.venv\Scripts\python.exe -m backend --port 8765
```

- `domain/game.py`: trạng thái ván, luật, thực hiện/hoàn tác, kết quả. Dùng thư viện chess.
- `application/session.py`: lệnh move/undo/reset/claim/resign/agree_draw/save/load và snapshot gửi cho FE.
- `application/storage.py`: lưu JSON nguyên tử, kiểm tra dữ liệu khi khôi phục và tạo PGN.
- `api/server.py`: HTTP/JSON trên localhost; chuyển request thành lệnh của application.
- `ai/tournament.py`: chạy giải AI vs AI theo cặp, đổi màu cân bằng và xuất W/D/L, CSV, JSON, PGN.
- `__main__.py`: điểm chạy BE độc lập.
- `requirements.txt`: chỉ cần chess, không phụ thuộc Pygame hoặc Godot.

Backend quyết định nước hợp lệ, lượt chơi và kết quả. Các AI nhận bản sao của bàn cờ qua `ai/search.py`. MCTS nằm trong `ai/mcts.py`; bản A* + Alpha–Beta dùng `ai/pawn_routes.py` để đánh giá đường phong cấp. Đồng hồ có thể chọn 5/10/15 phút hoặc tắt.

Backend giữ một ván trong RAM cho mỗi server. Launcher và CLI tự lưu ở `.local/saves/current.json`, khôi phục lịch sử và kết quả khi khởi động lại. Test khởi tạo server không truyền save_path sẽ chỉ dùng RAM. Chỉ phục vụ ứng dụng local, chưa phải dịch vụ multiplayer.

Hợp đồng giao tiếp: `docs/API.md` ở gốc repository. Hướng dẫn chạy giải và đọc bảng thành tích: `docs/EXPERIMENTS.md`.
