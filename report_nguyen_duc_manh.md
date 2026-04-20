# Báo Cáo Cá Nhân – Day 13 Observability Lab

> **Sinh viên:** Nguyễn Đức Mạnh  
> **Lớp / Nhóm:** C401 – Table E1  
> **Ngày nộp:** 20/04/2026  
> **Repository:** Lab_13_C401_Table_E1  

---

## 1. Tổng Quan Công Việc Cá Nhân

Trong Lab 13 về **Observability & Alert Management**, tôi đảm nhận toàn bộ pipeline từ thiết lập nền tảng ứng dụng đến hệ thống cảnh báo thời gian thực. Cụ thể, tôi hoàn thành các hạng mục sau:

| # | Hạng mục | File chính | Trạng thái |
|---|---|---|---|
| 1 | Correlation ID Middleware | `app/middleware.py` | ✅ Hoàn thành |
| 2 | Structured Logging + PII Scrubbing | `app/logging_config.py`, `app/pii.py` | ✅ Hoàn thành |
| 3 | Metrics Engine (P95, P99, cost, quality) | `app/metrics.py` | ✅ Hoàn thành |
| 4 | FastAPI App – Enrich logs, quota, cost guard | `app/main.py` | ✅ Hoàn thành |
| 5 | Agent Pipeline + Langfuse Tracing | `app/agent.py` | ✅ Hoàn thành |
| 6 | Alert Monitor (real-time, 5 rules, JSONL) | `scripts/alert_monitor.py` | ✅ Hoàn thành |
| 7 | Alert Rules Config + SLO Config | `config/alert_rules.yaml`, `config/slo.yaml` | ✅ Hoàn thành |
| 8 | Bằng chứng alert kích hoạt | `data/alerts.jsonl` | ✅ Có bằng chứng |

---

## 2. Chi Tiết Từng Phần Đã Thực Hiện

---

### 2.1 Correlation ID Middleware (`app/middleware.py`)

**Mục tiêu:** Đảm bảo mọi request đều có một `x-request-id` duy nhất xuyên suốt vòng đời request → đây là nền tảng để trace lỗi từ log → metrics → Langfuse.

**Những gì tôi làm:**
- Tạo class `CorrelationIdMiddleware` kế thừa `BaseHTTPMiddleware` của Starlette.
- Gọi `clear_contextvars()` **trước mỗi request** để tránh rò rỉ context giữa các request song song (concurrency leak).
- Đọc header `x-request-id` từ phía client; nếu không có thì tự sinh `req-<8-char-hex>` bằng `uuid.uuid4()`.
- Bind `correlation_id` vào **structlog contextvars** → mọi log trong request đó sẽ tự động có trường `correlation_id`.
- Gắn `correlation_id` vào `request.state` để handler downstream dùng khi trả về response.
- Đo `process_time_ms` và gắn vào response headers (`x-response-time-ms`).

```python
# Trích đoạn core logic
header_id = request.headers.get("x-request-id")
correlation_id = header_id if header_id else f"req-{uuid.uuid4().hex[:8]}"
bind_contextvars(correlation_id=correlation_id)
request.state.correlation_id = correlation_id
```

**Lý do thiết kế:**  
Format `req-<hex>` ngắn gọn, dễ grep trong log, phân biệt rõ request từ client vs. request do hệ thống tự sinh.

---

### 2.2 PII Scrubbing (`app/pii.py`)

**Mục tiêu:** Loại bỏ dữ liệu nhạy cảm khỏi log trước khi ghi ra file, tuân thủ quy định bảo vệ thông tin cá nhân.

**Những gì tôi làm:**
- Xây dựng dictionary `PII_PATTERNS` với **7 loại PII** được phát hiện bằng regex:

