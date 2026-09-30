from __future__ import annotations

import pytest

from app.dashboard import aggregate, percentile


def test_dashboard_percentiles_and_error_retrieval_aggregations() -> None:
    records = [
        {"event": "request_received"},
        {"event": "request_received"},
        {"event": "request_failed", "error_type": "RuntimeError"},
        {"event": "response_sent", "latency_ms": 100, "ttft_ms": 20, "cost_usd": 0.1,
         "tokens_in": 10, "tokens_out": 20, "quality_score": 0.8, "tool_success": True},
        {"event": "response_sent", "latency_ms": 200, "ttft_ms": 30, "cost_usd": 0.2,
         "tokens_in": 15, "tokens_out": 25, "quality_score": 0.6, "tool_success": False},
    ]
    data = aggregate(records)
    assert data["requests"] == 2
    assert data["p50"] == 100
    assert data["p95"] == 200
    assert data["ttft_p95"] == 30
    assert data["error_rate"] == 50
    assert data["retrieval_success"] == 50
    assert data["cost_total"] == pytest.approx(0.3)
    assert data["tokens_in"] == 25
    assert data["tokens_out"] == 45
    assert data["quality"] == pytest.approx(0.7)


def test_dashboard_percentile_handles_empty_and_bounds() -> None:
    assert percentile([], 95) == 0
    assert percentile([10, 20, 30], 95) == 30
