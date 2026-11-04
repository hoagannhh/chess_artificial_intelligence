# Backend — Python

Chạy từ thư mục gốc repository:

```powershell
.\.venv\Scripts\python.exe -m backend --port 8765
```

- `domain/game.py`: trạng thái ván, luật, thực hiện/hoàn tác, kết quả. Dùng thư viện chess.
- `application/session.py`: lệnh move/undo/reset/claim và snapshot gửi cho FE.
- `api/server.py`: HTTP/JSON trên localhost; chuyển request thành lệnh của application.
- `__main__.py`: điểm chạy BE độc lập.
- `requirements.txt`: chỉ cần chess, không phụ thuộc Pygame hoặc Godot.

Backend là nơi quyết định nước hợp lệ, lượt chơi và kết quả. API không tin vào vị trí quân do FE tự tính. AI, đồng hồ và lưu ván sẽ bổ sung ở backend sau; hiện chưa triển khai.

Backend giữ một ván trong RAM cho mỗi server. Khởi động lại sẽ tạo ván mới. Chỉ phục vụ ứng dụng local, chưa phải dịch vụ multiplayer.

Hợp đồng giao tiếp: `docs/API.md` ở gốc repository.
