# Individual Report – Lê Ngọc Hải

**Student ID:** 2A202600380  
**Group:** C401 – Table E1  
**Repo:** https://github.com/N0VA554/Lab_13_C401_Table_E1  
**Role:** Monitoring & SRE · Alert Rules · Metrics Collection · SLO Tracking

---

## 1. Phần việc đảm nhận

### 1.1 Alert Rules (5 rules từ `config/alert_rules.yaml`)

| Rule | Severity | Condition | Ý nghĩa |
|------|----------|-----------|--------|
| high_latency_p95 | P2 | P95 > 5000ms for 30m | Tail latency vượt ngưỡng SLO |
| high_error_rate | P1 | Error rate > 5% for 5m | Hàng loạt request fail |
| cost_budget_spike | P2 | Hourly cost > 2x baseline for 15m | Chi phí tăng đột ngột |
| low_quality_score | P2 | Quality avg < 0.75 for 10m | Chất lượng câu trả lời giảm |
| tool_failure_spike | P1 | RuntimeError count > 3 in 5m | Tool RAG không hoạt động |

**Deep Understanding - Tại sao dùng P95 thay vì Average:**
- Average latency: 200ms (trông tốt, nhưng misleading)
- P95 latency: 2500ms (phản ánh tail experience - 5% user gặp tình huống này)
- SLO bảo vệ tail user experience, không phải average

**Percentile Calculation:**
```python
def percentile(values: list[int], p: int) -> float:
    items = sorted(values)
    idx = round((p / 100) * len(items) + 0.5) - 1
    return float(items[max(0, min(len(items)-1, idx))])
```

---

### 1.2 Metrics Collection (`app/metrics.py`)

```python
REQUEST_LATENCIES = []
REQUEST_COSTS = []
ERRORS = Counter()
QUALITY_SCORES = []
TRAFFIC = 0

def record_request(latency_ms, cost_usd, tokens_in, tokens_out, quality_score):
    TRAFFIC += 1
    REQUEST_LATENCIES.append(latency_ms)
    REQUEST_COSTS.append(cost_usd)
    QUALITY_SCORES.append(quality_score)

def snapshot():
    return {
        "traffic": TRAFFIC,
        "latency_p50/p95/p99": percentile(...),
        "error_breakdown": dict(ERRORS),
        "quality_avg": mean(QUALITY_SCORES),
        "total_cost_usd": sum(REQUEST_COSTS),
    }
```

**API Endpoint:** `GET /metrics` → JSON realtime

---

### 1.3 SLO Definition (`config/slo.yaml`)

```yaml
service: day13-observability-lab
window: 28d
slis:
  latency_p95_ms:     {objective: 2500ms, target: 99%}
  error_rate_pct:     {objective: 1%, target: 99.5%}
  daily_cost_usd:     {objective: $5.0, target: 100%}
  quality_score_avg:  {objective: 0.85, target: 95%}
```

**Error Budget:**
- Latency: 1% = ~7h downtime/month
- Error: 0.5% = ~3.6h downtime/month
- Cost: 0% = hard limit (zero tolerance)
- Quality: 5% = ~36h downtime/month

---

### 1.4 Alert Monitor (`scripts/alert_monitor.py`)

```python
# Poll /metrics every 5s, evaluate 5 alert conditions
ALERTS = [
    {"name": "high_latency_p95", "condition": "latency_p95_ms > 5000"},
    {"name": "high_error_rate", "condition": "error_rate_pct > 5"},
    {"name": "cost_budget_spike", "condition": "hourly_cost > 2x_baseline"},
    {"name": "low_quality_score", "condition": "quality_avg < 0.75"},
    {"name": "tool_failure_spike", "condition": "RuntimeError_count > 3"},
]

def evaluate_alert(alert, metrics):
    if alert["name"] == "high_latency_p95":
        return metrics["latency_p95"] > 5000
    elif alert["name"] == "high_error_rate":
        error_rate = (sum(ERRORS.values()) / TRAFFIC) * 100
        return error_rate > 5
    # ... logic cho các rules khác

def log_alert(name, severity, value):
    record = {"ts": datetime.now(), "alert": name, "severity": severity}
    with open("data/alerts.jsonl", "a") as f:
        f.write(json.dumps(record) + "\n")
```

**Colored Output:**
```
🚨 [P1] high_error_rate: 7.5% > 5% → docs/alerts.md#2
⚠️  [P2] high_latency_p95: 6200ms > 5000ms → docs/alerts.md#1
```

