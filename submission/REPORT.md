# Báo cáo cá nhân — K4-L3B Day 13 Monitoring & LLMOps

> Mỗi học viên hoàn thiện một file duy nhất này. Khi dẫn evidence, dùng đường dẫn tương đối, ví dụ `evidence/07-trace-waterfall.png`.

## 1. Thông tin học viên

- **Họ và tên:** Nguyễn Thị Thùy Dương
- **MSSV:** 2A202602905
- **Lớp:** K4-L3B
- **Repository URL:** https://github.com/ntthduong/K4-L3-DAY13-NguyenThiThuyDuong-2A202602905-Monitoring-LLMOps
- **Commit SHA cuối:** đối chiếu theo HEAD được nộp trên LMS và GitHub Actions của HEAD đó
- **Challenge ID:** `day13-k4-l3b-monitoring-llmops-v1`
- **Tên project Langfuse cá nhân:** `day13-k4-l3b-2A202602905`

## 2. Evidence index

Điền đúng đường dẫn tới evidence thực tế. Có thể đổi tên hoặc dùng nhiều ảnh nếu cần.

| Evidence | Đường dẫn |
|---|---|
| Pytest cuối | `evidence/01-pytest.txt` |
| Log validator | `evidence/02-log-validator.png` |
| Dashboard validator | `evidence/03-dashboard-validator.png` |
| Structured log | `evidence/04-structured-log.png` |
| Correlation ID response header | `evidence/04b-correlation-header.png` |
| PII redaction | `evidence/05-pii-redaction.png` |
| Trace list | `evidence/06-trace-list.png` |
| Trace waterfall | `evidence/07-trace-waterfall.png` |
| Trace metadata | `evidence/08-trace-metadata.png` và `evidence/08-trace-metadata.txt` |
| Prompt versions | `evidence/09-prompt-versions.png` và `evidence/09-prompt-versions.txt` |
| Prompt rollback | `evidence/10-prompt-rollback.png` và `evidence/10-prompt-rollback.txt` |
| Dashboard runtime | `evidence/11a-dashboard-latency-errors.png`, `evidence/11b-dashboard-cost-token-quality.png` |
| Incident metric | `evidence/12-incident-metric.png` và `evidence/12-incident-metric.txt` |
| Incident log | `evidence/13-incident-log.png` và `evidence/13-incident-log.txt` |
| Incident trace | `evidence/14-incident-trace.png` và `evidence/14-incident-trace.txt` |
| Bonus cost comparison | `evidence/15-cost-before-after.txt` |
| Pre-submission automation | `evidence/16-pre-submission-check.txt` |

## 3. Kết quả kỹ thuật

| Nội dung | Baseline | Kết quả cuối | Nhận xét |
|---|---|---|---|
| `validate_logs.py` | 30/100 | 100/100 | 0 thiếu field/enrichment; 0 PII leak |
| `validate_dashboard.py` | Chưa đủ contract | 6/6 panel | Đủ sáu nhóm metric bắt buộc |
| `pytest` | 26 passed ở CP1 | 36+ passed | Có test dashboard failure, cost comparator và submission checker |
| Số traces hợp lệ | 0 | Tối thiểu 10 | Workload baseline/candidate/challenge đều tạo trace cá nhân |
| Số PII leak | Có trong baseline CP0 | 0 | Email, điện thoại, CCCD và thẻ được scrub |
| Latency P95 / TTFT P95 sau recovery | — | 154 ms / 50 ms | Incident P95 là 2659 ms |
| Retrieval success rate | — | 100% | Tính cả success và failure có `tool_success` |

## 4. Logging và PII