| Pattern | Mô tả | Ví dụ bị redact |
|---|---|---|
| `email` | Email address | `user@gmail.com` → `[REDACTED_EMAIL]` |
| `phone_vn` | Số điện thoại VN (09x, +84) | `0901234567` → `[REDACTED_PHONE_VN]` |
| `cccd` | CCCD 12 chữ số | `012345678901` → `[REDACTED_CCCD]` |
| `credit_card` | Số thẻ tín dụng 16 số | `4111-1111-1111-1111` → `[REDACTED_CREDIT_CARD]` |
| `passport` | Hộ chiếu Việt Nam (1 chữ + 7 số) | `C9876543` → `[REDACTED_PASSPORT]` |
| `student_id` | Mã sinh viên dạng VNI + 6 số | `vni123456` → `[REDACTED_STUDENT_ID]` |
| `address_ocean_park` | Địa chỉ Vinhomes Ocean Park | `12 Vinhomes Ocean Park` → `[REDACTED_ADDRESS_OCEAN_PARK]` |

- Hàm `scrub_text(text)`: áp dụng tuần tự tất cả regex lên chuỗi đầu vào.
- Hàm `summarize_text(text, max_len=80)`: scrub rồi cắt ngắn an toàn cho log preview.
- Hàm `hash_user_id(user_id)`: SHA-256 → lấy 12 ký tự hex đầu, đảm bảo `user_id` không bao giờ xuất hiện raw trong log.

```python
def scrub_text(text: str) -> str:
    safe = text
    for name, pattern in PII_PATTERNS.items():
        safe = re.sub(pattern, f"[REDACTED_{name.upper()}]", safe)
    return safe
```

---

### 2.3 Structured Logging (`app/logging_config.py`)

**Mục tiêu:** Cấu hình `structlog` để xuất log theo chuẩn JSON (JSONL) với đầy đủ context, tự động scrub PII.

**Những gì tôi làm:**
- Xây dựng `JsonlFileProcessor`: processor tùy chỉnh tự động ghi mỗi log entry ra `data/logs.jsonl` dưới dạng JSON line.
- Xây dựng `scrub_event`: processor kiểm tra và scrub PII trong field `payload` (dict) và field `event` (string) trước khi log được ghi.
- Cấu hình **processor chain** theo thứ tự:
  1. `merge_contextvars` → kéo `correlation_id`, `user_id_hash`, `session_id` tự động vào mọi log line
  2. `add_log_level` → thêm level (info/warning/error)
  3. `TimeStamper` → timestamp ISO 8601 UTC
  4. `scrub_event` (tự viết) → loại bỏ PII
  5. `JsonlFileProcessor` (tự viết) → ghi ra file
  6. `JSONRenderer` → render ra stdout

```python
structlog.configure(
    processors=[
        merge_contextvars,        # Kéo correlation_id vào mọi log
        structlog.processors.add_log_level,
        structlog.processors.TimeStamper(fmt="iso", utc=True, key="ts"),
        scrub_event,              # PII scrubbing tự viết
        JsonlFileProcessor(),     # Ghi JSONL ra file
        structlog.processors.JSONRenderer(),
    ],
    ...
)
```

---

### 2.4 Metrics Engine (`app/metrics.py`)

**Mục tiêu:** Thu thập và cung cấp các số liệu thời gian thực phục vụ alert monitor và dashboard.

**Những gì tôi làm:**
- Lưu trữ in-memory: `REQUEST_LATENCIES`, `REQUEST_COSTS`, `REQUEST_TOKENS_IN/OUT`, `QUALITY_SCORES`, `ERRORS` (Counter).
- Hàm `percentile(values, p)`: tính P50/P95/P99 latency bằng thuật toán nearest-rank.
- Hàm `snapshot()`: trả về toàn bộ metrics hiện tại qua endpoint `/metrics`:
  - `traffic`, `latency_p50/p95/p99`, `avg_cost_usd`, `total_cost_usd`
  - `tokens_in/out_total`, `error_breakdown`, `quality_avg`, `cost_violations`
- **Token quota per user**: `check_quota()` kiểm tra mỗi user không vượt 1,000 tokens; `record_user_tokens()` cập nhật sau mỗi request thành công.
- **Cost guard**: `check_cost()` kiểm tra chi phí mỗi query không vượt `$0.005`; `record_cost_violation()` đếm vi phạm.

---

### 2.5 FastAPI App (`app/main.py`)

**Mục tiêu:** Tích hợp tất cả các thành phần thành một ứng dụng FastAPI hoàn chỉnh với observability đầy đủ.

