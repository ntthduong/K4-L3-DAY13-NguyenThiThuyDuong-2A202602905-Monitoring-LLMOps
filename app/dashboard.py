from __future__ import annotations

import json
import math
from collections import Counter
from datetime import datetime, timedelta, timezone
from pathlib import Path
from statistics import mean
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
LOG_PATH = ROOT / "data" / "logs.jsonl"


def load_config() -> dict[str, Any]:
    import yaml

    return yaml.safe_load((ROOT / "config" / "dashboard.yaml").read_text(encoding="utf-8"))["dashboard"]


def load_records(path: Path = LOG_PATH) -> list[dict[str, Any]]:
    if not path.exists():
        return []
    records = []
    for line in path.read_text(encoding="utf-8").splitlines():
        try:
            value = json.loads(line)
        except json.JSONDecodeError:
            continue
        if isinstance(value, dict):
            records.append(value)
    return records


def percentile(values: list[float], p: int) -> float:
    if not values:
        return 0.0
    ordered = sorted(values)
    index = max(0, min(len(ordered) - 1, math.ceil(p * len(ordered) / 100) - 1))
    return float(ordered[index])


def within_window(records: list[dict[str, Any]], minutes: int) -> list[dict[str, Any]]:
    cutoff = datetime.now(timezone.utc) - timedelta(minutes=minutes)
    selected = []
    for record in records:
        try:
            ts = datetime.fromisoformat(str(record["ts"]).replace("Z", "+00:00"))
        except (KeyError, ValueError):
            continue
        if ts >= cutoff:
            selected.append(record)
    return selected


def aggregate(records: list[dict[str, Any]], time_range_minutes: int = 60) -> dict[str, Any]:
    requests = [r for r in records if r.get("event") == "request_received"]
    responses = [r for r in records if r.get("event") == "response_sent"]
    failures = [r for r in records if r.get("event") == "request_failed"]
    latencies = [float(r["latency_ms"]) for r in responses if isinstance(r.get("latency_ms"), (int, float))]
    ttfts = [float(r["ttft_ms"]) for r in responses if isinstance(r.get("ttft_ms"), (int, float))]
    costs = [float(r["cost_usd"]) for r in responses if isinstance(r.get("cost_usd"), (int, float))]
    input_tokens = [int(r["tokens_in"]) for r in responses if isinstance(r.get("tokens_in"), (int, float))]
    output_tokens = [int(r["tokens_out"]) for r in responses if isinstance(r.get("tokens_out"), (int, float))]
    quality = [float(r["quality_score"]) for r in responses if isinstance(r.get("quality_score"), (int, float))]
    tool_records = [r for r in responses if r.get("tool_success") is not None]
    minutes = max(1, time_range_minutes)
    return {
        "requests": len(requests),
        "rate": len(requests) / minutes,
        "p50": percentile(latencies, 50),
        "p95": percentile(latencies, 95),
        "p99": percentile(latencies, 99),
        "ttft_p95": percentile(ttfts, 95),
        "error_rate": (len(failures) / len(requests) * 100) if requests else 0.0,
        "errors": Counter(str(r.get("error_type", "unknown")) for r in failures),
        "retrieval_success": (sum(bool(r.get("tool_success")) for r in tool_records) / len(tool_records) * 100) if tool_records else 0.0,
        "costs": costs,
        "cost_total": sum(costs),
        "tokens_in": sum(input_tokens),
        "tokens_out": sum(output_tokens),
        "quality": mean(quality) if quality else 0.0,
        "responses": responses,
    }


def main() -> None:
    import streamlit as st

    config = load_config()
    st.set_page_config(page_title=config["title"], layout="wide")
    st.title(config["title"])
    st.caption(f"Nguồn: data/logs.jsonl · Cửa sổ: {config['time_range_minutes']} phút · Refresh: {config['refresh_seconds']} giây")
    st.markdown(f"<meta http-equiv='refresh' content='{config['refresh_seconds']}'>", unsafe_allow_html=True)

    data = aggregate(within_window(load_records(), config["time_range_minutes"]), config["time_range_minutes"])
    st.subheader("Latency percentiles and TTFT")
    cols = st.columns(4)
    for col, label, value in zip(cols, ("P50", "P95", "P99", "TTFT P95"), (data["p50"], data["p95"], data["p99"], data["ttft_p95"])):
        col.metric(label, f"{value:.0f} ms", delta="Within P95 threshold" if label == "P95" and value <= 3000 else ("Above P95 threshold" if label == "P95" else None))
    st.caption("Threshold: P95 ≤ 3000 ms")
    if data["responses"]:
        st.line_chart({"latency_ms": [r.get("latency_ms", 0) for r in data["responses"]], "ttft_ms": [r.get("ttft_ms", 0) for r in data["responses"]]})

    left, right = st.columns(2)
    with left:
        st.subheader("Request traffic")
        st.metric("Requests", data["requests"])
        st.metric("Rate", f"{data['rate']:.2f} requests/min")
        st.caption("Threshold: ≥ 1 request/min")
    with right:
        st.subheader("Error rate and retrieval success")
        st.metric("Error rate", f"{data['error_rate']:.2f}%")
        st.metric("Retrieval success", f"{data['retrieval_success']:.2f}%")
        st.caption(f"Threshold: error rate ≤ 2% · Error types: {dict(data['errors'])}")

    left, right = st.columns(2)
    with left:
        st.subheader("Cost over time")
        st.metric("Total cost", f"${data['cost_total']:.6f} USD")
        if data["costs"]:
            st.line_chart({"cost_usd_per_response": data["costs"]})
        st.caption("Threshold: total ≤ $2.50 USD")
    with right:
        st.subheader("Input and output tokens")
        st.bar_chart({"tokens": {"input": data["tokens_in"], "output": data["tokens_out"]}})
        st.caption("Threshold: total tokens ≤ 50,000")

    st.subheader("Quality proxy")
    st.metric("Mean quality score", f"{data['quality']:.3f} / 1.000")
    st.caption("Threshold: mean ≥ 0.75")


if __name__ == "__main__":
    main()
