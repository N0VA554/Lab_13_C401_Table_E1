import httpx, json
r = httpx.get("http://127.0.0.1:8000/metrics")
m = r.json()
total_errors = sum(m["error_breakdown"].values())
total_all = m["traffic"] + total_errors
error_pct = (total_errors / total_all * 100) if total_all > 0 else 0.0
print("=== Current Metrics State ===")
print(f"latency_p95   : {m['latency_p95']:.0f}ms  (alert if >5000)")
print(f"error_rate    : {error_pct:.1f}%  (alert if >5%)")
print(f"avg_cost_usd  : {m['avg_cost_usd']:.5f}  (alert if >2x baseline)")
print(f"quality_avg   : {m['quality_avg']:.3f}  (alert if <0.75)")
print(f"RuntimeError  : {m['error_breakdown'].get('RuntimeError',0)}")
print()
print(json.dumps(m, indent=2))
