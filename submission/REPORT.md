# Báo cáo cá nhân — K4-L3B Day 13 Monitoring & LLMOps

## 1. Thông tin học viên và bản nộp

- **Họ và tên:** Nguyễn Thị Thùy Dương
- **MSSV:** 2A202602905
- **Lớp:** K4-L3B
- **Repository:** [K4-L3-DAY13-NguyenThiThuyDuong-2A202602905-Monitoring-LLMOps](https://github.com/ntthduong/K4-L3-DAY13-NguyenThiThuyDuong-2A202602905-Monitoring-LLMOps)
- **Commit đã chạy full CI:** `600f63aa471cf2d3eceeb630fb8ec680190dea77`
- **Commit dùng để nộp:** SHA của `HEAD` trên `origin/main` được ghi trên VLearn LMS/Codelabs sau lần push cuối.
- **Challenge ID:** `day13-k4-l3b-monitoring-llmops-v1`
- **Langfuse project cá nhân:** `day13-k4-l3b-2A202602905`

## 2. Tổng hợp kết quả

| Hạng mục | Baseline | Kết quả cuối | Evidence |
|---|---:|---:|---|
| Pytest | 26 tests pass ở CP1 | **36 tests pass** | [01-pytest.txt](evidence/01-pytest.txt) |
| Log validator | 30/100 | **100/100**, 0 PII leak | [02-log-validator.png](evidence/02-log-validator.png) |
| Dashboard validator | Chưa đủ contract | **6/6 panel** | [03-dashboard-validator.png](evidence/03-dashboard-validator.png) |
| Langfuse traces | 0 trace hợp lệ | **Tối thiểu 10 trace cá nhân** | [06-trace-list.png](evidence/06-trace-list.png) |
| Correlation | Chưa xuyên suốt | Header, log và trace dùng cùng `correlation_id` | [04b](evidence/04b-correlation-header.png), [08](evidence/08-trace-metadata.png) |
| PII protection | PII mẫu còn xuất hiện | Email, điện thoại, CCCD và thẻ được scrub trước sink | [05-pii-redaction.png](evidence/05-pii-redaction.png) |
| Dashboard runtime | Thiếu dữ liệu/panel | Đủ latency, TTFT, traffic, errors, retrieval, cost, tokens, quality | [11a](evidence/11a-dashboard-latency-errors.png), [11b](evidence/11b-dashboard-cost-token-quality.png) |
| Challenge recovery | P95 incident 2659 ms | **P95 154 ms**, TTFT P95 50 ms | [12-incident-metric.png](evidence/12-incident-metric.png) |
| Pre-submission gate | Chạy thủ công rời rạc | **PASS** tests, validators, evidence và secret scan | [16-pre-submission-check.txt](evidence/16-pre-submission-check.txt) |

## 3. Logging, correlation và bảo vệ PII

### 3.1 Correlation ID xuyên suốt request

Middleware xóa context cũ ở đầu mỗi request, kiểm tra `x-request-id` theo định dạng `req-<8-hex>` và sinh ID mới nếu header thiếu hoặc không hợp lệ. ID được bind vào `structlog`, truyền vào agent và Langfuse trace, rồi trả về cả response body lẫn header `x-request-id`. Header `x-response-time-ms` ghi tổng thời gian xử lý. Vì context được reset trước khi bind, các request đồng thời không rò correlation context sang nhau.

Mỗi structured log có `timestamp`, `event`, `correlation_id`, `user_id_hash`, `session_id`, `feature`, `model` và `env`. User ID chỉ được lưu dưới dạng SHA-256 rút gọn. Evidence runtime: [structured log](evidence/04-structured-log.png) và [response header](evidence/04b-correlation-header.png).

### 3.2 PII được scrub trước khi ghi

Processor `scrub_event` chạy trước JSON renderer và JSONL file writer, đồng thời duyệt đệ quy các chuỗi trong cấu trúc log. Các rule xử lý đủ bốn loại dữ liệu theo rubric: email, số điện thoại Việt Nam, CCCD 12 số và thẻ thanh toán 16 số. Vì redaction nằm trước sink, cả console log lẫn file log đều nhận dữ liệu đã che.

Kết quả runtime chứa input PII giả và output đã redact được lưu tại [05-pii-redaction.png](evidence/05-pii-redaction.png). Log validator cuối đạt **100/100**, không thiếu field/enrichment và phát hiện **0 PII leak**.

## 4. Tracing và managed prompt

### 4.1 Cấu trúc trace và liên kết với log

Workload baseline, candidate và challenge được chạy bằng project cá nhân `day13-k4-l3b-2A202602905`. Trace root `lab-agent-run` chứa hai child observation đúng quan hệ cha-con:

1. `retrieval`: ghi trạng thái tool, thời gian truy xuất và kết quả đã scrub.
2. `llm-generation`: ghi model, prompt metadata, token usage, cost và output đã scrub.

`correlation_id` trong trace metadata trùng với structured log, cho phép đi từ một log line đến đúng trace. Evidence gồm [trace list](evidence/06-trace-list.png), [waterfall](evidence/07-trace-waterfall.png) và [metadata](evidence/08-trace-metadata.png) / [text export](evidence/08-trace-metadata.txt).

### 4.2 Prompt v1/v2, promote và rollback

Managed prompt `day13-chat` dùng đủ ba biến `{{feature}}`, `{{docs}}`, `{{message}}`. Source lấy prompt theo label từ Langfuse và trace ghi `prompt_source=langfuse`; version không được hard-code trong ứng dụng.

| Lần chạy | Version/label | Trace ID | Kết quả |
|---|---|---|---|
| Baseline | v1 / `baseline` | `b959f8dc2f37d026badad22430322af7` | Prompt policy đầy đủ |
| Candidate | v2 / `candidate` | `5609145463eb38788da56305532a5919` | Prompt rút gọn, tối đa ba câu |
| Promote | v2 / `production` | `41c06e7df601e24437d73afe45e69662` | Production dùng candidate |
| Rollback | v1 / `production` | `1584fe58e6a2c9ad312840bf34fe8e6d` | Production quay về baseline |

Trạng thái cuối là `baseline → v1`, `candidate → v2`, `production → v1`. Evidence: [prompt versions](evidence/09-prompt-versions.png) / [text](evidence/09-prompt-versions.txt) và [promote/rollback](evidence/10-prompt-rollback.png) / [text](evidence/10-prompt-rollback.txt).

## 5. Dashboard, SLO và alerts

### 5.1 Dashboard sáu nhóm tín hiệu

Dashboard Streamlit đọc structured JSONL, dùng time range 60 phút và refresh 30 giây. Sáu nhóm metric gồm:

1. Latency P50/P95/P99 và TTFT P95, đơn vị ms, có đường threshold.
2. Traffic theo request/phút.
3. Error rate và retrieval success rate theo phần trăm.
4. Tổng/average cost theo USD.
5. Input/output token usage.
6. Average quality score.

Retrieval success được tính trên mọi event có `tool_success`, gồm cả `response_sent` và `request_failed`, nên tool failure làm tỷ lệ giảm đúng. Dashboard runtime: [11a-dashboard-latency-errors.png](evidence/11a-dashboard-latency-errors.png) và [11b-dashboard-cost-token-quality.png](evidence/11b-dashboard-cost-token-quality.png). Contract đạt 6/6 tại [03-dashboard-validator.png](evidence/03-dashboard-validator.png).

### 5.2 SLO và error budget

[SLO configuration](../config/slo.yaml) đặt mục tiêu **99,5% request thành công và có latency ≤ 3000 ms trong cửa sổ 28 ngày**. Error budget là `100% - 99,5% = 0,5%`; với 10.000 request, tối đa 50 request được phép lỗi hoặc vượt 3000 ms. Ngưỡng này bảo vệ trải nghiệm tail latency và vẫn dành một ngân sách nhỏ cho sự cố hoặc thay đổi có kiểm soát.

### 5.3 Alerts và runbook

[Alert rules](../config/alert_rules.yaml) có đủ duration, severity, owner, Slack channel và runbook:

| Alert | Điều kiện | Duration | Severity |
|---|---|---:|---|
| `HighLatencyP95` | P95 latency > 3000 ms | 5 phút | warning |
| `ElevatedErrorRate` | Error rate > 2% | 5 phút | critical |
| `LowRetrievalSuccess` | Retrieval success < 90% | 10 phút | warning |

Ba alert đều symptom-based và dẫn đến các bước triage/mitigation cụ thể trong [docs/alerts.md](../docs/alerts.md).

## 6. Điều tra challenge: Metrics → Logs → Traces → Root cause

### 6.1 Metrics xác định triệu chứng và time window

- **Challenge ID:** `day13-k4-l3b-monitoring-llmops-v1`.
- **Incident:** `rag_slow`, feature `monitoring`.
- **UTC:** 2026-09-30 18:11:55–18:13:01.
- **Asia/Bangkok:** 2026-10-01 01:11:55–01:13:01.
- **15 request trong incident:** P50 2655 ms, P95/P99 2659 ms, TTFT P95 53 ms.
- **Tín hiệu phân biệt:** latency vượt threshold challenge 2000 ms, trong khi error rate 0% và retrieval success 100%.

Evidence metric/time range: [12-incident-metric.png](evidence/12-incident-metric.png) / [text](evidence/12-incident-metric.txt).

### 6.2 Logs chọn đúng request bất thường

Trong time window trên, event `response_sent` lúc `2026-09-30T18:12:37.449640Z` có:

- `correlation_id=req-5e877d82`;
- latency 2659 ms;
- TTFT 52 ms;
- request thành công nhưng tổng latency cao bất thường.

Evidence: [13-incident-log.png](evidence/13-incident-log.png) / [text](evidence/13-incident-log.txt).

### 6.3 Trace khoanh vùng root cause

Trace `4e470655fe5c0284b1ae86b0d9d25670` có cùng `correlation_id=req-5e877d82`. Root mất 2,660 giây; child `retrieval` mất 2,502 giây; child `llm-generation` chỉ mất 0,154 giây. Retrieval chiếm khoảng 94% tổng thời gian, khớp trực tiếp với metric và log.

**Root cause:** incident `rag_slow` làm dependency retrieval chờ thêm 2,5 giây. TTFT, error rate và generation bình thường, nên bằng chứng xác định retrieval là nguyên nhân chính.

**Fix action:** tắt incident, khôi phục retrieval dependency và chạy lại cùng workload. Sau recovery, P95 giảm từ 2659 ms xuống **154 ms**, TTFT P95 còn **50 ms**.

**Preventive measure:** duy trì alert tail latency; dùng correlation ID để lọc request vượt ngưỡng; áp dụng timeout và circuit breaker cho retrieval; theo dõi riêng retrieval observation để phát hiện dependency degradation sớm.

Evidence: [14-incident-trace.png](evidence/14-incident-trace.png) / [text](evidence/14-incident-trace.txt).

## 7. Quyết định kỹ thuật, blocker và kiến thức vận hành

### 7.1 Quyết định kỹ thuật chính

Tôi bind correlation context ngay tại middleware và đặt PII processor trước mọi renderer/file writer. Thiết kế này tạo một định danh xuyên suốt response, logs và traces, đồng thời bảo đảm dữ liệu nhạy cảm được loại bỏ trước khi đi vào sink. Dashboard, incident investigation và Langfuse lookup vì thế dùng cùng một khóa đối chiếu có thể kiểm chứng.

### 7.2 Blocker đã xử lý

Endpoint trace legacy trả HTTP 410 trên Langfuse organization mới. Tôi kiểm tra project/key mà không in secret, chuyển phần export sang Observations API v2, rồi xác nhận lại root/retrieval/generation, prompt version, tokens và cost. Với cache managed prompt 60 giây, tôi dùng tiến trình API mới sau mỗi lần đổi label để trace promote/rollback lấy đúng version. Blocker đã được xử lý và trạng thái cuối được kiểm chứng bằng các trace ID ở mục 4.2.

### 7.3 Cách hiểu chuỗi observability

Metrics trả lời **hệ thống bất thường ở đâu và khi nào**; logs chọn **request cụ thể** trong time window bằng `correlation_id`; trace cùng ID phân rã **thời gian từng bước**; observation bất thường cung cấp **root cause có thể kiểm chứng**. Trong challenge, chuỗi đó là P95 2659 ms → log `req-5e877d82` → trace `4e470...` → retrieval 2,502 giây → `rag_slow`.

### 7.4 Vai trò của prompt, cost, SLO và rollback

- Prompt version giúp tái hiện chính xác policy đã tạo ra từng response.
- Label cho phép promote/rollback mà không sửa hoặc deploy lại code.
- Token và cost là guardrail để tối ưu prompt trên cùng workload mà vẫn giữ quality/error rate.
- SLO và error budget biến độ tin cậy thành mục tiêu đo được; alerts phát hiện sớm khi vượt ngân sách vận hành.
- Trace gắn prompt name/version/label giúp nối thay đổi prompt với latency, quality và cost.

### 7.5 Điều học được và giới hạn còn lại

Điều quan trọng nhất là validator xác nhận contract, còn evidence runtime và chuỗi Metrics → Logs → Traces chứng minh hệ thống thực sự điều tra được sự cố. Lab dùng LLM/retrieval simulator để kết quả lặp lại ổn định, nên các con số latency/cost tuyệt đối được dùng cho môi trường lab; cách đo, versioning, correlation, SLO và rollback áp dụng tương tự khi thay bằng provider production.

## 8. Bonus

### 8.1 Cost optimization trên cùng workload

Baseline và candidate chạy cùng tập query, cùng concurrency và **100 request mỗi phía**. Candidate rút gọn phần policy cố định nhưng giữ đủ ba biến và ý nghĩa an toàn.

| Metric | Baseline | Candidate | Thay đổi |
|---|---:|---:|---:|
| Input tokens trung bình | 33,80 | 31,60 | **-6,51%** |
| Tổng input cost | 0,010140 USD | 0,009480 USD | **-6,51%** |
| Average cost | 0,000596 USD | 0,000590 USD | **-1,11%** |
| Total cost | 0,059640 USD | 0,058980 USD | **-1,11%** |
| Latency P95 | 162 ms | 160 ms | **-1,23%** |
| Quality trung bình | 0,880 | 0,880 | 0,00 |
| Error rate | 0% | 0% | 0 điểm % |

Comparator chỉ PASS khi hai phía có cùng request count, candidate giảm input tokens/input cost/average total cost, quality không giảm quá 0,02 và error rate không tăng. Chi tiết: [15-cost-before-after.txt](evidence/15-cost-before-after.txt).

### 8.2 Automation và CI

- `scripts/pre_submission_check.py` chạy pytest, validators, kiểm tra evidence, placeholder, link hỏng, forbidden files và secret trong tracked files.
- Chế độ `--ci` bỏ phụ thuộc runtime/Langfuse nhưng vẫn giữ tests, dashboard contract, cấu trúc submission, forbidden-file và secret scan.
- GitHub Actions dùng Python 3.11 và chạy checker trên mỗi push/pull request.
- `scripts/export_runtime_evidence.py` xuất evidence đã scrub từ structured log và Langfuse Observations API v2.
- `scripts/capture_dashboard.py` chụp dashboard sau khi Streamlit render chart.

Local gate đạt PASS tại [16-pre-submission-check.txt](evidence/16-pre-submission-check.txt); CI xanh tại [17-ci-final-sha.png](evidence/17-ci-final-sha.png).

## 9. Evidence index đầy đủ

| Mã | Evidence |
|---|---|
| 01 | [Pytest cuối](evidence/01-pytest.txt) |
| 02 | [Log validator](evidence/02-log-validator.png) |
| 03 | [Dashboard validator](evidence/03-dashboard-validator.png) |
| 04 | [Structured log](evidence/04-structured-log.png), [correlation header](evidence/04b-correlation-header.png) |
| 05 | [PII redaction runtime](evidence/05-pii-redaction.png) |
| 06 | [Danh sách trace](evidence/06-trace-list.png) |
| 07 | [Trace waterfall](evidence/07-trace-waterfall.png) |
| 08 | [Trace metadata](evidence/08-trace-metadata.png), [text](evidence/08-trace-metadata.txt) |
| 09 | [Prompt versions/labels](evidence/09-prompt-versions.png), [text](evidence/09-prompt-versions.txt) |
| 10 | [Promote/rollback](evidence/10-prompt-rollback.png), [text](evidence/10-prompt-rollback.txt) |
| 11 | [Latency/errors/retrieval](evidence/11a-dashboard-latency-errors.png), [cost/tokens/quality](evidence/11b-dashboard-cost-token-quality.png) |
| 12 | [Incident metric](evidence/12-incident-metric.png), [text](evidence/12-incident-metric.txt) |
| 13 | [Incident log](evidence/13-incident-log.png), [text](evidence/13-incident-log.txt) |
| 14 | [Incident trace](evidence/14-incident-trace.png), [text](evidence/14-incident-trace.txt) |
| 15 | [Cost before/after](evidence/15-cost-before-after.txt) |
| 16 | [Pre-submission check](evidence/16-pre-submission-check.txt) |
| 17 | [GitHub Actions xanh](evidence/17-ci-final-sha.png) |

## 10. Checklist trước khi nộp

- [x] Source, tests, config, report và evidence thuộc repository cá nhân.
- [x] Pytest pass; log validator 100/100; dashboard validator 6/6.
- [x] Structured log và trace nối được bằng correlation ID.
- [x] PII giả được redact trước khi render/ghi file; evidence không chứa PII thô.
- [x] Có tối thiểu 10 trace cá nhân, waterfall, metadata, prompt v1/v2 và rollback thật.
- [x] Dashboard có dữ liệu, đủ sáu nhóm metric, time range, đơn vị và threshold.
- [x] SLO, error budget, ba alert và runbook đầy đủ.
- [x] Incident evidence nối cùng metric → log → trace → root cause.
- [x] Bonus cost dùng cùng workload và giữ nguyên quality/error rate.
- [x] Pre-submission automation và GitHub Actions đều PASS.
- [x] `.env`, `config/challenge.json`, runtime logs, benchmark logs, secret và cache không được Git track.
- [x] Tất cả đường dẫn evidence là đường dẫn tương đối và mở được trên GitHub.
- [ ] Ghi URL repository và SHA của commit `HEAD` cuối trên VLearn LMS/Codelabs.
