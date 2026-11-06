# Hợp đồng FE ↔ BE

HTTP JSON, mặc định `http://127.0.0.1:8765`. Launcher sử dụng cổng trống và truyền `--bridge-port` cho Godot. Một server giữ một ván cờ; launcher/CLI tự lưu và khôi phục từ `.local/saves/current.json`.

## GET /state

Trả về HTTP 200 với snapshot:

| Trường | Kiểu | Ý nghĩa |
|---|---|---|
| pieces | array | Mỗi phần tử `{square: int, symbol: string}` |
| legal | string[] | Nước đi hợp lệ theo UCI, ví dụ `e2e4`, `a7a8q` |
| turn | string | `white` hoặc `black` |
| title, detail | string | Thông báo trạng thái hiện tại |
| history | string[] | Nước đã chơi theo SAN |
| finished | boolean | Ván đã kết thúc hay chưa |
| check | int | Ô vua đang bị chiếu, hoặc -1 |
| last | string | Nước cuối theo UCI, hoặc chuỗi rỗng |
| claimable | boolean | Có thể yêu cầu hòa hay không |
| can_undo | boolean | Có nước đi hoặc kết quả thủ công để hoàn tác |
| result | string | `*`, `1-0`, `0-1`, `1/2-1/2` |
| fen | string | Thế cờ hiện tại |
| pgn | string | Toàn bộ ván theo PGN, gồm kết quả |
| notice | string | Thông báo tự lưu/khôi phục hoặc lỗi ghi ổ đĩa |

Chỉ số ô: a1=0, h1=7, a8=56, h8=63. Ký hiệu quân trắng viết hoa, đen viết thường: P/N/B/R/Q/K. FE ánh xạ sang tọa độ 3D.

## POST /action

Header `Content-Type: application/json`, body là một trong:

```json
{"action":"move","move":"e2e4"}
```

```json
{"action":"undo"}
```

```json
{"action":"reset"}
```

```json
{"action":"claim"}
```

Các lệnh bổ sung: `resign` (người đến lượt đầu hàng), `agree_draw` (hòa do cả hai đồng ý), `save` và `load` (file tự lưu cố định; không nhận đường dẫn từ client). Mỗi lệnh dùng dạng `{"action":"resign"}`. FE xác nhận trước khi reset/resign/agree_draw. `undo` hủy kết quả thủ công trước, sau đó mới hoàn tác nước đi.

Mỗi thay đổi được tự lưu. Nếu ghi ổ đĩa thất bại, nước đi vẫn được chấp nhận trong RAM và `notice` báo lỗi; không báo rằng ván đã lưu. `load` chỉ thay thế ván sau khi toàn bộ dữ liệu được kiểm tra.

Thành công: HTTP 200 và snapshot cập nhật như GET /state. Thất bại: HTTP 400 và `{ "error": "..." }`, ví dụ nước đi không hợp lệ. POST từ browser có Origin bị từ chối bằng 403. Endpoint GET không tồn tại trả 404; endpoint POST không được phép trả 403. Body giới hạn 4096 byte.

FE chỉ cập nhật bàn cờ bằng snapshot thành công. Khi mất kết nối, hiển thị lỗi và cho kết nối lại. Không tự suy diễn rằng một request lỗi đã thực hiện thành công.

Chưa có xác thực người dùng, session nhiều người hoặc API AI. Không mở server ra mạng bên ngoài.
