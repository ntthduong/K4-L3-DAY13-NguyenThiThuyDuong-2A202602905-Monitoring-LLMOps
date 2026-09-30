from __future__ import annotations

import json
from pathlib import Path

from scripts.compare_prompt_cost import compare, load_records, render, summarize


def _records(tokens_in: int, cost: float, quality: float = 0.8) -> list[dict]:
    return [
        {"event": "request_received"},
        {
            "event": "response_sent",
            "tokens_in": tokens_in,
            "tokens_out": 100,
            "cost_usd": cost,
            "latency_ms": 150,
            "quality_score": quality,
        },
    ]


def test_cost_comparison_passes_for_cheaper_equal_quality_candidate() -> None:
    baseline = summarize(_records(tokens_in=200, cost=0.0030))
    candidate = summarize(_records(tokens_in=100, cost=0.0025))

    passed, checks = compare(baseline, candidate)

    assert passed
    assert all(line.startswith("PASS") for line in checks)
    assert "RESULT: PASS" in render(baseline, candidate)


def test_cost_comparison_rejects_mismatched_workloads() -> None:
    baseline = summarize(_records(tokens_in=200, cost=0.0030) * 2)
    candidate = summarize(_records(tokens_in=100, cost=0.0025))

    passed, checks = compare(baseline, candidate)

    assert not passed
    assert "FAIL: same request count" in checks


def test_load_records_reports_invalid_json_line(tmp_path: Path) -> None:
    path = tmp_path / "bad.jsonl"
    path.write_text(json.dumps({"event": "request_received"}) + "\nnot-json\n", encoding="utf-8")

    try:
        load_records(path)
    except ValueError as exc:
        assert ":2" in str(exc)
    else:
        raise AssertionError("invalid JSONL must fail")