- **Cách tạo/nhận và truyền correlation ID:** Middleware xóa context cũ, chỉ chấp nhận `x-request-id` theo dạng `req-<8 hex>`; nếu thiếu/sai định dạng thì tạo ID mới. ID được bind vào structlog, truyền vào agent/trace, trả trong body và header `x-request-id`; header `x-response-time-ms` ghi thời gian xử lý.
- **Các metadata được ghi vào structured log:** `user_id_hash` (SHA-256 rút gọn, không ghi user ID thô), `session_id`, `feature`, `model`, `env`; các event API cùng request dùng chung metadata và `correlation_id`.
- **Cách bảo đảm PII được scrub trước khi ghi:** `scrub_event` chạy trước JSONL file writer và JSON renderer; scrubber đệ quy các string trong cấu trúc log. Pattern xử lý email, điện thoại Việt Nam, CCCD 12 số và thẻ thanh toán 16 số.
- **Cách kiểm chứng kết quả:** Baseline validator CP0 là 30/100. Sau khi triển khai, `python scripts/validate_logs.py` đạt **100/100**, không thiếu field/enrichment và không phát hiện PII leak. Bộ test cuối có từ 36 test trở lên; output chính xác được lưu tại `evidence/01-pytest.txt`.

## 5. Tracing và prompt versioning

- **Cách xác nhận traces do chính tôi tạo trong project cá nhân:** Tôi chạy workload baseline, candidate và challenge bằng key của project `day13-k4-l3b-2A202602905`. Trace list thể hiện đúng project và nhiều hơn 10 trace mới.
- **Cấu trúc root/retrieval/generation observations:** Root `lab-agent-run` chứa child `retrieval` (retriever) và `llm-generation` (generation); generation ghi model, prompt preview đã scrub, token usage và cost.
- **Cách nối trace với log:** `correlation_id` được truyền qua context trace metadata; cùng ID được ghi ở structured log và response.
- **Prompt name:** `day13-chat`.
- **Version/label baseline:** version 1, labels `baseline` và `production`.
- **Version/label candidate:** version 2, label `candidate`.
- **Trace ID của mỗi version:** baseline `b959f8dc2f37d026badad22430322af7`; candidate `5609145463eb38788da56305532a5919`.
- **Cách promote và rollback `production`:** Tôi chuyển `production` sang version 2 và tạo trace `41c06e7df601e24437d73afe45e69662`. Sau đó chuyển `production` về version 1 và tạo trace `1584fe58e6a2c9ad312840bf34fe8e6d`. Các trace đều ghi `prompt_source=langfuse`; trạng thái cuối là `production -> version 1`.

## 6. Dashboard, SLO và alerts

- **Dashboard và sáu panel:** Dashboard Streamlit đọc JSONL runtime, dùng cửa sổ 60 phút và refresh 30 giây; có latency/TTFT, traffic, errors/retrieval success, cost, tokens và quality. Retrieval success lấy mọi event có `tool_success`, kể cả `request_failed`.
- **SLO và lý do chọn:** 99.5% request thành công trong 28 ngày với latency ≤ 3000ms, theo `config/slo.yaml`; threshold cần được đối chiếu với baseline workload cá nhân.
- **Cách tính error budget:** 100% - 99.5% = 0.5%; trên 10.000 request cho phép tối đa 50 request không đạt SLO.
- **Ba alert và runbook tương ứng:** `HighLatencyP95`, `ElevatedErrorRate`, `LowRetrievalSuccess`; có duration, severity, owner, Slack channel và hướng dẫn điều tra/mitigation trong `config/alert_rules.yaml` và `docs/alerts.md`.

## 7. Điều tra challenge

- **Challenge ID:** `day13-k4-l3b-monitoring-llmops-v1`.
- **Khoảng thời gian điều tra:** 2026-09-30 18:11:55–18:13:01 UTC, tương ứng 2026-10-01 01:11:55–01:13:01 Asia/Bangkok.
- **Triệu chứng từ metrics:** 15 request incident có latency P50 2655 ms, P95/P99 2659 ms và TTFT P95 53 ms. P95 vượt threshold challenge 2000 ms, trong khi error rate 0% và retrieval success 100%.
- **Log line và correlation ID liên quan:** `response_sent` lúc `2026-09-30T18:12:37.449640Z`, `correlation_id=req-5e877d82`, latency 2659 ms, TTFT 52 ms.
- **Trace ID và span gây ảnh hưởng:** trace `4e470655fe5c0284b1ae86b0d9d25670`. Root mất 2,660 giây; retrieval mất 2,502 giây; generation chỉ mất 0,154 giây.
- **Root cause:** incident `rag_slow` mô phỏng dependency retrieval chậm bằng thời gian chờ 2,5 giây. Metric, log và trace cùng chỉ vào retrieval.
- **Fix action:** tắt incident/khôi phục dependency retrieval và chạy lại cùng workload. Recovery P95 giảm còn 154 ms, TTFT P95 còn 50 ms.
- **Preventive measure:** giữ alert tail latency, lọc request vượt threshold bằng correlation ID, đặt timeout/circuit breaker và theo dõi riêng latency của retrieval observation.

