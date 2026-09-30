from __future__ import annotations

import asyncio
import json
import re
from pathlib import Path

import httpx

from app import logging_config
from app.main import app


def test_correlation_id_and_enrichment_are_logged_and_returned(
    monkeypatch, tmp_path: Path
) -> None:
    log_path = tmp_path / "logs.jsonl"
    monkeypatch.setattr(logging_config, "LOG_PATH", log_path)

    async def send() -> httpx.Response:
        transport = httpx.ASGITransport(app=app)
        async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
            return await client.post(
                "/chat",
                json={
                    "user_id": "student-01",
                    "session_id": "session-01",
                    "feature": "qa",
                    "message": "Email me at student@example.com",
                },
            )

    response = asyncio.run(send())
    correlation_id = response.headers["x-request-id"]
    assert re.fullmatch(r"req-[0-9a-f]{8}", correlation_id)
    assert response.headers["x-response-time-ms"]
    assert response.json()["correlation_id"] == correlation_id

    records = [json.loads(line) for line in log_path.read_text(encoding="utf-8").splitlines()]
    api_records = [record for record in records if record.get("service") == "api"]
    assert len(api_records) == 2
    for record in api_records:
        assert record["correlation_id"] == correlation_id
        assert record["user_id_hash"] != "student-01"
        assert record["session_id"] == "session-01"
        assert record["feature"] == "qa"
        assert record["model"]
        assert record["env"]
    assert "student@example.com" not in log_path.read_text(encoding="utf-8")


def test_valid_request_id_is_propagated(monkeypatch, tmp_path: Path) -> None:
    log_path = tmp_path / "logs.jsonl"
    monkeypatch.setattr(logging_config, "LOG_PATH", log_path)

    async def send() -> httpx.Response:
        transport = httpx.ASGITransport(app=app)
        async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
            return await client.post(
                "/chat",
                headers={"x-request-id": "req-1234abcd"},
                json={"user_id": "u", "session_id": "s", "feature": "qa", "message": "hello"},
            )

    response = asyncio.run(send())
    assert response.headers["x-request-id"] == "req-1234abcd"
    records = [json.loads(line) for line in log_path.read_text(encoding="utf-8").splitlines()]
    assert all(record["correlation_id"] == "req-1234abcd" for record in records)