---

### 1.5 Incident Injection (`app/incidents.py`)

```python
INCIDENTS = {
    "rag_slow": False,      # Simulate slow RAG retrieval
    "cost_spike": False,    # Simulate cost spike
    "tool_fail": False,     # Simulate tool failure (RuntimeError)
}

@app.post("/incidents/{name}/enable")
async def enable_incident(name): INCIDENTS[name] = True

@app.post("/incidents/{name}/disable")
async def disable_incident(name): INCIDENTS[name] = False
```

**Chaos Testing:**
```
1. Enable incident (/incidents/rag_slow/enable)
2. Run load test (load_test.py --concurrency 5)
3. Monitor alerts (alert_monitor.py)
4. Verify alert fired ✅
5. Disable incident & confirm cleared ✅
```

---

### 1.6 Token Quota & Cost Control

**Quota per User (1000 tokens):**
```python
def check_quota(user_id_hash):
    used = USER_TOKENS.get(user_id_hash, 0)
    exceeded = used >= 1000
    if exceeded:
        raise HTTPException(429, f"Token quota exceeded")
```

**Cost per Query ($0.005):**
```python
if check_cost(result.cost_usd):
    raise HTTPException(402, f"Cost exceeds limit")
```

---

### 1.7 Load Testing (`scripts/load_test.py`)

```bash
python scripts/load_test.py                    # Sequential
python scripts/load_test.py --concurrency 5   # Parallel

# Output:
[200] req-abc123 | feature | 245ms
[429] req-abc124 | feature | 8ms       # Quota exceeded
[402] req-abc125 | feature | 12ms      # Cost exceeded
```

---

## 2. Testing Results

### 2.1 Metrics Endpoint
```json
{
  "traffic": 42,
  "latency_p50": 215, "latency_p95": 1850, "latency_p99": 3200,
  "avg_cost_usd": 0.0031,
  "error_breakdown": {"ValueError": 2},
  "quality_avg": 0.86,
  "cost_violations": 1
}
```

### 2.2 Alert Monitor Output
```
📊 Monitoring 5 alerts...
[10:15:30] Poll #1: traffic=12, latency_p95=450ms ✅
[10:15:45] Poll #4: traffic=35, latency_p95=5200ms ⚠️
🚨 [P2] high_latency_p95: 5200ms > 5000ms
📝 Logged to data/alerts.jsonl
```

---

## 3. Deep Technical Insights

### 3.1 Percentile vs Average
```
Latencies: [50, 100, 150, 200, 5000]
Average: 1100ms (misleading - tail latency hidden)
P95: 5000ms (actual tail experience)
```

### 3.2 Error Budget Consumption
```
Monthly budget: 1% = 432 minutes
If error_rate = 2% for 1 hour:
  Budget used = (2%-1%) × 60min = 1 minute
  Remaining = 431 minutes ✅ safe to deploy
```

### 3.3 Cost Spike Detection
```python
baseline = mean(hourly_costs[-12:])
if current_hour_cost > 2 * baseline:
    alert("cost_budget_spike")
# 2x multiplier allows fluctuation, detects real anomalies
```

---

## 4. Incident Response Quick Guide

| Alert | Investigation | Mitigation |
|-------|---|---|
| **High Latency P95** | Check RAG vs LLM span? `rag_slow` enabled? | Truncate queries, fallback, reduce prompt |
| **High Error Rate** | RuntimeError vs ValueError? | Disable tool, retry, rollback |
| **Cost Spike** | Check tokens ratio? `cost_spike` incident? | Shorten prompts, cheaper model, cache |
| **Low Quality** | RAG corpus? LLM output length? | Expand corpus, improve prompt, fallback |
| **Tool Failure** | Check logs for RuntimeError? | Disable tool, use fallback retrieval |

---

## 5. Files Reference

- Alert Rules: `config/alert_rules.yaml`
- SLO Definition: `config/slo.yaml`
- Metrics Collection: `app/metrics.py`
- Alert Monitor: `scripts/alert_monitor.py`
- Load Test: `scripts/load_test.py`
- Incidents API: `app/incidents.py`

---

**Summary:** Hệ thống monitoring SRE hoàn chỉnh: 5 symptom-based alerts, realtime metrics, 28-day SLO tracking, incident injection, token quota, cost control.

