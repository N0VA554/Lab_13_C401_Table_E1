"""
scripts/alert_monitor.py
------------------------
Real-time alert monitor for Day 13 Observability Lab.

# Force UTF-8 output on Windows so ANSI and ASCII work correctly.
import sys, io
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

Polls /metrics every POLL_INTERVAL seconds, evaluates all 5 alert
conditions from config/alert_rules.yaml, and fires colored console
alerts + writes to data/alerts.jsonl for grading evidence.

Usage:
    python scripts/alert_monitor.py                  # default 5s poll
    python scripts/alert_monitor.py --interval 2     # faster polling
    python scripts/alert_monitor.py --base-url http://127.0.0.1:8000
"""
from __future__ import annotations

import argparse
import json
import time
from collections import deque
from datetime import datetime, timezone
from pathlib import Path

import httpx

# ─── ANSI colours ──────────────────────────────────────────────────────────────
RED     = "\033[91m"
YELLOW  = "\033[93m"
GREEN   = "\033[92m"
CYAN    = "\033[96m"
BOLD    = "\033[1m"
RESET   = "\033[0m"

SEVERITY_COLOR = {"P1": RED, "P2": YELLOW, "P3": CYAN}

# ─── Alert thresholds (mirror config/alert_rules.yaml) ────────────────────────
ALERTS = [
    {
        "name":      "high_latency_p95",
        "severity":  "P2",
        "condition": "latency_p95_ms > 5000",
        "window_s":  30,   # must be true for 30 s in lab (30 min in prod)
        "runbook":   "docs/alerts.md#1-high-latency-p95",
    },
    {
        "name":      "high_error_rate",
        "severity":  "P1",
        "condition": "error_rate_pct > 5",
        "window_s":  10,   # must be true for 10 s in lab (5 min in prod)
        "runbook":   "docs/alerts.md#2-high-error-rate",
    },
    {
        "name":      "cost_budget_spike",
        "severity":  "P2",
        "condition": "avg_cost_usd > 2x_baseline",
        "window_s":  15,   # must be true for 15 s in lab (15 min in prod)
        "runbook":   "docs/alerts.md#3-cost-budget-spike",
    },
    {
        "name":      "low_quality_score",
        "severity":  "P2",
        "condition": "quality_avg < 0.75",
        "window_s":  10,
        "runbook":   "docs/alerts.md#4-low-quality-score",
    },
    {
        "name":      "tool_failure_spike",
        "severity":  "P1",
        "condition": "RuntimeError_count_delta > 3",
        "window_s":  10,
        "runbook":   "docs/alerts.md#5-tool-failure-spike",
    },
]

ALERT_LOG = Path("data/alerts.jsonl")


# ─── Helpers ───────────────────────────────────────────────────────────────────

def ts() -> str:
    return datetime.now(timezone.utc).isoformat()


def log_alert(name: str, severity: str, value: str, condition: str, runbook: str) -> None:
    """Append a fired alert to data/alerts.jsonl for grading evidence."""
    ALERT_LOG.parent.mkdir(parents=True, exist_ok=True)
    record = {
        "ts":        ts(),
        "alert":     name,
        "severity":  severity,
        "value":     value,
        "condition": condition,
        "runbook":   runbook,
    }
    with ALERT_LOG.open("a", encoding="utf-8") as f:
        f.write(json.dumps(record) + "\n")


def print_alert(name: str, severity: str, value: str, condition: str, runbook: str) -> None:
    color = SEVERITY_COLOR.get(severity, YELLOW)
    bar   = "=" * 60
    now   = datetime.now().strftime("%H:%M:%S")
    print(f"\n{color}{BOLD}{bar}{RESET}")
    print(f"{color}{BOLD}🚨 ALERT FIRED [{severity}] — {name}{RESET}  {now}")
    print(f"   Condition : {condition}")
    print(f"   Observed  : {value}")
    print(f"   Runbook   : {runbook}")
    print(f"{color}{BOLD}{bar}{RESET}\n")


def print_ok(name: str, value: str) -> None:
    print(f"  {GREEN}✓{RESET}  {name:<30}  {value}")


def print_header(poll: int, metrics: dict) -> None:
    now = datetime.now().strftime("%H:%M:%S")
    print(f"\n{CYAN}{BOLD}─── Poll #{poll}  {now} ───────────────────────────────────{RESET}")
    print(f"     traffic={metrics['traffic']}  "
          f"p95={metrics['latency_p95']:.0f}ms  "
          f"quality={metrics['quality_avg']:.2f}  "
          f"cost=${metrics['total_cost_usd']:.4f}  "
          f"errors={sum(metrics['error_breakdown'].values())}")


# ─── Condition evaluators ──────────────────────────────────────────────────────

