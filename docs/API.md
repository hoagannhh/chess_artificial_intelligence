# Hợp đồng FE ↔ BE

HTTP JSON, mặc định `http://127.0.0.1:8765`. Launcher sử dụng cổng trống và truyền `--bridge-port` cho Godot. Một server giữ một ván cờ trong RAM.

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

Thành công: HTTP 200 và snapshot cập nhật như GET /state. Thất bại: HTTP 400 và `{ "error": "..." }`, ví dụ nước đi không hợp lệ. POST từ browser có Origin bị từ chối bằng 403. Endpoint GET không tồn tại trả 404; endpoint POST không được phép trả 403. Body giới hạn 4096 byte.

FE chỉ cập nhật bàn cờ bằng snapshot thành công. Khi mất kết nối, hiển thị lỗi và cho kết nối lại. Không tự suy diễn rằng một request lỗi đã thực hiện thành công.

Chưa có xác thực người dùng, lưu ván lâu dài, session nhiều người hoặc API AI. Không mở server ra mạng bên ngoài.