**Những gì tôi làm:**
- Mount `CorrelationIdMiddleware` → tất cả request đều có correlation ID.
- Endpoint `/chat` (POST):
  - **Bind log context**: `user_id_hash`, `session_id`, `feature`, `model`, `env` → mọi log trong request đều có context đầy đủ.
  - **Quota check**: chặn user vượt 1,000 tokens với HTTP 429 + log `quota_exceeded`.
  - **Cost guard**: chặn query vượt `$0.005` với HTTP 402 + log `cost_limit_exceeded`.
  - **Error recording**: bắt mọi exception, gọi `record_error(error_type)` rồi raise HTTP 500.
- Endpoint `/metrics` (GET): trả về snapshot metrics cho alert monitor.
- Endpoint `/incidents/{name}/enable|disable`: điều khiển kịch bản lỗi inject.
- Mount **Dashboard UI** tĩnh tại `/dashboard`.
- Log sự kiện `app_started` khi khởi động, kèm `tracing_enabled` status.

---

### 2.6 Agent Pipeline (`app/agent.py`)

**Mục tiêu:** Xây dựng pipeline RAG + LLM với tracing Langfuse đầy đủ metadata.

**Những gì tôi làm:**
- `@observe(name="lab_agent_run")`: decorator Langfuse tự động tạo trace cho mỗi lần agent chạy.
- Pipeline 6 bước: RAG retrieval → Prompt engineering → LLM generation → Quality heuristic → Langfuse enrich → Metrics record.
- `update_current_trace()`: gắn `user_id` (đã hash), `session_id`, `tags` (`["lab", feature, model]`), `metadata`.
- `update_current_generation()`: gắn input prompt, output text, `doc_count`, `quality_score`, token usage.
- Heuristic quality score: 0.5 base + cộng điểm nếu có document, độ dài hợp lý, từ khóa liên quan.

---

### 2.7 Alert Monitor (`scripts/alert_monitor.py`)

**Mục tiêu:** Xây dựng công cụ giám sát real-time tự động phát hiện vi phạm SLO và ghi bằng chứng.

**Đây là phần phức tạp nhất tôi tự viết hoàn toàn** (261 dòng). Kiến trúc gồm:

**5 Alert Rules được đánh giá mỗi poll:**

| Alert | Severity | Condition | Window |
|---|---|---|---|
| `high_latency_p95` | P2 | latency_p95 > 5000ms | 30s |
| `high_error_rate` | P1 | error_rate > 5% | 10s |
| `cost_budget_spike` | P2 | avg_cost > 2x baseline | 15s |
| `low_quality_score` | P2 | quality_avg < 0.75 | 10s |
| `tool_failure_spike` | P1 | RuntimeError delta > 3 | 10s |

**Logic sustained-window**: Alert chỉ kích hoạt khi condition vi phạm **liên tục ít nhất 50% số lần đọc trong window** → tránh false positive từ spike đơn lẻ.

```python
min_readings = max(1, int(win_s / interval) // 2)
sustained = len(window_readings) >= min_readings and all(window_readings)
```

**Tính năng:**
- **Baseline cost tự động**: lần đầu có traffic, ghi nhận `avg_cost_usd` làm baseline; 2x baseline = ngưỡng spike.
- **Alert deduplication**: `firing: set[str]` ngăn log alert trùng lặp trong khi condition vẫn vi phạm.
- **Auto-resolve**: khi condition trở về bình thường, in thông báo `[RESOLVED]` màu xanh.
- **JSONL evidence**: mỗi alert fired được append vào `data/alerts.jsonl` với timestamp UTC.
- **ANSI color output**: P1 đỏ, P2 vàng, trạng thái OK xanh → dễ scan trên terminal.
- **UTF-8 safe**: `sys.stdout.reconfigure(encoding="utf-8")` tránh lỗi UnicodeEncodeError trên Windows.

---

### 2.8 Alert Rules & SLO Config

**`config/alert_rules.yaml`** – Định nghĩa 5 alert rules với owner, type (symptom-based / cause-based), runbook link.

**`config/slo.yaml`** – Định nghĩa 4 SLI/SLO targets:

| SLI | Objective | Target Availability |
|---|---|---|
| `latency_p95_ms` | < 2500ms | 99.0% |
| `error_rate_pct` | < 1% | 99.5% |
| `daily_cost_usd` | < $5.00 | 100% |
| `quality_score_avg` | > 0.85 | 95.0% |

---

## 3. Bằng Chứng Kỹ Thuật

### 3.1 Alerts đã kích hoạt (data/alerts.jsonl)

```jsonl
{"ts": "2026-04-20T09:30:19.463094+00:00", "alert": "high_error_rate", "severity": "P1", "value": "error_rate=33.3%", "condition": "error_rate_pct > 5", "runbook": "docs/alerts.md#2-high-error-rate"}
{"ts": "2026-04-20T09:41:16.103045+00:00", "alert": "low_quality_score", "severity": "P2", "value": "quality_avg=0.000", "condition": "quality_avg < 0.75", "runbook": "docs/alerts.md#4-low-quality-score"}
```

Hai alert đã được kích hoạt trong quá trình load test:
- **`high_error_rate` (P1)**: Error rate đạt 33.3% khi inject incident → vượt ngưỡng 5% → alert bắn ngay.
- **`low_quality_score` (P2)**: Quality score = 0.000 khi RAG bị lỗi hoàn toàn → dưới ngưỡng 0.75.

### 3.2 Logs có Correlation ID

File `data/logs.jsonl` chứa các log entry với format đầy đủ, ví dụ:
```json
{
  "correlation_id": "req-a3f8b21c",
  "user_id_hash": "5f2d8a1e3b9c",
  "session_id": "sess-001",
  "feature": "chat",
  "model": "claude-sonnet-4-5",
  "env": "dev",
  "event": "response_sent",
  "ts": "2026-04-20T09:28:15.123Z",
  "latency_ms": 342
}
```

### 3.3 PII đã được redact

Ví dụ log entry: input chứa `"email tôi là user@example.com số điện thoại 0901234567"` → sau `scrub_text()`:  
```
"email tôi là [REDACTED_EMAIL] số điện thoại [REDACTED_PHONE_VN]"
```

---

## 4. Incident Response – Phân Tích Sự Cố

**Kịch bản inject:** `high_error_rate` (error_rate = 33.3%)

**Flow điều tra:**
1. **Metrics** → `/metrics` endpoint cho thấy `error_breakdown: {"RuntimeError": N}` tăng đột ngột.
2. **Alert** → `alert_monitor.py` bắn `high_error_rate` [P1] sau 10 giây duy trì.
3. **Logs** → grep `correlation_id` từ alert timestamp → tìm log `"request_failed"` với `error_type: RuntimeError`.
4. **Root cause** → `app/incidents.py` flag kích hoạt → `mock_rag.py` hoặc `mock_llm.py` ném RuntimeError có chủ ý.
5. **Fix** → Gọi `/incidents/rag_slow/disable` → error rate trở về 0% → alert tự `[RESOLVED]`.

**Preventive measure:** Thêm circuit breaker trong `agent.py`: nếu error rate > 20% trong 1 phút, tự động fallback sang cached response.

---

## 5. Kết Luận

Qua Lab 13, tôi đã triển khai thực tế một hệ thống observability đầy đủ cho AI agent:

- **Logging**: Structured JSON log với correlation ID, PII scrubbing tự động, dual-output (file + stdout).
- **Tracing**: Langfuse trace tích hợp với metadata đầy đủ (`user_id_hash`, `session_id`, `tags`, token usage).
- **Metrics**: Real-time in-memory metrics với P95/P99 latency, quality score, cost tracking, per-user quota.
- **Alerting**: 5 alert rules được đánh giá theo sustained-window logic, ghi JSONL evidence, auto-resolve.
- **Incident Response**: Quy trình Metrics → Alert → Log → Root Cause được thực hành trực tiếp.

**Điểm học được:** Observability không chỉ là "thêm log" mà là thiết kế hệ thống sao cho bất kỳ sự cố nào cũng có thể được phát hiện, định vị và giải thích hoàn toàn từ dữ liệu có sẵn — không cần debug live production.

---

*Báo cáo được nộp kèm theo repository `Lab_13_C401_Table_E1` với đầy đủ bằng chứng trong `data/alerts.jsonl` và `data/logs.jsonl`.*
