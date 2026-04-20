# Day 13 Observability Lab Report

> **Instruction**: Fill in all sections below. This report is designed to be parsed by an automated grading assistant. Ensure all tags (e.g., `[GROUP_NAME]`) are preserved.

## 1. Team Metadata
- GROUP_NAME: E1
- REPO_URL: https://github.com/N0VA554/Lab_13_C401_Table_E1
- MEMBERS:
  - Nguyễn Đức Manh, Role: Security & Privacy · Dashboard UI · Token Limit (per user & per query)
  - Nguyễn Anh Hào, Role: Logging structure
  - Lê Hà An, Role: agent.py, tracing.py
  - Lê Ngọc Hải, Role: Monitoring & SRE
  - Nguyễn Ngọc Cường, Role: QA, Reporting

---

## 2. Group Performance (Auto-Verified)
- VALIDATE_LOGS_FINAL_SCORE: 100/100
- TOTAL_TRACES_COUNT: 75
- PII_LEAKS_FOUND: 0

---

## 3. Technical Evidence (Group)

### 3.1 Logging & Tracing
- EVIDENCE_CORRELATION_ID_SCREENSHOT: dashboard.jpg
- EVIDENCE_PII_REDACTION_SCREENSHOT: data/logs.jsonl
- EVIDENCE_TRACE_WATERFALL_SCREENSHOT: alert.jpg
- TRACE_WATERFALL_EXPLANATION: (Briefly explain one interesting span in your trace)

### 3.2 Dashboard & SLOs
- DASHBOARD_6_PANELS_SCREENSHOT: dashboard.jpg
- SLO_TABLE:

  | SLI | Target | Window | Current Value |
  |---|---:|---|---:|
  | Latency P95 | < 2500ms | 28d | 98.8% |
  | Error Rate | ≤ 1% | 28d | 99.6% |
  | Cost Budget | < $5/day | 1d | < $5/day |

### 3.3 Alerts & Runbook
- ALERT_RULES_SCREENSHOT: alert.jpg
- SAMPLE_RUNBOOK_LINK: docs/alerts.md#1-high-latency-p95

---

## 4. Incident Response (Group)
- SCENARIO_NAME: người dùng đặt câu hỏi quá dài
- SYMPTOMS_OBSERVED: thời gian chạy chậm dần khi đạt sát giới hạn token
- ROOT_CAUSE_PROVED_BY: hiển thị biểu đồ trên dashboard về user đã đạt quá limit token
- FIX_ACTION: có cảnh báo trên dashboard và thông báo rõ limit của người dùng đó
- PREVENTIVE_MEASURE: giới hạn số token người dùng hỏi trên chat bot và hiển thị khi người dùng đạt giới hạn để họ xóa bớt token đi (ví dụ 1000 token)

---

## 5. Individual Contributions & Evidence

### Nguyễn Đức Manh
- TASKS_COMPLETED: Security & Privacy (PII scrubber) · Dashboard UI · Token limit (per user & per query)
- EVIDENCE_LINK: https://github.com/N0VA554/Lab_13_C401_Table_E1/commit/9469033, https://github.com/N0VA554/Lab_13_C401_Table_E1/commit/d2c51f1, https://github.com/N0VA554/Lab_13_C401_Table_E1/commit/1c998b1

### Nguyễn Anh Hào
- TASKS_COMPLETED: Logging structure · Request correlation · Context enrichment
- EVIDENCE_LINK: app/main.py, https://github.com/N0VA554/Lab_13_C401_Table_E1/commit/19cdcea507bc99381a2f2030663e3b8e7179445b

### Lê Hà An
- TASKS_COMPLETED: agent.py · tracing.py
- EVIDENCE_LINK: agent.py, tracing.py, https://github.com/N0VA554/Lab_13_C401_Table_E1/commit/92e6f54905c2f08fbd5e2b0a4fab1d2b50fb9b79

### Lê Ngọc Hải
- TASKS_COMPLETED: Monitoring & SRE
- EVIDENCE_LINK: app/metrics.py, config/slo.yaml, scripts/alert_monitor.py,app/incidents.py, scripts/load_test.py, https://github.com/N0VA554/Lab_13_C401_Table_E1/commit/9c32bcca0bb8f83d62e9551f3860586d2e9ef909, https://github.com/N0VA554/Lab_13_C401_Table_E1/commit/d437cc6a970a425b4d09f297837b4799bab239f0

### Nguyễn Ngọc Cường
- TASKS_COMPLETED: QA · Reporting
- EVIDENCE_LINK: docs/blueprint-template.md, images/alert.jpg, images/dashboard.jpg, https://github.com/N0VA554/Lab_13_C401_Table_E1/commit/2c5c7d74600bd3773358688490befd1ea73dedbb

---

## 6. Bonus Items (Optional)
- [BONUS_COST_OPTIMIZATION]: Cost guardrail + monitoring (enforce max cost/query $0.005; track `avg_cost_usd`, `total_cost_usd`, `cost_violations` via `/metrics`). Evidence: `app/main.py` (cost check + 402), `app/metrics.py` (snapshot fields), `dashboard/index.html` (cost panel).
- [BONUS_AUDIT_LOGS]: Not implemented in code (only placeholder env var). Evidence: `.env.example` has `AUDIT_LOG_PATH=data/audit.jsonl`; README mentions optional `data/audit.jsonl`; no writer found in `app/`.
- [BONUS_CUSTOM_METRIC]: Custom in-memory metrics endpoint `/metrics` + `/metrics/users` (latency percentiles, tokens totals, quality_avg, error_breakdown, per-user quota). Evidence: `app/metrics.py`, `app/main.py`, `scripts/alert_monitor.py`, `dashboard/index.html`.