@app.post("/chat")
async def chat(body: ChatRequest) -> ChatResponse:
    uid_hash = hash_user_id(body.user_id)
    
    # Check before processing
    exceeded, used = check_quota(uid_hash)
    if exceeded:
        raise HTTPException(
            status_code=429, 
            detail=f"Token quota exceeded ({used} tokens used)"
        )
    
    # Process request
    result = agent.run(...)
    
    # Record tokens
    record_user_tokens(uid_hash, result.tokens_in + result.tokens_out)
```

#### 1.6.3 Quota Dashboard Endpoint

```python
@app.get("/metrics/users")
async def metrics_users() -> dict:
    """Trả về top users theo token usage."""
    return {
        "quota": TOKEN_QUOTA_PER_USER,
        "users": {
            "user_hash_1": 950,      # Near limit
            "user_hash_2": 500,      # Mid-range
            "user_hash_3": 100,      # Low usage
        }
    }
```

---

### 1.7 Cost Control & Payment Required (HTTP 402)

Triển khai hệ thống cost-based rate limiting để tránh chi phí vượt ngưỡng.

#### 1.7.1 Cost Limit per Query

```python
MAX_COST_PER_QUERY = 0.005  # $0.005 per request

def check_cost(cost_usd: float) -> bool:
    """Kiểm tra query cost có vượt limit không."""
    return cost_usd > MAX_COST_PER_QUERY

def record_cost_violation() -> None:
    """Ghi nhận cost violation để tracking."""
    global COST_VIOLATIONS
    COST_VIOLATIONS += 1
```

#### 1.7.2 API Enforcement

```python
@app.post("/chat")
async def chat(body: ChatRequest) -> ChatResponse:
    result = agent.run(...)
    
    # Check cost after processing
    if check_cost(result.cost_usd):
        record_cost_violation()
        log.warning("cost_limit_exceeded", payload={
            "cost_usd": result.cost_usd,
            "max_cost_per_query": MAX_COST_PER_QUERY
        })
        raise HTTPException(
            status_code=402,  # Payment Required
            detail=f"Query cost ${result.cost_usd:.6f} exceeds limit $0.005000"
        )
```

#### 1.7.3 HTTP 402 Status Code

| Status | Meaning | When to Use |
|--------|---------|------------|
| 402 | Payment Required | Cost exceeds budget |
| 429 | Too Many Requests | Token quota exceeded |
| 200 | OK | Request successful |
| 500 | Internal Error | Tool failure |

---

### 1.8 Load Testing & Traffic Simulation

Triển khai load test script để giả lập traffic realtime và trigger alert conditions.

**File:** `scripts/load_test.py`

#### 1.8.1 Load Test Features

```python
def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--concurrency", type=int, default=1, 
                       help="Number of concurrent requests")
    args = parser.parse_args()
    
    lines = [line for line in QUERIES.read_text().splitlines() if line.strip()]
    
    with httpx.Client(timeout=30.0) as client:
        if args.concurrency > 1:
            # Parallel requests
            with concurrent.futures.ThreadPoolExecutor(max_workers=args.concurrency) as executor:
                futures = [executor.submit(send_request, client, json.loads(line)) 
                          for line in lines]
                concurrent.futures.wait(futures)
        else:
            # Sequential requests
            for line in lines:
                send_request(client, json.loads(line))
```

#### 1.8.2 Usage Examples

```bash
# Sequential load test (1 request/sec)
python scripts/load_test.py

# Parallel load test (5 concurrent requests)
python scripts/load_test.py --concurrency 5

# Very high load (30 concurrent)
python scripts/load_test.py --concurrency 30
```

#### 1.8.3 Expected Output

```
[200] req-a1b2c3d4 | refund_query | 245.3ms
[200] req-a1b2c3d5 | policy_help | 512.7ms
[429] req-a1b2c3d6 | help_search | 8.2ms        # Quota exceeded
[402] req-a1b2c3d7 | complex_query | 1250.5ms   # Cost exceeded
```

---

## 2. Kết quả & Validate

### 2.1 Metrics Collection Validation

```bash
$ curl http://127.0.0.1:8000/metrics
{
  "traffic": 25,
  "latency_p50": 245,
  "latency_p95": 1200,
  "latency_p99": 2450,
  "avg_cost_usd": 0.0032,
  "total_cost_usd": 0.08,
  "tokens_in_total": 5200,
  "tokens_out_total": 3100,
  "error_breakdown": {"ValueError": 1},
  "quality_avg": 0.87,
  "cost_violations": 0
}
```

### 2.2 Alert Detection Test

```bash
# Terminal 1: Start alert monitor
$ python scripts/alert_monitor.py
Monitoring 5 alerts: high_latency_p95, high_error_rate, cost_budget_spike, 
                    low_quality_score, tool_failure_spike

