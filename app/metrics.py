from __future__ import annotations

from collections import Counter
from statistics import mean

REQUEST_LATENCIES: list[int] = []
REQUEST_COSTS: list[float] = []
REQUEST_TOKENS_IN: list[int] = []
REQUEST_TOKENS_OUT: list[int] = []
ERRORS: Counter[str] = Counter()
TRAFFIC: int = 0
QUALITY_SCORES: list[float] = []

TOKEN_QUOTA_PER_USER = 1000
USER_TOKENS: dict[str, int] = {}

MAX_COST_PER_QUERY = 0.005
COST_VIOLATIONS: int = 0


def record_request(latency_ms: int, cost_usd: float, tokens_in: int, tokens_out: int, quality_score: float) -> None:
    global TRAFFIC
    TRAFFIC += 1
    REQUEST_LATENCIES.append(latency_ms)
    REQUEST_COSTS.append(cost_usd)
    REQUEST_TOKENS_IN.append(tokens_in)
    REQUEST_TOKENS_OUT.append(tokens_out)
    QUALITY_SCORES.append(quality_score)


def record_user_tokens(user_id_hash: str, tokens: int) -> None:
    USER_TOKENS[user_id_hash] = USER_TOKENS.get(user_id_hash, 0) + tokens


def check_quota(user_id_hash: str) -> tuple[bool, int]:
    """Returns (is_exceeded, current_usage)."""
    used = USER_TOKENS.get(user_id_hash, 0)
    return used >= TOKEN_QUOTA_PER_USER, used


def check_cost(cost_usd: float) -> bool:
    """Returns True if cost exceeds max limit."""
    return cost_usd > MAX_COST_PER_QUERY


def record_cost_violation() -> None:
    global COST_VIOLATIONS
    COST_VIOLATIONS += 1


def user_quota_snapshot() -> dict:
    return {
        "quota": TOKEN_QUOTA_PER_USER,
        "users": {uid: used for uid, used in sorted(USER_TOKENS.items(), key=lambda x: -x[1])},
    }



def record_error(error_type: str) -> None:
    ERRORS[error_type] += 1



def percentile(values: list[int], p: int) -> float:
    if not values:
        return 0.0
    items = sorted(values)
    idx = max(0, min(len(items) - 1, round((p / 100) * len(items) + 0.5) - 1))
    return float(items[idx])



def snapshot() -> dict:
    return {
        "traffic": TRAFFIC,
        "latency_p50": percentile(REQUEST_LATENCIES, 50),
        "latency_p95": percentile(REQUEST_LATENCIES, 95),
        "latency_p99": percentile(REQUEST_LATENCIES, 99),
        "avg_cost_usd": round(mean(REQUEST_COSTS), 4) if REQUEST_COSTS else 0.0,
        "total_cost_usd": round(sum(REQUEST_COSTS), 4),
        "tokens_in_total": sum(REQUEST_TOKENS_IN),
        "tokens_out_total": sum(REQUEST_TOKENS_OUT),
        "error_breakdown": dict(ERRORS),
        "quality_avg": round(mean(QUALITY_SCORES), 4) if QUALITY_SCORES else 0.0,
        "max_cost_per_query": MAX_COST_PER_QUERY,
        "cost_violations": COST_VIOLATIONS,
    }
