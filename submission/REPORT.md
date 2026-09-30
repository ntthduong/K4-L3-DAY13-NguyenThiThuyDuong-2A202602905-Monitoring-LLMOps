# Báo cáo cá nhân — K4-L3B Day 13 Monitoring & LLMOps

> Mỗi học viên hoàn thiện một file duy nhất này. Khi dẫn evidence, dùng đường dẫn tương đối, ví dụ `evidence/07-trace-waterfall.png`.

## 1. Thông tin học viên

- **Họ và tên:**
- **MSSV:**
- **Lớp:** K4-L3B
- **Repository URL:**
- **Commit SHA cuối:**
- **Challenge ID:**
- **Tên project Langfuse cá nhân:** `day13-k4-l3b-<MSSV>`

## 2. Evidence index

Điền đúng đường dẫn tới evidence thực tế. Có thể đổi tên hoặc dùng nhiều ảnh nếu cần.

| Evidence | Đường dẫn |
|---|---|
| Pytest cuối | Chưa chụp — kết quả CP1: 26 passed |
| Log validator | Chưa chụp — kết quả CP1: 100/100 |
| Dashboard validator | `evidence/03-dashboard-validator.png` |
| Structured log | `evidence/04-structured-log.png` |
| Correlation ID response header | `evidence/04b-correlation-header.png` |
| PII redaction | `evidence/05-pii-redaction.png` |
| Trace list | `evidence/06-trace-list.png` |
| Trace waterfall | `evidence/07-trace-waterfall.png` |
| Trace metadata | `evidence/08-trace-metadata.png` |
| Prompt versions | `evidence/09-prompt-versions.png` |
| Prompt rollback | `evidence/10-prompt-rollback.png` |
| Dashboard runtime | `evidence/11-dashboard-overview.png` |
| Incident metric | `evidence/12-incident-metric.png` |
| Incident log | `evidence/13-incident-log.png` |
| Incident trace | `evidence/14-incident-trace.png` |

## 3. Kết quả kỹ thuật

| Nội dung | Baseline | Kết quả cuối | Nhận xét |
|---|---|---|---|
| `validate_logs.py` | 30/100 | CP1: 100/100 | 10 correlation ID; 0 thiếu field/enrichment; 0 PII leak |
| `validate_dashboard.py` | | | |
| `pytest` | | | |
| Số traces hợp lệ | | | |
| Số PII leak | | | |
| Latency P95 / TTFT P95 | | | |
| Retrieval success rate | | | |

## 4. Logging và PII

- **Cách tạo/nhận và truyền correlation ID:** Middleware xóa context cũ, chỉ chấp nhận `x-request-id` theo dạng `req-<8 hex>`; nếu thiếu/sai định dạng thì tạo ID mới. ID được bind vào structlog, truyền vào agent/trace, trả trong body và header `x-request-id`; header `x-response-time-ms` ghi thời gian xử lý.
- **Các metadata được ghi vào structured log:** `user_id_hash` (SHA-256 rút gọn, không ghi user ID thô), `session_id`, `feature`, `model`, `env`; các event API cùng request dùng chung metadata và `correlation_id`.
- **Cách bảo đảm PII được scrub trước khi ghi:** `scrub_event` chạy trước JSONL file writer và JSON renderer; scrubber đệ quy các string trong cấu trúc log. Pattern xử lý email, điện thoại Việt Nam, CCCD 12 số và thẻ thanh toán 16 số.
- **Cách kiểm chứng kết quả:** Baseline validator CP0 là 30/100, được lưu tại `../data/logs.baseline-cp0.jsonl`. Sau khi triển khai, `python scripts/load_test.py` tạo 10 request mới và `python scripts/validate_logs.py` đạt **100/100**: 21 records (gồm `app_started`), 0 record thiếu field bắt buộc, 0 record thiếu enrichment, 10 correlation ID duy nhất, 0 PII leak. `python -m pytest -q`: **26 passed**. Log runtime hiện tại: `../data/logs.jsonl`.

