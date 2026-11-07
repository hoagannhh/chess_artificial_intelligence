# AI và thực nghiệm

Có bốn lựa chọn: **Minimax**, **Alpha–Beta**, **PVS / NegaScout** và **MCTS**. Mã ở `backend/ai/search.py` và `backend/ai/mcts.py`; thư viện chess chỉ cung cấp luật, không cung cấp AI.

## Thiết kế

- Minimax tối đa hóa điểm cho Trắng, tối thiểu hóa cho Đen.
- Alpha–Beta dùng cùng hàm đánh giá và cùng thứ tự nước đi, thêm cắt tỉa.
- PVS tìm nhánh đầu với cửa sổ đầy đủ, thăm dò các nhánh sau bằng cửa sổ hẹp và tìm lại khi cần. Cùng hàm đánh giá/thứ tự nước với Minimax và Alpha–Beta.
- Hàm đánh giá: giá trị quân (tốt 100, mã 320, tượng 330, xe 500, hậu 900), thưởng tiến tốt và kiểm soát trung tâm của mã/tượng. Chiếu hết có điểm lớn, hòa tự động bằng 0.
- Minimax, Alpha–Beta và PVS dùng iterative deepening từ 1 tới độ sâu chọn, kiểm tra deadline tại mỗi nút. Hết giờ trả kết quả vòng hoàn thành gần nhất. Nếu chưa xong vòng 1, dùng nước hợp lệ dự phòng và báo depth 0.
- Tìm trên bản sao, push/pop được bảo vệ bằng finally. Ván thật chỉ thay đổi sau khi tìm xong và nước được kiểm tra hợp lệ.
- AI tự yêu cầu hòa khi đủ điều kiện lặp thế cờ/50 nước ở lượt hiện tại. Đây là chính sách chung của hai bên.
- Chưa có quiescence, transposition table hoặc opening book. Đây là bản tham chiếu phục vụ môn học, chưa phải engine mạnh.

## Chạy trong giao diện

Mở run.bat, chọn thuật toán mỗi bên, Level rồi Start AI. Pause AI dừng sau nước đang tính; One Move đánh đúng một lượt. Mỗi nước tối đa khoảng 1 giây tìm kiếm, khoảng nghỉ hiển thị 0,45 giây. Camera và giao diện vẫn phản hồi vì tìm kiếm ở backend, ngoài tiến trình Godot.

## Chạy nhiều ván và xuất dữ liệu

```powershell
.\.venv\Scripts\python.exe -m backend.ai.match --white pvs --black mcts --games 2 --depth 3 --time-ms 1000 --max-plies 200 --output .local/experiments/run-01
```

Tham số --white/--black nhận minimax, alphabeta, pvs hoặc mcts. Chương trình đổi màu hai thuật toán đã chọn mỗi ván, xuất `moves.csv` và các file PGN. Dùng thư mục output mới cho mỗi lần chạy; không ghi đè CSV có sẵn. Chạy độc lập với ván tự lưu của app. Giới hạn plies là số lượt của một bên, không phải số cặp nước; ván bị giới hạn vẫn mang kết quả `*`, không tính thành hòa.

So sánh hiệu quả cắt tỉa ở **cùng thế cờ và cùng độ sâu đã hoàn thành**. Với cùng thời gian, hai thuật toán có thể đạt độ sâu khác nhau. Nodes/cutoffs cộng tất cả vòng tìm kiếm, bao gồm vòng bị ngắt; thời gian đo riêng phần search, không gồm HTTP, animation và ghi file. Các ván lặp lại có tính xác định, không phải các mẫu độc lập; cần thêm tập thế cờ xuất phát và ghi phần cứng/phiên bản mã trước khi làm báo cáo chính thức. Không suy ra Elo từ vài ván tự đấu.

Kiểm thử `tests/test_ai.py` kiểm tra điểm/nước tương đương ở độ sâu hoàn thành, chiếu hết, timeout, không đổi thế cờ đầu vào, tự đấu và hoàn tác. Godot smoke kiểm tra tự chạy lần lượt cả bốn thuật toán, dừng rồi hoàn tác.

## MCTS và cách đọc số liệu

MCTS gồm selection (UCT), expansion, simulation và backpropagation. Giá trị lưu từ phía Trắng; ở nút Đen, dấu phần khai thác trong UCT đảo lại để Đen chọn phản công có lợi cho mình. Chọn nước cuối theo số lượt thăm lớn nhất; nếu bằng nhau, dùng reward có lợi cho bên đến lượt.

- Rollout chọn ngẫu nhiên nước hợp lệ. **Level 1–5** đặt giới hạn rollout **8–40 lượt đơn**, không phải độ sâu tìm kiếm đầy đủ. Thời gian vẫn là khoảng 1 giây/nước trong UI.
- Rollout kết thúc: Trắng thắng +1, Đen thắng -1, hòa 0. Nếu đạt giới hạn mà chưa kết thúc, dùng `tanh(evaluation / 600)`. Đây là reward heuristic, **không phải xác suất thắng**, không so trực tiếp với điểm centipawn của PVS.
- Trước mô phỏng có kiểm tra chiếu hết trong một nước. Khi tìm thấy, chọn ngay (có thể báo 0 simulations). Thuật toán vẫn là bản cơ sở, dễ bỏ sót chiến thuật sâu.
- Dừng khi hết thời gian hoặc đủ 4096 mô phỏng hoàn tất. Mô phỏng bị ngắt không được cập nhật ngược lên cây. Nếu chưa có mẫu hoàn tất, dùng nước hợp lệ dự phòng và reward null.
- `iterations`: mô phỏng hoàn tất; `nodes`: số node cây được tạo (kể cả gốc, không tính vị trí rollout và bước kiểm tra chiếu hết); `tree_depth`: mức sâu nhất của cây đã đi qua; `rollout_limit`: giới hạn rollout; `mean_reward`: reward trung bình của nhánh được chọn. `score` là null, `depth` là 0 với MCTS.
- PRNG dùng seed 0 mặc định. Giới hạn thời gian có thể làm số mô phỏng khác nhau giữa các lần chạy. Test dùng ngân sách mô phỏng cố định để kiểm tra tính tái lập.

PVS thêm `researches` (số lần tìm lại với cửa sổ đầy đủ). CSV lưu cả thống kê PVS lẫn MCTS. Không so số node của MCTS và Minimax như cùng một phép đo; nên so ở cùng ngân sách thời gian và nhiều thế cờ, đổi màu hai bên.

## Người đấu AI

Chọn PLAY MODE = Human vs AI, chọn You play White/Black và thuật toán cho bên máy. AI tự chạy đúng lượt; chọn Black sẽ để AI mở ván. Mode áp dụng cho thế cờ hiện tại, New Game khởi tạo lại. Undo cặp nước tạm dừng AI; nước người tiếp theo bật lại. Có thể đổi sang Human vs Human hoặc AI vs AI khi không có request đang xử lý. Chi tiết thao tác ở README. Godot smoke kiểm tra cả hai màu người, tự trả lời, không cho điều khiển bên máy và Undo cặp nước.
