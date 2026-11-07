# Backend — Python

Chạy từ thư mục gốc repository:

```powershell
.\.venv\Scripts\python.exe -m backend --port 8765
```

- `domain/game.py`: trạng thái ván, luật, thực hiện/hoàn tác, kết quả. Dùng thư viện chess.
- `application/session.py`: lệnh move/undo/reset/claim/resign/agree_draw/save/load và snapshot gửi cho FE.
- `application/storage.py`: lưu JSON nguyên tử, kiểm tra dữ liệu khi khôi phục và tạo PGN.
- `api/server.py`: HTTP/JSON trên localhost; chuyển request thành lệnh của application.
- `__main__.py`: điểm chạy BE độc lập.
- `requirements.txt`: chỉ cần chess, không phụ thuộc Pygame hoặc Godot.

Backend là nơi quyết định nước hợp lệ, lượt chơi và kết quả. API không tin vào vị trí quân do FE tự tính. AI Minimax/Alpha–Beta/PVS nằm trong `ai/search.py`, MCTS trong `ai/mcts.py`, chạy tại backend trên bản sao bàn cờ; đồng hồ chưa triển khai.

Backend giữ một ván trong RAM cho mỗi server. Launcher và CLI tự lưu ở `.local/saves/current.json`, khôi phục lịch sử và kết quả khi khởi động lại. Test khởi tạo server không truyền save_path sẽ chỉ dùng RAM. Chỉ phục vụ ứng dụng local, chưa phải dịch vụ multiplayer.

Hợp đồng giao tiếp: `docs/API.md` ở gốc repository.
