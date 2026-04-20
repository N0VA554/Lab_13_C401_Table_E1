# Alert Rules and Runbooks

## 1. High latency P95
- Severity: P2
- Trigger: `latency_p95_ms > 5000 for 30m`
- Impact: tail latency breaches SLO
- First checks:
  1. Open top slow traces in the last 1h
  2. Compare RAG span vs LLM span
  3. Check if incident toggle `rag_slow` is enabled
- Mitigation:
  - truncate long queries
  - fallback retrieval source
  - lower prompt size

## 2. High error rate
- Severity: P1
- Trigger: `error_rate_pct > 5 for 5m`
- Impact: users receive failed responses
- First checks:
  1. Group logs by `error_type`
  2. Inspect failed traces
  3. Determine whether failures are LLM, tool, or schema related
- Mitigation:
  - rollback latest change
  - disable failing tool
  - retry with fallback model

## 3. Cost budget spike
- Severity: P2
- Trigger: `hourly_cost_usd > 2x_baseline for 15m`
- Impact: burn rate exceeds budget
- First checks:
  1. Split traces by feature and model
  2. Compare tokens_in/tokens_out
  3. Check if `cost_spike` incident was enabled
- Mitigation:
  - shorten prompts
  - route easy requests to cheaper model
  - apply prompt cache

## 4. Low quality score
- Severity: P2
- Trigger: `quality_score_avg < 0.75 for 10m`
- Impact: agent answers are degraded — users receive low-relevance or short responses
- First checks:
  1. Check `quality_avg` in `/metrics` endpoint
  2. Review recent traces in Langfuse — compare `doc_count` and `quality_score` metadata
  3. Check if RAG corpus is returning "No domain document matched" for most queries
  4. Check if LLM output length dropped significantly (tokens_out low)
- Mitigation:
  - expand RAG corpus with more domain documents
  - improve prompt to produce longer, more relevant answers
  - add fallback answer strategy when no docs matched

## 5. Tool failure spike
- Severity: P1
- Trigger: `error_breakdown.RuntimeError > 3 in 5m`
- Impact: vector store / RAG tool is failing — all requests error out with 500
- First checks:
  1. Check logs for `error_type: RuntimeError` and `event: request_failed`
  2. Check if incident toggle `tool_fail` is enabled (via `/health` endpoint)
  3. Verify vector store connectivity and timeout settings in `mock_rag.py`
- Mitigation:
  - disable failing tool via `/incidents/tool_fail/disable`
  - switch to fallback retrieval (keyword search)
  - return graceful degraded response without RAG context
