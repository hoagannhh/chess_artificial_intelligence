# AlphaZero thu nhỏ cho cờ vua

Mô hình kết hợp mạng policy–value, tìm kiếm PUCT, tự đấu và tùy chọn học có giám sát từ thầy.
Mạng mặc định có khoảng 679 nghìn tham số, 32 kênh và hai khối residual.
Ngân sách huấn luyện ban đầu phù hợp để kiểm tra quy trình trên CPU. Sức chơi cần được đo qua thực nghiệm.

## Cài đặt

Chạy PowerShell tại thư mục gốc project.

```powershell
.\.venv\Scripts\python.exe -m pip install -r backend/ai/alphazero/requirements.txt
```

Tệp requirements cài PyTorch CPU. Có thể dùng bản PyTorch CUDA tương thích với máy và truyền
`--device cuda` cho lệnh huấn luyện. Phần chọn nước trong app hiện dùng CPU.

## Huấn luyện và tiếp tục

```powershell
.\.venv\Scripts\python.exe -m backend.ai.alphazero.train --iterations 2 --games 2 --simulations 16 --max-plies 256 --steps 16 --batch-size 16
.\.venv\Scripts\python.exe -m backend.ai.alphazero.train --resume --iterations 10 --games 4 --simulations 64 --steps 64
```

Thư mục mặc định là `.local/models/alphazero/`. Lần chạy mới cần một thư mục chưa tồn tại.
`--resume` tiếp tục từ `latest.pt`, giữ trọng số, trạng thái optimizer, bộ nhớ replay và bộ sinh số ngẫu nhiên.
Tham số `--iterations` quy định số vòng chạy thêm. Kiến trúc mạng và trạng thái optimizer
được lấy từ checkpoint khi tiếp tục. Learning rate, các tham số tự đấu và số bước cập nhật lấy từ lệnh mới.
Mạng khởi tạo mới dùng LeakyReLU ở đầu value để duy trì gradient khi đầu ra tích chập âm.
Khi nạp để chơi, checkpoint dùng hàm kích hoạt đã lưu. Các lượt huấn luyện mới và tiếp tục
mặc định dùng LeakyReLU. `--value-activation relu` cho phép chạy đối chứng với cách cũ.

| Tệp | Nội dung |
|---|---|
| `initial.pt` | Mạng khởi tạo, dùng làm mốc đối chiếu |
| `checkpoint-0001.pt`, … | Trọng số sau mỗi vòng, dùng để đánh giá từng phiên bản |
| `current.pt` | Model mới nhất để app nạp |
| `latest.pt` | Trạng thái huấn luyện để tiếp tục |
| `metrics.json` | Loss, số ván theo kết quả, số ván dừng ở giới hạn, cấu hình mỗi vòng |
| `selfplay-0001.pgn`, … | Các ván tạo dữ liệu theo vòng |

Checkpoint được thay thế nguyên tử sau mỗi vòng. Ctrl+C giải phóng khóa `training.lock`.
Nếu tiến trình bị tắt cưỡng bức, kiểm tra rằng tiến trình huấn luyện đã kết thúc trước khi xóa khóa còn sót.
Dữ liệu trong vòng chưa lưu sẽ được tạo lại khi tiếp tục.

## Học từ Alpha–Beta + Quiescence

Thầy được cố định là `alphabeta_q`, dùng bộ máy tìm kiếm của project.
Ở mỗi thế cờ, thầy tạo nhãn policy cho nước được đề xuất và nhãn value bằng
`tanh(score_cp / 600)` sau khi đổi điểm về phía đang đi. Nhãn value này là đánh giá heuristic.
Những lần tìm kiếm chưa hoàn thành độ sâu 1 được bỏ qua khi tạo mẫu.
Các mẫu ghi độ sâu hoàn thành, độ sâu yêu cầu, điểm gốc, nước đề xuất và thông tin hết thời gian.

Dữ liệu được tạo bằng các ván có khám phá, với tám nửa nước đầu chọn ngẫu nhiên
và xác suất khám phá mặc định 15% ở các lượt sau. Policy luôn học nước thầy đề xuất
trước khi chọn nước thực sự đi. Các ván này phục vụ tạo dữ liệu huấn luyện.
Đánh giá sức chơi dùng runner giải đấu với các cấu hình được cố định.

Khởi động bằng hai vòng học từ thầy, mỗi vòng bốn ván. `--games 0` đặt số ván tự đấu bằng 0.
Thư mục output cần chưa tồn tại.

```powershell
.\.venv\Scripts\python.exe -m backend.ai.alphazero.train --output .local/models/teacher-new --games 0 --teacher-games 4 --teacher-depth 3 --teacher-time-ms 200 --iterations 2 --max-plies 128 --steps 128 --learning-rate 0.0003
```

Có thể thêm `--init-from đường-dẫn-checkpoint.pt` để bắt đầu từ trọng số đã có.
Sau giai đoạn khởi động, tiếp tục tự đấu và học từ thầy trong cùng thư mục.