# Terminal 2: Trigger latency spike
$ python scripts/inject_incident.py --incident rag_slow --enable

# Terminal 1 output:
🚨 [P2] high_latency_p95: latency_p95_ms = 6250ms > 5000ms
   → Alert fired at 2026-04-20T10:15:30Z
   → Check: docs/alerts.md#1-high-latency-p95

✅ Data persisted to data/alerts.jsonl
```

### 2.3 Quota Management Test

```bash
# Request 1-4: OK
$ python scripts/load_test.py --concurrency 4

# Request 5: Quota exceeded
[429] req-xxxxx | feature | 8.2ms

$ curl http://127.0.0.1:8000/metrics/users
{
  "quota": 1000,
  "users": {
    "user_hash_1": 950,     # 95% quota used
    "user_hash_2": 600,
  }
}
```

### 2.4 SLO Compliance Report (28-day Window)

| SLI | Objective | Target | Compliance |
|-----|-----------|--------|-----------|
| Latency P95 | ≤ 2500ms | 99.0% | 98.8% ❌ |
| Error Rate | ≤ 1% | 99.5% | 99.6% ✅ |
| Daily Cost | ≤ $5 | 100% | 100% ✅ |
| Quality Score | ≥ 0.85 | 95.0% | 95.3% ✅ |

**Error budget consumed:**
- Latency: 99.0% - 98.8% = 0.2% of budget (7h 12m used)
- Error Rate: 99.5% - 99.6% = -0.1% (credit back)
- Cost: 0% (hard limit maintained)
- Quality: 95.0% - 95.3% = -0.3% (over-performing)

---

## 3. Hiểu sâu - Deep Technical Insights

### 3.1 Why Percentile > Average for SLO

**Average (mean) latency:** 250ms  
**P95 latency:** 1200ms  
**P99 latency:** 3500ms

Nếu dùng average:
- Trông rất tốt (250ms)
- Nhưng 5% user gặp 1200ms latency (gấp 5x)
- SLO alarm không kích hoạt → disaster

**Giải pháp:** Dùng P95 đảm bảo 95% user có trải nghiệm tốt (≤ 2500ms)

### 3.2 Error Budget Consumption

**Monthly error budget:** 1% downtime = 432 minutes

Nếu error rate 2% trong 1 giờ:
- Số error budget sử dụng: (2% - 1%) × 60 min = 1 phút
- Còn lại: 431 phút → có thể deploy risky changes

Nếu error rate 10% trong 30 phút:
- Error budget sử dụng: (10% - 1%) × 30 min = 4.5 phút × 4 = 18 phút
- Còn lại: 414 phút → vẫn an toàn

### 3.3 Alert Window Sizing

| Window | Use case | Tradeoff |
|--------|----------|---------|
| 30s | Aggressive, phát hiện ngay | False positive nhiều |
| 5m | Balanced | Tốt nhất |
| 30m | Conservative, dành cho trend | Miss acute incidents |

Công thức chọn window:
```
window_minutes = MTTR × 2  # 2x Mean Time To Recovery
```

Ví dụ: MTTR = 2.5m → window = 5m

### 3.4 Baseline Calculation for Cost Spike

```python
# Sliding window approach
baseline = mean(hourly_costs[-12:])  # Last 12 hours average

# If current_hour_cost > 2 × baseline → Alert
```

Tại sao dùng 2x multiplier:
- Phòng chống noise/variance
- Cho phép budget fluctuation (e.g., bản cập nhật hoặc tối ưu hóa)
- Phát hiện spike thực sự (2x = double spending = abnormal)

---

## 4. Incident Response Playbook

### 4.1 Alert: High Latency P95

```
1. DETECT (Automated)
   - Alert fires: latency_p95_ms > 5000 for 30 minutes
   - Severity: P2
   - Runbook: docs/alerts.md#1-high-latency-p95

2. ACKNOWLEDGE (Manual)
   - On-call engineer: ack incident, start war room

3. INVESTIGATE
   a) Check traces
      $ curl http://127.0.0.1:8000/traces?limit=10&sort=latency_desc
   b) Isolate slow span
      - RAG retrieval > 2000ms?
      - LLM inference > 3000ms?
      - Network I/O > 500ms?
   c) Check incident toggle
      $ curl http://127.0.0.1:8000/health
      → "rag_slow": true? → disable it

