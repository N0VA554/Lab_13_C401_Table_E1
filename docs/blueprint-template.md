# Day 13 Observability Lab Report

> **Instruction**: Fill in all sections below. This report is designed to be parsed by an automated grading assistant. Ensure all tags (e.g., `[GROUP_NAME]`) are preserved.

## 1. Team Metadata
- [GROUP_NAME]: E1
- [REPO_URL]: https://github.com/N0VA554/Lab_13_C401_Table_E1
- [MEMBERS]: 5
  - Nguyễn Đức Manh, Role: Security & Privacy · Dashboard UI · Token Limit (per user & per query)
  - Nguyễn Anh Hào, Role: Logging structure
  - Lê Hà An, Role: agent.py, tracing.py
  - Lê Ngọc Hải, Role: Monitoring & SRE
  - Nguyễn Ngọc Cường, Role: QA, Reporting

---

## 2. Group Performance (Auto-Verified)
- [VALIDATE_LOGS_FINAL_SCORE]: 100/100
- [TOTAL_TRACES_COUNT]: 75
- [PII_LEAKS_FOUND]: 0

---

## 3. Technical Evidence (Group)

### 3.1 Logging & Tracing
- [EVIDENCE_CORRELATION_ID_SCREENSHOT]: dashboard.jpg
- [EVIDENCE_PII_REDACTION_SCREENSHOT]: data/logs.jsonl
- [EVIDENCE_TRACE_WATERFALL_SCREENSHOT]: alert.jpg
- [TRACE_WATERFALL_EXPLANATION]: (Briefly explain one interesting span in your trace)

### 3.2 Dashboard & SLOs
- [DASHBOARD_6_PANELS_SCREENSHOT]: dashboard.jpg
- [SLO_TABLE]:
| SLI | Target | Window | Current Value |
|---|---:|---|---:|
| Latency P95 | < 2500ms | 28d |98.8% |
| Error Rate | ≤ 1%| 28d |99.6% |
| Cost Budget | < $5/day | 1d | < $5/day|

### 3.3 Alerts & Runbook
- [ALERT_RULES_SCREENSHOT]: alert.jpg
- [SAMPLE_RUNBOOK_LINK]: docs/alerts.md#1-high-latency-p95

---

## 4. Incident Response (Group)
- [SCENARIO_NAME]: người dùng đặt câu hỏi quá dài
- [SYMPTOMS_OBSERVED]: thời gian chạy chậm dần khi đạt sát giới hạn token
- [ROOT_CAUSE_PROVED_BY]: hiển thị biểu đồ trên dashboard về user đã đạt quá limit token
- [FIX_ACTION]: có cảnh báo trên dashboard và thông báo rõ limit của người dùng đó
- [PREVENTIVE_MEASURE]: giới hạn số token người dùng hỏi trên chat bot và hiển thị khi người dùng đạt giới hạn để họ xóa bớt token đi (ví dụ 1000 token)

---

## 5. Individual Contributions & Evidence

### Nguyễn Đức Manh
- [TASKS_COMPLETED]: Security & Privacy (PII scrubber) · Dashboard UI · Token limit (per user & per query)
- [EVIDENCE_LINK]: https://github.com/N0VA554/Lab_13_C401_Table_E1/commit/9469033, https://github.com/N0VA554/Lab_13_C401_Table_E1/commit/d2c51f1, https://github.com/N0VA554/Lab_13_C401_Table_E1/commit/1c998b1

### Nguyễn Anh Hào
- [TASKS_COMPLETED]: Logging structure · Request correlation · Context enrichment
- [EVIDENCE_LINK]: app/main.py

### Lê Hà An
- [TASKS_COMPLETED]: agent.py · tracing.py
- [EVIDENCE_LINK]: agent.py, tracing.py

### Lê Ngọc Hải
- [TASKS_COMPLETED]: Monitoring & SRE
- [EVIDENCE_LINK]: app/metrics.py, config/slo.yaml, scripts/alert_monitor.py,app/incidents.py, scripts/load_test.py

### Nguyễn Ngọc Cường
- [TASKS_COMPLETED]: QA · Reporting
- [EVIDENCE_LINK]: docs/blueprint-template.md, images/alert.jpg, images/dashboard.jpg, https://github.com/N0VA554/Lab_13_C401_Table_E1/commit/2c5c7d74600bd3773358688490befd1ea73dedbb

---

## 6. Bonus Items (Optional)
- [BONUS_COST_OPTIMIZATION]: (Description + Evidence)
- [BONUS_AUDIT_LOGS]: (Description + Evidence)
- [BONUS_CUSTOM_METRIC]: (Description + Evidence)