def eval_conditions(metrics: dict, prev_metrics: dict | None, baseline_cost: float) -> dict[str, tuple[bool, str]]:
    """
    Returns {alert_name: (is_breached, observed_value_str)}
    """
    results: dict[str, tuple[bool, str]] = {}

    # 1. High latency P95
    p95 = metrics["latency_p95"]
    results["high_latency_p95"] = (p95 > 5000, f"latency_p95={p95:.0f}ms")

    # 2. High error rate
    total_errors  = sum(metrics["error_breakdown"].values())
    total_traffic = metrics["traffic"]
    total_all     = total_errors + total_traffic
    error_pct     = (total_errors / total_all * 100) if total_all > 0 else 0.0
    results["high_error_rate"] = (error_pct > 5, f"error_rate={error_pct:.1f}%")

    # 3. Cost budget spike (avg_cost_usd > 2× baseline)
    avg_cost = metrics["avg_cost_usd"]
    threshold = baseline_cost * 2 if baseline_cost > 0 else 999
    results["cost_budget_spike"] = (
        avg_cost > threshold,
        f"avg_cost=${avg_cost:.5f}  (2×baseline=${threshold:.5f})"
    )

    # 4. Low quality score
    quality = metrics["quality_avg"]
    results["low_quality_score"] = (quality < 0.75, f"quality_avg={quality:.3f}")

    # 5. Tool failure spike — RuntimeError count delta since last poll
    runtime_now  = metrics["error_breakdown"].get("RuntimeError", 0)
    runtime_prev = (prev_metrics or metrics)["error_breakdown"].get("RuntimeError", 0)
    delta        = runtime_now - runtime_prev
    results["tool_failure_spike"] = (delta > 3, f"RuntimeError_delta={delta}")

    return results


# ─── Main monitor loop ─────────────────────────────────────────────────────────

def main() -> None:
    parser = argparse.ArgumentParser(description="Lab 13 real-time alert monitor")
    parser.add_argument("--base-url",  default="http://127.0.0.1:8000")
    parser.add_argument("--interval",  type=float, default=5.0, help="Poll interval in seconds")
    args = parser.parse_args()

    base_url = args.base_url.rstrip("/")
    interval = args.interval

    # sliding window: deque of (timestamp, {alert_name: is_breached})
    history: deque[tuple[float, dict[str, bool]]] = deque()

    # track which alerts are currently "firing" to avoid duplicate prints
    firing: set[str] = set()

    prev_metrics: dict | None = None
    baseline_cost: float = 0.0
    poll_count = 0

    print(f"{BOLD}{CYAN}╔══════════════════════════════════════════════════════╗{RESET}")
    print(f"{BOLD}{CYAN}║      Lab 13 — Real-time Alert Monitor                ║{RESET}")
    print(f"{BOLD}{CYAN}║  Polling {base_url}/metrics every {interval}s              ║{RESET}")
    print(f"{BOLD}{CYAN}║  Alerts log → data/alerts.jsonl                      ║{RESET}")
    print(f"{BOLD}{CYAN}╚══════════════════════════════════════════════════════╝{RESET}")
    print(f"\n  Press {BOLD}Ctrl+C{RESET} to stop.\n")

    with httpx.Client(timeout=5.0) as client:
        while True:
            poll_count += 1
            now = time.monotonic()

            try:
                resp = client.get(f"{base_url}/metrics")
                resp.raise_for_status()
                metrics = resp.json()
            except Exception as exc:
                print(f"{RED}[{datetime.now().strftime('%H:%M:%S')}] Cannot reach {base_url}/metrics — {exc}{RESET}")
                time.sleep(interval)
                continue

            # Set baseline cost from first successful poll with traffic
            if baseline_cost == 0.0 and metrics["avg_cost_usd"] > 0:
                baseline_cost = metrics["avg_cost_usd"]
                print(f"  {CYAN}Baseline cost set: ${baseline_cost:.5f}/req{RESET}")

            print_header(poll_count, metrics)

            # Evaluate all conditions
            results = eval_conditions(metrics, prev_metrics, baseline_cost)

            # Add to history
            history.append((now, {k: v[0] for k, v in results.items()}))

            # Prune history older than max window needed
            max_window = max(a["window_s"] for a in ALERTS)
            while history and (now - history[0][0]) > max_window + interval:
                history.popleft()

            # Check each alert with its time window
            for alert in ALERTS:
                name    = alert["name"]
                win_s   = alert["window_s"]
                is_now, value_str = results[name]

                # Find readings within this alert's window
                window_readings = [
                    breached[name]
                    for t, breached in history
                    if (now - t) <= win_s
                ]

                # Alert fires if ALL recent readings in window are breached
                sustained = len(window_readings) >= max(1, int(win_s / interval) // 2) and all(window_readings)

                if sustained and name not in firing:
                    # NEW alert — fire it
                    firing.add(name)
                    print_alert(name, alert["severity"], value_str, alert["condition"], alert["runbook"])
                    log_alert(name, alert["severity"], value_str, alert["condition"], alert["runbook"])

                elif not is_now and name in firing:
                    # Alert recovered
                    firing.discard(name)
                    color = SEVERITY_COLOR.get(alert["severity"], YELLOW)
                    print(f"  {GREEN}✅ RESOLVED{RESET}  {color}{name}{RESET}  ({value_str})")

                else:
                    status = f"{RED}BREACHED{RESET}" if is_now else f"{GREEN}OK{RESET}"
                    print(f"  {status}  {name:<30}  {value_str}")

            prev_metrics = metrics
            time.sleep(interval)


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print(f"\n\n{BOLD}Monitor stopped.{RESET}  Alert log saved to data/alerts.jsonl\n")