## 8. Giải thích và tự đánh giá

- **Một quyết định kỹ thuật quan trọng và lý do:** correlation ID được bind ngay ở middleware, còn PII được scrub trước mọi renderer/file writer. Nhờ vậy, mọi event nối được với trace mà dữ liệu nhạy cảm không chạm vào sink.
- **Một lỗi/blocker đã gặp:** trace ban đầu ghi `prompt_source=local-fallback` vì managed prompt/label chưa đầy đủ. Ngoài ra endpoint trace legacy trả HTTP 410 cho organization Langfuse mới.
- **Cách tìm nguyên nhân và xử lý:** kiểm tra key/project mà không in secret, tạo đúng version/labels, khởi động tiến trình mới để tránh cache 60 giây và xác nhận `prompt_source=langfuse`. Với API, chuyển sang Observations API v2.
- **Cách hiểu luồng Metrics → Logs → Traces:** metrics xác định triệu chứng/time window; log chọn request cụ thể bằng correlation ID; trace cùng ID phân rã thời gian từng bước; span bất thường cung cấp root cause kiểm chứng được.
- **Vai trò của prompt version, token/cost, SLO hoặc rollback trong vận hành LLM:** version giúp truy ngược request và so sánh cost; label cho phép promote/rollback không đổi code; token/cost là guardrail; SLO/error budget xác định mức reliability chấp nhận được.
- **Điều quan trọng nhất đã học:** validator chỉ kiểm tra contract; bằng chứng runtime và liên kết ba lớp observability mới chứng minh hệ thống điều tra được sự cố.
- **Hạn chế hoặc phần chưa hoàn thành, nếu có:** LLM và retrieval là simulator nên latency/cost tuyệt đối không đại diện production; quy trình đo, liên kết ID, versioning và rollback vẫn áp dụng như nhau.

## 9. Bonus

### Cost optimization

Hai prompt chạy cùng 100 request, cùng concurrency và tập query. Candidate rút gọn phần cố định nhưng giữ đủ ba biến prompt:

- input tokens trung bình 33,80 → 31,60, giảm 6,51%;
- input cost 0,010140 → 0,009480 USD, giảm 6,51%;
- total/average cost giảm 1,11%;
- quality trung bình giữ 0,880 và error rate giữ 0%;
- comparator chỉ PASS nếu request count bằng nhau, cost giảm và quality/error không xấu đi.

### Submission automation

- `scripts/pre_submission_check.py` chạy tests/validators, kiểm tra evidence, placeholder, link hỏng, file cấm và secret trong tracked files.
- GitHub Actions chạy Python 3.11 và checker ở chế độ CI trên mỗi push/PR.
- `scripts/export_runtime_evidence.py` xuất evidence đã scrub từ structured log và Langfuse Observations API v2.
- `scripts/capture_dashboard.py` chụp dashboard sau khi Streamlit render các chart lazy-loaded.

## 10. Checklist trước khi nộp

- [x] Kết quả và evidence được tạo từ source hiện tại; CI kiểm tra SHA được push.
- [x] Tất cả ảnh/output mở được bằng đường dẫn tương đối.
- [x] Incident evidence nối đúng metric → log → trace bằng `req-5e877d82`.
- [x] Trace/prompt evidence thuộc project Langfuse cá nhân và không lộ secret.
- [x] Repository chạy lại được theo README và có pre-submission automation.
- [x] Secret, challenge config, runtime logs và PII thô không được Git track.
- [ ] URL repo và commit SHA cuối cần được nộp trên LMS/Codelabs sau khi push hoàn tất.