```powershell
.\.venv\Scripts\python.exe -m backend.ai.alphazero.train --resume --output .local/models/teacher-new --iterations 10 --games 2 --teacher-games 1 --teacher-depth 3 --teacher-time-ms 200 --simulations 64 --max-plies 256 --steps 64 --teacher-ratio 0.25 --learning-rate 0.0003
```

Model có bộ nhớ dữ liệu thầy riêng, mặc định tối đa 2.048 mẫu.
Khi cả hai loại dữ liệu có sẵn, `--teacher-ratio 0.25` dành khoảng một phần tư mỗi batch cho thầy.
Giai đoạn chỉ có dữ liệu thầy dùng toàn bộ batch từ thầy.
`--teacher-games 0` dừng tạo nhãn mới nhưng dữ liệu thầy đã lưu vẫn dùng được khi resume.
`--teacher-ratio 0` chuyển sang cập nhật bằng dữ liệu tự đấu khi đã có dữ liệu tự đấu.

`latest.pt` chứa cả hai bộ nhớ và optimizer. Các file `teacher-NNNN.pgn`
ghi ván tạo dữ liệu cùng lời chú thích về nước thầy đề xuất.
`metrics.json` ghi số nhãn, số mẫu bị bỏ qua và phân bố độ sâu thầy thực sự hoàn thành.
Checkpoint có `training_method` và `lineage` để truy vết các giai đoạn
`supervised_teacher`, `teacher_assisted_self_play` và `self_play`.
Trường `training_method` cũng xuất hiện trong CSV từng nước và thống kê AI của giao diện.

Khi dùng nhánh này trong báo cáo, mô tả phương pháp là
**học có giám sát từ Alpha–Beta + Quiescence, kết hợp học tăng cường tự đấu và MCTS**.
Sức chơi phụ thuộc chất lượng, độ đa dạng của dữ liệu thầy và ngân sách huấn luyện.

Để mở model trong nhánh này trên giao diện, đặt đường dẫn trước khi chạy app.

```powershell
$env:CHESS_AZ_TEACHER_MODEL = (Resolve-Path .local/models/teacher-new/current.pt).Path
.\run.bat
```

## Chơi và đánh giá

Chạy `run.bat`, chọn **Human vs AI** hoặc **AI vs AI**, sau đó chọn nhánh mong muốn.

| Nhánh trong app | Mã dùng với CLI | Model mặc định |
|---|---|---|
| AlphaZero | `alphazero` | `.local/models/alphazero/current.pt` |
| AlphaZero có thầy | `alphazero_teacher` | `.local/models/alphazero-teacher-01/current.pt` |

Hai model được nạp và giữ trong bộ nhớ độc lập để có thể đánh luân phiên trong cùng ván.
Mỗi nhánh có cấu hình đường dẫn riêng. Có thể chỉ định checkpoint cố định trước khi mở app hoặc chạy giải.

```powershell
$env:CHESS_AZ_PLAIN_MODEL = (Resolve-Path .local/models/alphazero/checkpoint-0032.pt).Path
$env:CHESS_AZ_TEACHER_MODEL = (Resolve-Path .local/models/alphazero-teacher-01/checkpoint-0003.pt).Path
.\run.bat
```

```powershell
.\.venv\Scripts\python.exe -m backend.ai.tournament --algorithms alphazero alphazero_teacher --games-per-pair 2 --depth 1 --time-ms 1000 --max-plies 256 --output .local/experiments/az-branches-01
```

Mỗi lần đánh giá dùng thư mục output mới. Kết quả vẫn phân biệt Trắng và Đen.
`model_id` ghi dấu vân tay checkpoint trong CSV từng nước. CSV từng ván có thêm
`white_model_id` và `black_model_id` để xác định checkpoint của từng bên. Bảng kết quả trong app
hiển thị AlphaZero kèm mã model để phân biệt các phiên bản. Để so sánh ổn định, dùng
`checkpoint-NNNN.pt` cố định trong toàn bộ giải. Các ván dừng ở `max-plies` được ghi dở dang.

Level 1–5 đặt trần 64–320 mô phỏng, đồng thời chịu giới hạn thời gian mỗi nước.
Giá trị mạng được quy đổi về phía Trắng trong giao diện, nằm trong [-1, 1].
Thời gian thống kê tìm kiếm bắt đầu sau khi nạp model. Lần gọi đầu có thêm chi phí nhập PyTorch và đọc checkpoint.
Một lần tính mạng đang chạy có thể vượt nhẹ thời hạn.

## Quy trình học

Mỗi trạng thái chứa tám vị trí gần nhất, quân cờ, số lần lặp lại, lượt đi, quyền nhập thành,
đồng hồ 50 nước, số thứ tự nước và ô bắt tốt qua đường. Cách mã hóa dùng tọa độ tuyệt đối.
Mỗi ô xuất phát có 73 dạng nước đi, tổng cộng 4.672 đầu ra. Các nước bất hợp lệ
bị loại khi chọn nước. Mạng có hai đầu ra policy và value, với value theo phía đang đi.

