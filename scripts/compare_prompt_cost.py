from __future__ import annotations

import argparse
import json
import math
import sys
from dataclasses import dataclass
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from app.cli import configure_utf8_stdio

INPUT_PRICE_PER_MILLION = 3.0
QUALITY_TOLERANCE = 0.02


@dataclass(frozen=True)
class RunSummary:
    requests: int
    responses: int
    failures: int
    error_rate_pct: float
    avg_tokens_in: float
    avg_tokens_out: float
    input_cost_usd: float
    total_cost_usd: float
    avg_cost_usd: float
    latency_p95_ms: float
    quality_avg: float


def _percentile(values: list[float], percentile: int) -> float:
    if not values:
        return 0.0
    ordered = sorted(values)
    index = max(0, min(len(ordered) - 1, math.ceil(percentile * len(ordered) / 100) - 1))
    return ordered[index]


def load_records(path: Path) -> list[dict]:
    records: list[dict] = []
    for number, line in enumerate(path.read_text(encoding="utf-8").splitlines(), start=1):
        if not line.strip():
            continue
        try:
            value = json.loads(line)
        except json.JSONDecodeError as exc:
            raise ValueError(f"{path}:{number} không phải JSON hợp lệ") from exc
        if isinstance(value, dict):
            records.append(value)
    return records


def summarize(records: list[dict]) -> RunSummary:
    requests = [record for record in records if record.get("event") == "request_received"]
    responses = [record for record in records if record.get("event") == "response_sent"]
    failures = [record for record in records if record.get("event") == "request_failed"]
    if not requests or not responses:
        raise ValueError("Log phải có request_received và response_sent")

    tokens_in = [float(record["tokens_in"]) for record in responses]
    tokens_out = [float(record["tokens_out"]) for record in responses]
    costs = [float(record["cost_usd"]) for record in responses]
    latencies = [float(record["latency_ms"]) for record in responses]
    qualities = [float(record["quality_score"]) for record in responses]
    return RunSummary(
        requests=len(requests),
        responses=len(responses),
        failures=len(failures),
        error_rate_pct=len(failures) / len(requests) * 100,
        avg_tokens_in=sum(tokens_in) / len(tokens_in),
        avg_tokens_out=sum(tokens_out) / len(tokens_out),
        input_cost_usd=sum(tokens_in) / 1_000_000 * INPUT_PRICE_PER_MILLION,
        total_cost_usd=sum(costs),
        avg_cost_usd=sum(costs) / len(costs),
        latency_p95_ms=_percentile(latencies, 95),
        quality_avg=sum(qualities) / len(qualities),
    )


def _change(before: float, after: float) -> float:
    return 0.0 if before == 0 else (after - before) / before * 100


def compare(baseline: RunSummary, candidate: RunSummary) -> tuple[bool, list[str]]:
    checks = [
        (baseline.requests == candidate.requests, "same request count"),
        (candidate.avg_tokens_in < baseline.avg_tokens_in, "candidate input tokens decreased"),
        (candidate.input_cost_usd < baseline.input_cost_usd, "candidate input cost decreased"),
        (candidate.avg_cost_usd < baseline.avg_cost_usd, "candidate total average cost decreased"),
        (candidate.quality_avg >= baseline.quality_avg - QUALITY_TOLERANCE, "quality stayed within 0.02"),
        (candidate.error_rate_pct <= baseline.error_rate_pct, "error rate did not increase"),
    ]
    return all(result for result, _ in checks), [f"{'PASS' if result else 'FAIL'}: {label}" for result, label in checks]


def render(baseline: RunSummary, candidate: RunSummary) -> str:
    passed, checks = compare(baseline, candidate)
    lines = [
        "Prompt cost comparison (same workload)",
        "",
        "metric | baseline | candidate | change",
        "--- | ---: | ---: | ---:",
        f"requests | {baseline.requests} | {candidate.requests} | {_change(baseline.requests, candidate.requests):+.2f}%",
        f"error_rate_pct | {baseline.error_rate_pct:.2f} | {candidate.error_rate_pct:.2f} | {_change(baseline.error_rate_pct, candidate.error_rate_pct):+.2f}%",
        f"avg_tokens_in | {baseline.avg_tokens_in:.2f} | {candidate.avg_tokens_in:.2f} | {_change(baseline.avg_tokens_in, candidate.avg_tokens_in):+.2f}%",
        f"avg_tokens_out | {baseline.avg_tokens_out:.2f} | {candidate.avg_tokens_out:.2f} | {_change(baseline.avg_tokens_out, candidate.avg_tokens_out):+.2f}%",
        f"input_cost_usd | {baseline.input_cost_usd:.6f} | {candidate.input_cost_usd:.6f} | {_change(baseline.input_cost_usd, candidate.input_cost_usd):+.2f}%",
        f"avg_cost_usd | {baseline.avg_cost_usd:.6f} | {candidate.avg_cost_usd:.6f} | {_change(baseline.avg_cost_usd, candidate.avg_cost_usd):+.2f}%",
        f"total_cost_usd | {baseline.total_cost_usd:.6f} | {candidate.total_cost_usd:.6f} | {_change(baseline.total_cost_usd, candidate.total_cost_usd):+.2f}%",
        f"latency_p95_ms | {baseline.latency_p95_ms:.2f} | {candidate.latency_p95_ms:.2f} | {_change(baseline.latency_p95_ms, candidate.latency_p95_ms):+.2f}%",
        f"quality_avg | {baseline.quality_avg:.3f} | {candidate.quality_avg:.3f} | {_change(baseline.quality_avg, candidate.quality_avg):+.2f}%",
        "",
        *checks,
        "",
        f"RESULT: {'PASS' if passed else 'FAIL'}",
    ]
    return "\n".join(lines) + "\n"


def main() -> None:
    configure_utf8_stdio()
    parser = argparse.ArgumentParser(description="Compare two prompt runs on the same workload")
    parser.add_argument("--baseline", type=Path, required=True)
    parser.add_argument("--candidate", type=Path, required=True)
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()

    baseline = summarize(load_records(args.baseline))
    candidate = summarize(load_records(args.candidate))
    report = render(baseline, candidate)
    print(report, end="")
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(report, encoding="utf-8")
    passed, _ = compare(baseline, candidate)
    raise SystemExit(0 if passed else 1)


if __name__ == "__main__":
    main()
