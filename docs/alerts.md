# Alert và runbook

Các alert bên dưới dựa trên triệu chứng quan sát được trong log/dashboard. Kênh Slack là `#k4-l3b-alerts`; owner cấu hình hiện tại là `student-2A202602905` và cần đổi nếu MSSV/repository được dùng bởi học viên khác.

## HighLatencyP95

- **Severity / duration:** warning, 5 phút liên tục.
- **Điều kiện:** P95 `response_sent.latency_ms` > 3000 ms.
- **Ảnh hưởng:** người dùng phải chờ lâu mới nhận câu trả lời.
- **Kiểm tra:** (1) Xác nhận time range và P95/P99 trên dashboard. (2) Lọc `response_sent` chậm trong `data/logs.jsonl`, lấy `correlation_id`. (3) Mở trace cùng ID, so sánh thời gian retrieval và generation.
- **Mitigation:** nếu retrieval chậm, kiểm tra/tắt practice incident hoặc khôi phục dependency; nếu generation/prompt chậm bất thường, rollback prompt `production` về version ổn định; xác nhận P95 phục hồi.
- **Slack:** `#k4-l3b-alerts`.

## ElevatedErrorRate

- **Severity / duration:** critical, 5 phút liên tục.
- **Điều kiện:** error rate > 2% trong cửa sổ quan sát.
- **Ảnh hưởng:** request thất bại, người dùng không nhận được câu trả lời.
- **Kiểm tra:** (1) Xem error rate và breakdown theo `error_type`. (2) Lọc event `request_failed`, lấy `correlation_id` và lỗi đã scrub. (3) Mở trace liên quan, xác định lỗi ở retrieval hay generation.
- **Mitigation:** khôi phục dependency/config vừa thay đổi; rollback prompt nếu có tương quan; tắt practice incident nếu đang bật. Theo dõi error rate cho đến khi thấp hơn 2%.
- **Slack:** `#k4-l3b-alerts`.

## LowRetrievalSuccess

- **Severity / duration:** warning, 10 phút liên tục.
- **Điều kiện:** retrieval success rate < 90%.
- **Ảnh hưởng:** câu trả lời thiếu context hoặc request lỗi khi retrieval không sẵn sàng.
- **Kiểm tra:** (1) Xác nhận mẫu số retrieval trên dashboard. (2) Lọc log `tool_name=retrieval` và `tool_success=false` theo khoảng thời gian. (3) Mở trace cùng correlation ID, xem retrieval observation và tình trạng nguồn dữ liệu.
- **Mitigation:** kiểm tra khả dụng/cấu hình kho retrieval, khôi phục cấu hình gần nhất; nếu đang chạy practice failure scenario thì tắt scenario; xác nhận success rate vượt 90%.
- **Slack:** `#k4-l3b-alerts`.