PUCT dùng xác suất từ mạng để định hướng khám phá và đảo dấu điểm qua mỗi lượt.
Trước tìm kiếm, bộ máy kiểm tra nước chiếu hết ngay để ưu tiên kết quả đã được luật xác nhận.
Self-play thêm nhiễu Dirichlet ở gốc và lấy mẫu nước theo số lượt thăm trong 30 nửa nước đầu.
Sau đó tiếp tục lấy mẫu với nhiệt độ mặc định 0,75 để duy trì khám phá.
`--temperature-moves` và `--late-temperature` điều chỉnh hai phần này.
Khi dùng model để thi đấu, nước đi vẫn được chọn theo lượt thăm cao nhất.
Policy học từ phân bố lượt thăm của MCTS. Value học kết quả cuối ván, thắng +1, hòa 0, thua -1
theo phía đang đi ở từng mẫu. Các ván bị cắt ở giới hạn chỉ đóng góp policy loss,
value loss được che đi. Khi nhiều ván bị cắt, nên kiểm tra số `value_positions` trước khi đánh giá
khả năng học kết quả ván cờ. Tự đấu áp dụng cùng chính sách nhận hòa khi đủ điều kiện như app.
Một nửa dung lượng replay dành cho mẫu thắng–thua, nửa còn lại dành cho hòa và ván dở dang.
Cách lấy mẫu này bảo vệ dữ liệu quyết định trước các đợt tự đấu liên tục hòa, đồng thời làm thay đổi
phân bố dữ liệu huấn luyện. `decisive_positions` đếm các mẫu thắng–thua còn giữ lại.
`terminations` ghi số ván theo từng lý do kết thúc. Lệnh train cảnh báo nếu replay thiếu mẫu thắng–thua.

## Khi model lặp nước và liên tục hòa

Value loss có thể rất nhỏ nếu tất cả nhãn đều bằng 0. Cần kiểm tra số mẫu thắng–thua,
lý do hòa, PGN và kết quả đấu đối thủ độc lập để đánh giá sức chơi.
Để thử khôi phục khả năng học trên một nhánh mới, dùng `--init-from` với thư mục output mới.
Nhánh này lấy trọng số từ checkpoint, tạo optimizer và replay mới, đánh số vòng từ 1.

```powershell
.\.venv\Scripts\python.exe -m backend.ai.alphazero.train --init-from .local/models/alphazero/checkpoint-0032.pt --output .local/models/alphazero-recovery-01 --value-activation leaky_relu --iterations 3 --games 4 --simulations 64 --max-plies 256 --steps 32 --learning-rate 0.0002 --late-temperature 1
```

Khi thư mục này đã được tạo, tiếp tục bằng `--resume --output .local/models/alphazero-recovery-01`.
Truyền lại các tham số tự đấu, learning rate và số bước cập nhật mong muốn khi tiếp tục.
Chọn checkpoint trong nhánh đó bằng `CHESS_AZ_PLAIN_MODEL` để đánh giá.

`run.bat` đặt đường dẫn mặc định cho `CHESS_AZ_PLAIN_MODEL` và `CHESS_AZ_TEACHER_MODEL`
nếu chúng chưa được cấu hình. Các lệnh Python trực tiếp vẫn hỗ trợ biến cũ `CHESS_AZ_MODEL`
cho nhánh thường khi `CHESS_AZ_PLAIN_MODEL` chưa được đặt.

Đây là thiết kế thu nhỏ có vòng huấn luyện tuần tự, dựng cây mới mỗi nước, replay hữu hạn
và chưa có đánh giá tự động để lựa chọn checkpoint tốt nhất. `current.pt` là bản mới nhất.
Kết quả vài vòng chạy thử chỉ xác minh hoạt động. Đánh giá sức chơi cần nhiều ván đổi màu,
cùng thời gian mỗi nước và tập thế xuất phát được ghi rõ.

Thiết kế tham khảo [bài báo AlphaZero của DeepMind](https://storage.googleapis.com/deepmind-media/DeepMind.com/Blog/alphazero-shedding-new-light-on-chess-shogi-and-go/alphazero_preprint.pdf).
Lưu và nạp trọng số dựa trên [hướng dẫn PyTorch](https://docs.pytorch.org/tutorials/beginner/saving_loading_models.html).

## Kiểm thử

```powershell
.\.venv\Scripts\python.exe -m unittest discover -s tests -p test_alphazero.py -q
.\.venv\Scripts\python.exe tests/godot_smoke.py --alphazero-both
```

Kiểm thử Godot cho cả hai nhánh cần hai model khác nhau ở đường dẫn mặc định
hoặc các biến `CHESS_AZ_PLAIN_MODEL` và `CHESS_AZ_TEACHER_MODEL` tương ứng.
