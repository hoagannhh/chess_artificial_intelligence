# Chess App

Ứng dụng cờ vua: **Godot làm giao diện, Python xử lý luật và ván đấu**.
Chơi hai người cùng máy, đấu với máy hoặc cho các AI đấu nhau. Có bảy AI tìm kiếm cùng hai nhánh **AlphaZero** và **AlphaZero có thầy**.

## Mở app

Nhấp đúp **run.bat**, hoặc chạy ở thư mục gốc:

```powershell
.\.venv\Scripts\python.exe app.py
```

Launcher tự mở backend, chạy Godot và đóng backend khi thoát game.

## Các thư mục chính

| Thư mục | Nội dung |
|---|---|
| **frontend/** | Dự án Godot đang sử dụng: giao diện, bàn cờ, camera, model |
| **backend/** | Luật, trạng thái ván, xử lý lệnh và API Python |
| **tests/** | Kiểm thử Python và kết nối Godot–Python |
| **docs/** | Hướng dẫn, hợp đồng API và lộ trình |
| **archive/** | Các bản thử cũ và tài nguyên của chúng; không phải app chính |

Các mục kỹ thuật có dấu chấm không cần sửa khi phát triển tính năng: `.venv/` là môi trường Python, `.tools/` chứa Godot portable, `.local/` chứa ván tự lưu và ảnh kiểm tra, `.git/` là lịch sử Git.

Thư mục gốc chỉ giữ `app.py` (launcher), `run.bat` (mở app), `requirements.txt` (thư viện) và README cùng các file cấu hình.

## Phát triển riêng FE / BE

BE, chạy từ thư mục gốc:

```powershell
.\.venv\Scripts\python.exe -m backend --port 8765
```

FE: mở **frontend/project.godot** trong Godot rồi nhấn F5. FE kết nối backend ở cổng 8765; nhấn Reconnect nếu cần. Khởi động lại BE sẽ khôi phục ván tự lưu trong `.local/saves/current.json`.

- [Hướng dẫn giao diện 3D](docs/GODOT_3D.md)
- [Hợp đồng API](docs/API.md)
- [Lộ trình](docs/ROADMAP.md)
- [Backend](backend/README.md)
- [Chạy thực nghiệm AI](docs/EXPERIMENTS.md)

## Cài trên máy mới

Cài Python 3.12 và Godot 4 tương thích (đã kiểm tra với 4.5.1):

```powershell
py -3.12 -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
.\.venv\Scripts\python.exe app.py --godot "C:/Godot/Godot.exe"
```

Máy hiện tại đã có `.venv` và Godot portable trong `.tools/godot`. Không sao chép `.venv` sang máy khác. Môi trường hiện tại dùng Python 3.12.10 độc lập trong `.tools/python312`, không phụ thuộc runtime Codex. Nếu cần tạo lại: `.\.tools\python312\python.exe -m venv .venv`. Xem phiên bản bằng `python --version` (không có khoảng trắng giữa -- và version).

## Kiểm thử

BE không cần Pygame:

```powershell
.\.venv\Scripts\python.exe -m unittest discover -s tests -p "test_domain.py" -v
.\.venv\Scripts\python.exe -m unittest discover -s tests -p "test_bridge.py" -v
.\.venv\Scripts\python.exe -m unittest discover -s tests -p "test_lifecycle.py" -v
.\.venv\Scripts\python.exe tests/godot_smoke.py
```

Thêm `--capture` vào smoke test để chụp `.local/output/godot-3d.png`.
Muốn chạy toàn bộ test, gồm UI cũ, cài `archive/pygame/requirements.txt` rồi chạy:

```powershell
.\.venv\Scripts\python.exe -m unittest discover -s tests -p "test_*.py" -v
```

## Phạm vi hiện tại

- Quân cờ truyền thống 3D: vua, hậu, tượng, mã, xe, tốt; hai màu ngà và xanh đen.
- Hai người cùng máy; gợi ý nước hợp lệ, nước vừa đi, cảnh báo chiếu, phong cấp đủ bốn lựa chọn.
- Lịch sử SAN, hoàn tác, chơi lại có xác nhận, đầu hàng, hòa theo thỏa thuận và yêu cầu hòa theo luật.
- Thông báo kết quả khi hết ván; vẫn xem được bàn cờ và hoàn tác để phân tích.
- Tự lưu sau mỗi thao tác, tự khôi phục khi mở lại. **New Game** thay thế ván đang lưu sau khi xác nhận.
- **Export PGN** lưu ván ra file để xem bằng phần mềm cờ khác. Chưa nhập PGN.
- Xoay, zoom, đảo hướng và đặt lại camera.

Bộ luật sử dụng thư viện `chess`. Bản chơi local có đồng hồ đếm ngược tùy chọn và chín lựa chọn AI. Chỉ chạy một phiên app tại một thời điểm vì dùng chung file tự lưu.

Chạy `run.bat` rồi chọn **AI vs AI** để đấu **AlphaZero** với **AlphaZero có thầy**.
Hai nhánh mặc định lần lượt nạp `.local/models/alphazero/current.pt` và
`.local/models/alphazero-teacher-01/current.pt`. Bảng thực nghiệm ghi riêng tên nhánh,
màu quân và mã checkpoint của mỗi bên.

AlphaZero cần cài thêm PyTorch và tạo model. Có thể học trước từ Alpha–Beta + Quiescence
rồi tiếp tục tự đấu. Hướng dẫn cài đặt, học từ thầy, tự đấu, tiếp tục huấn luyện
và đánh giá từng phiên bản nằm trong [hướng dẫn AlphaZero](backend/ai/alphazero/README.md).

Nếu file lưu hỏng, app báo lỗi và giữ nguyên file; chọn New Game sẽ lưu bản hỏng thành `current.invalid.json` trước khi tạo ván mới.

## Cho AI đấu nhau

1. Chạy `run.bat`. Chọn New Game nếu muốn bắt đầu ván mới; Start AI tiếp tục từ thế cờ hiện tại.
2. Chọn Play Mode = AI vs AI, rồi chọn thuật toán cho White và Black; có thể chọn cùng thuật toán cho hai bên.
3. Chọn Level 1–5 (mặc định 3). Với MCTS, mức này quy định giới hạn mô phỏng 8–40 nửa nước. Hai nhánh AlphaZero dùng trần 64–320 lượt tìm kiếm. Sáu AI tìm theo độ sâu dùng mức này làm độ sâu chính. Mỗi bên có khoảng 1 giây tính mỗi nước.
4. Nhấn Start AI. Pause AI dừng sau nước đang tính; One Move chỉ đánh một nước cho bên đến lượt.
5. Xem độ sâu hoàn thành/yêu cầu, số nút, số lần cắt tỉa, thời gian và điểm đánh giá từ phía Trắng. MCTS hiển thị số mô phỏng, node cây và reward riêng. Cuộn bảng bên phải để xem các nút phía dưới.

Camera vẫn sử dụng được khi AI tính. Để tự đi quân hoặc hoàn tác, Pause rồi chờ nước hiện tại kết thúc. Mở lại app khôi phục ván nhưng không tự khởi động AI.

Chi tiết thuật toán và chạy nhiều ván lấy CSV/PGN: [AI](docs/AI.md).

Giải đấu terminal lưu cấu hình từ lúc bắt đầu trong `run_config.json`. Khi dừng
bằng Ctrl+C, các ván đã ghi đầy đủ được giữ lại. Chạy tiếp bằng đúng thư mục cũ:

```powershell
.\.venv\Scripts\python.exe -m backend.ai.tournament --resume --output .local/experiments/TEN_GIAI_CU
```

Thêm `--dry-run` để kiểm tra số ván đã lưu và ván tiếp theo mà không đấu hoặc ghi file.
Ván đang tính khi ngắt sẽ được đấu lại; các ván đã ghi, kể cả ván chạm giới hạn
`max_plies`, được bỏ qua. Giữ nguyên checkpoint AI trong suốt một giải.
Giải cũ chưa có `run_config.json` hoặc `metadata.json` cần truyền lại các tham số
`--algorithms`, `--games-per-pair`, `--depth`, `--time-ms`, `--max-plies` của lệnh gốc
trong lần tiếp tục đầu tiên (và `--initial-fen` nếu đã dùng thế xuất phát riêng).
Nếu CSV/PGN bị ghi thiếu hoặc không khớp lịch đấu, chương trình báo lỗi và giữ nguyên dữ liệu.
Nếu bị tắt cưỡng bức, có thể còn `tournament.lock`; chỉ xóa file khóa sau khi xác nhận
không còn tiến trình chạy giải đó. Bảng kết quả trên giao diện nhận giải khi hoàn tất.

## Người đấu AI

1. Chạy `run.bat`, chọn **PLAY MODE → Human vs AI**.
2. Chọn **You play → White / Black**. Camera quay về phía người chơi; chọn Đen thì AI Trắng đi trước.
3. Chọn thuật toán ở hàng của phía AI và Level. AI tự trả lời sau nước người chơi, không cần nhấn Start mỗi lượt.
4. Chế độ áp dụng cho thế cờ hiện tại. Chọn **New Game** nếu muốn chơi lại từ đầu.

Trong chế độ này chỉ được đi bên đã chọn, kể cả khi AI tạm dừng. Undo lùi cặp nước khi AI đã trả lời (hoặc lùi một nước khi chưa trả lời), rồi tạm dừng AI. Đi nước khác sẽ bật lại AI; Start AI tiếp tục nếu đang tới lượt máy. Kết quả hòa/đầu hàng thủ công được hủy trước khi hoàn tác nước đi.

Resign và Claim Draw chỉ dùng khi đến lượt người. Agree Draw tắt vì chưa có cơ chế AI chấp nhận đề nghị hòa. Pause dừng sau nước đang tính. Khi mở lại, ván được khôi phục nhưng chế độ mặc định là Human vs Human; chọn lại Human vs AI và màu muốn chơi.
