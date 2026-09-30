from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any

from dotenv import load_dotenv
from langfuse import get_client

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from app.challenge import load_challenge
from app.dashboard import aggregate


def _read_jsonl(path: Path) -> list[dict[str, Any]]:
    return [
        json.loads(line)
        for line in path.read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]


def _safe_log_record(record: dict[str, Any]) -> dict[str, Any]:
    keys = (
        "ts",
        "event",
        "correlation_id",
        "feature",
        "model",
        "latency_ms",
        "ttft_ms",
        "tokens_in",
        "tokens_out",
        "cost_usd",
        "quality_score",
        "tool_name",
        "tool_success",
    )
    return {key: record.get(key) for key in keys if key in record}


def _observation_summary(observation: Any) -> dict[str, Any]:
    metadata = observation.metadata or {}
    return {
        "trace_id": observation.trace_id,
        "observation_id": observation.id,
        "parent_observation_id": observation.parent_observation_id,
        "name": observation.name,
        "type": str(observation.type),
        "start_time": str(observation.start_time),
        "latency_seconds": observation.latency,
        "model": observation.model,
        "usage": observation.usage_details,
        "cost": observation.cost_details,
        "prompt_name": observation.prompt_name,
        "prompt_version": observation.prompt_version,
        "correlation_id": metadata.get("correlation_id"),
        "prompt_label": metadata.get("prompt_label"),
        "prompt_source": metadata.get("prompt_source"),
    }


def _write(path: Path, heading: str, payload: Any) -> None:
    path.write_text(
        f"{heading}\n{'=' * len(heading)}\n\n"
        + json.dumps(payload, ensure_ascii=False, indent=2, default=str)
        + "\n",
        encoding="utf-8",
    )


def main() -> None:
    parser = argparse.ArgumentParser(description="Export scrubbed runtime evidence from logs and Langfuse")
    parser.add_argument("--log", type=Path, required=True)
    parser.add_argument("--correlation-id", required=True)
    parser.add_argument("--output-dir", type=Path, default=Path("submission/evidence"))
    parser.add_argument("--project-name", default="day13-k4-l3b-2A202602905")
    args = parser.parse_args()
    args.output_dir.mkdir(parents=True, exist_ok=True)

    records = _read_jsonl(args.log)
    selected = next(
        record
        for record in records
        if record.get("event") == "response_sent"
        and record.get("correlation_id") == args.correlation_id
    )
    enabled = next(record for record in records if record.get("event") == "incident_enabled")
    disabled = next(record for record in records if record.get("event") == "incident_disabled")
    incident_records = [
        record
        for record in records
        if enabled["ts"] <= record.get("ts", "") <= disabled["ts"]
    ]
    incident_metrics = aggregate(incident_records)
    challenge = load_challenge()
    metric_payload = {
        "source": str(args.log),
        "challenge_id": challenge.challenge_id,
        "incident": challenge.incident,
        "window_start_utc": enabled["ts"],
        "window_end_utc": disabled["ts"],
        "requests": incident_metrics["requests"],
        "latency_p50_ms": incident_metrics["p50"],
        "latency_p95_ms": incident_metrics["p95"],
        "latency_p99_ms": incident_metrics["p99"],
        "ttft_p95_ms": incident_metrics["ttft_p95"],
        "error_rate_pct": incident_metrics["error_rate"],
        "retrieval_success_pct": incident_metrics["retrieval_success"],
        "slo_latency_threshold_ms": challenge.latency_threshold_ms,
    }
    _write(args.output_dir / "12-incident-metric.txt", "Incident metric evidence", metric_payload)
    _write(
        args.output_dir / "13-incident-log.txt",
        "Incident structured log evidence",
        _safe_log_record(selected),
    )

    load_dotenv()
    client = get_client()
    observations = client.api.observations.get_many(
        limit=1000,
        from_start_time=datetime.now(timezone.utc) - timedelta(days=1),
        fields="core,basic,metadata,model,usage,prompt,metrics,trace_context",
    ).data
    incident_observations = [
        observation
        for observation in observations
        if (observation.metadata or {}).get("correlation_id") == args.correlation_id
    ]
    incident_observations.sort(key=lambda observation: observation.start_time)
    trace_payload = {
        "source": "Langfuse Observations API v2",
        "project": args.project_name,
        "correlation_id": args.correlation_id,
        "trace_id": incident_observations[0].trace_id,
        "observations": [_observation_summary(item) for item in incident_observations],
    }
    _write(args.output_dir / "14-incident-trace.txt", "Incident trace evidence", trace_payload)

    agent_observations = [item for item in observations if item.name == "lab-agent-run"]

    def latest(label: str, version: int) -> Any:
        matches = [
            item
            for item in agent_observations
            if (item.metadata or {}).get("prompt_label") == label
            and (item.metadata or {}).get("prompt_version") == version
        ]
        return max(matches, key=lambda item: item.start_time)

    baseline = latest("baseline", 1)
    candidate = latest("candidate", 2)
    promoted = latest("production", 2)
    rolled_back = latest("production", 1)
    candidate_trace = [item for item in observations if item.trace_id == candidate.trace_id]
    candidate_trace.sort(key=lambda item: item.start_time)
    _write(
        args.output_dir / "08-trace-metadata.txt",
        "Managed prompt trace metadata",
        {
            "source": "Langfuse Observations API v2",
            "project": args.project_name,
            "trace_id": candidate.trace_id,
            "observations": [_observation_summary(item) for item in candidate_trace],
        },
    )

    prompt_states = {}
    for label in ("baseline", "candidate", "production"):
        prompt = client.get_prompt(
            "day13-chat",
            label=label,
            type="text",
            cache_ttl_seconds=0,
            max_retries=0,
        )
        prompt_states[label] = {"version": prompt.version, "labels": prompt.labels}
    _write(
        args.output_dir / "09-prompt-versions.txt",
        "Langfuse prompt versions",
        {"project": args.project_name, "prompt_name": "day13-chat", "states": prompt_states},
    )
    _write(
        args.output_dir / "10-prompt-rollback.txt",
        "Langfuse prompt promote and rollback",
        {
            "project": args.project_name,
            "prompt_name": "day13-chat",
            "baseline_trace": _observation_summary(baseline),
            "candidate_trace": _observation_summary(candidate),
            "promoted_production_trace": _observation_summary(promoted),
            "rolled_back_production_trace": _observation_summary(rolled_back),
            "current_production_version": prompt_states["production"]["version"],
        },
    )
    print("Exported scrubbed evidence 08-10 and 12-14")


if __name__ == "__main__":
    main()