## 5. Tracing và prompt versioning

- **Cách xác nhận traces do chính tôi tạo trong project cá nhân:** Chưa thực hiện; cần chạy workload sau khi cấu hình project Langfuse cá nhân.
- **Cấu trúc root/retrieval/generation observations:** Root `lab-agent-run` chứa child `retrieval` (retriever) và `llm-generation` (generation); generation ghi model, prompt preview đã scrub, token usage và cost.
- **Cách nối trace với log:** `correlation_id` được truyền qua context trace metadata; cùng ID được ghi ở structured log và response.
- **Prompt name:**
- **Version/label baseline:**
- **Version/label candidate:**
- **Trace ID của mỗi version:**
- **Cách promote và rollback `production`:**

## 6. Dashboard, SLO và alerts

- **Dashboard và sáu panel:** Dashboard runtime Streamlit tại `app/dashboard.py`, nguồn `data/logs.jsonl`; có latency/TTFT, traffic, errors/retrieval success, cost, tokens và quality. Cần chụp ảnh runtime sau khi chạy.
- **SLO và lý do chọn:** 99.5% request thành công trong 28 ngày với latency ≤ 3000ms, theo `config/slo.yaml`; threshold cần được đối chiếu với baseline workload cá nhân.
- **Cách tính error budget:** 100% - 99.5% = 0.5%; trên 10.000 request cho phép tối đa 50 request không đạt SLO.
- **Ba alert và runbook tương ứng:** `HighLatencyP95`, `ElevatedErrorRate`, `LowRetrievalSuccess`; có duration, severity, owner, Slack channel và hướng dẫn điều tra/mitigation trong `config/alert_rules.yaml` và `docs/alerts.md`.

> Ví dụ cách viết error budget: "SLO 99.5% trong 28 ngày nghĩa là error budget 0.5%. Nếu workload có 10,000 request thì tối đa 50 request được phép lỗi hoặc chậm hơn ngưỡng SLO."

## 7. Điều tra challenge

- **Challenge ID:**
- **Khoảng thời gian điều tra:**
- **Triệu chứng từ metrics:**
- **Log line và correlation ID liên quan:**
- **Trace ID và span gây ảnh hưởng:**
- **Root cause:**
- **Fix action:**
- **Preventive measure:**

> Gợi ý cách viết ngắn, không thay cho evidence thực tế: "Metric cho thấy `[latency/error/cost/quality]` bất thường trong `[khoảng thời gian]`. Log line `[event]` có `correlation_id=[...]` đại diện cho request bị ảnh hưởng. Trace cùng `correlation_id` cho thấy span `[retrieval/generation/prompt/tool]` có dấu hiệu `[chậm/lỗi/token tăng]`. Root cause là `[nguyên nhân suy ra từ evidence]`. Fix action là `[hành động khôi phục]`; preventive measure là `[alert/runbook/test/guardrail để ngăn tái diễn]`."

## 8. Giải thích và tự đánh giá

- **Một quyết định kỹ thuật quan trọng và lý do:**
- **Một lỗi/blocker đã gặp:**
- **Cách tìm nguyên nhân và xử lý:**
- **Cách hiểu luồng Metrics → Logs → Traces:**
- **Vai trò của prompt version, token/cost, SLO hoặc rollback trong vận hành LLM:**
- **Điều quan trọng nhất đã học:**
- **Hạn chế hoặc phần chưa hoàn thành, nếu có:**

## 9. Checklist trước khi nộp

- [ ] Kết quả và evidence thuộc commit SHA cuối.
- [ ] Tất cả ảnh/output mở được bằng đường dẫn tương đối.
- [ ] Incident evidence nối đúng metric → log → trace.
- [ ] Trace/prompt evidence thuộc project Langfuse cá nhân và ảnh không lộ key/secret.
- [ ] Repository chạy lại được theo README.
- [ ] Không có secret, API key, PII thô hoặc evidence của người khác/lớp khác.
- [ ] URL repo và commit SHA cuối đã được nộp trên LMS/Codelabs.