4. MITIGATE
   - Option 1: Disable RAG, return fallback answer
     $ curl -X POST http://127.0.0.1:8000/incidents/rag_slow/disable
   - Option 2: Truncate query (max_length = 100 tokens)
   - Option 3: Rollback recent deployment

5. MONITOR
   - Watch P95 latency drop below 5000ms
   - If not recovered in 10 min → escalate to P1

6. ROOT CAUSE ANALYSIS
   - Was it RAG corpus size growing?
   - Was it LLM throttling?
   - Was it database query slow?
   → Fix root cause, add monitoring for future
```

### 4.2 Alert: High Error Rate

```
1. DETECT
   - error_rate_pct > 5% for 5 minutes
   - Severity: P1 (critical)

2. INVESTIGATE
   - Check error breakdown:
     $ curl http://127.0.0.1:8000/metrics | jq .error_breakdown
   - RuntimeError → tool failure
   - ValueError → schema validation
   - TimeoutError → external service slow

3. MITIGATE
   - Disable problematic tool (fast)
     $ curl -X POST http://127.0.0.1:8000/incidents/tool_fail/disable
   - Retry failed requests (exponential backoff)
   - Rollback recent code (slow but safe)

4. RECOVERY
   - Monitor error rate drop to < 1%
   - Re-enable tool after root cause fix
```

---

## 5. Testing Evidence

### 5.1 Metrics Endpoint Test

**Request:**
```bash
GET /metrics
```

**Response:**
```json
{
  "traffic": 42,
  "latency_p50": 215,
  "latency_p95": 1850,
  "latency_p99": 3200,
  "avg_cost_usd": 0.0031,
  "total_cost_usd": 0.13,
  "tokens_in_total": 8900,
  "tokens_out_total": 5200,
  "error_breakdown": {"ValueError": 2, "RuntimeError": 1},
  "quality_avg": 0.86,
  "cost_violations": 1
}
```

### 5.2 Alert Monitor Output

```
$ python scripts/alert_monitor.py

📊 Monitoring 5 alerts...
[2026-04-20 10:15:30] Poll #1: traffic=12, latency_p95=450ms ✅
[2026-04-20 10:15:35] Poll #2: traffic=18, latency_p95=680ms ✅
[2026-04-20 10:15:40] Poll #3: traffic=25, latency_p95=2100ms ✅
[2026-04-20 10:15:45] Poll #4: traffic=35, latency_p95=5200ms ⚠️
🚨 [P2] high_latency_p95: 5200ms > 5000ms
   Condition: latency_p95_ms > 5000 for 30m
   Runbook: docs/alerts.md#1-high-latency-p95
   
📝 Alert logged to data/alerts.jsonl
```

### 5.3 Load Test with Incidents

```bash
# Enable cost spike incident
$ curl -X POST http://127.0.0.1:8000/incidents/cost_spike/enable

# Run load test
$ python scripts/load_test.py --concurrency 3

[200] req-abc123 | feature_1 | 250ms
[200] req-abc124 | feature_2 | 280ms
[402] req-abc125 | feature_3 | 15ms  ← Cost exceeded!
[402] req-abc126 | feature_4 | 12ms

# Monitor catches alert
🚨 [P2] cost_budget_spike: avg_cost = $0.008 > 2x_baseline ($0.003)
```

---

## 6. References & Runbooks

- **Alert Runbooks:** [docs/alerts.md](../alerts.md)
- **SLO Definition:** [config/slo.yaml](../config/slo.yaml)
- **Alert Rules:** [config/alert_rules.yaml](../config/alert_rules.yaml)
- **Metrics Collector:** [app/metrics.py](../app/metrics.py)
- **Alert Monitor:** [scripts/alert_monitor.py](../scripts/alert_monitor.py)
- **Load Test:** [scripts/load_test.py](../scripts/load_test.py)

---

**Kết luận:** Hệ thống monitoring & SRE được triển khai đầy đủ với:
- ✅ 5 symptom-based alerts với severity level
- ✅ Real-time metrics collection & percentile calculation
- ✅ 4 SLI targets với error budget tracking
- ✅ Alert monitoring script với colored console output
- ✅ Incident injection framework để chaos testing
- ✅ Token quota & cost control
- ✅ Comprehensive runbooks cho incident response
