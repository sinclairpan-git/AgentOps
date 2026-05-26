from __future__ import annotations

import json
from contextlib import contextmanager
from copy import deepcopy
from http.client import HTTPConnection
from http.server import ThreadingHTTPServer
from pathlib import Path
from threading import Thread
from typing import Iterator

import pytest

from agentops.api.console_snapshot import build_console_snapshot
from agentops.api.runtime import ingest_runtime_events
from agentops.api.server import create_http_handler
from agentops.storage.repository import InMemoryRepository


FIXTURE_PATH = (
    Path(__file__).resolve().parents[2]
    / "contracts"
    / "cross-project"
    / "fixtures"
    / "ai_sdlc_executable_task_runtime_batch.v1.json"
)


def _fixture_batch() -> dict:
    return json.loads(FIXTURE_PATH.read_text(encoding="utf-8"))


def _clone_runtime_store(source: InMemoryRepository) -> InMemoryRepository:
    restarted = InMemoryRepository()
    restarted.runtime_runs = deepcopy(source.runtime_runs)
    restarted.trace_spans = deepcopy(source.trace_spans)
    restarted.guardrail_results = deepcopy(source.guardrail_results)
    restarted.runtime_idempotency_index = deepcopy(source.runtime_idempotency_index)
    restarted.runtime_dlq = deepcopy(source.runtime_dlq)
    restarted.runtime_outbox_receipts = deepcopy(source.runtime_outbox_receipts)
    return restarted


def _json_request(
    server: ThreadingHTTPServer, method: str, path: str, payload: dict | None = None
) -> tuple[int, dict]:
    connection = HTTPConnection(
        server.server_address[0], server.server_address[1], timeout=5
    )
    try:
        body = json.dumps(payload).encode("utf-8") if payload is not None else None
        headers = {"Content-Type": "application/json"} if payload is not None else {}
        connection.request(method, path, body=body, headers=headers)
        response = connection.getresponse()
        raw_body = response.read().decode("utf-8")
        return response.status, json.loads(raw_body) if raw_body else {}
    finally:
        connection.close()


class _TransactionProbeRepository(InMemoryRepository):
    def __init__(self, *, fail_commit: bool = False) -> None:
        super().__init__()
        self.fail_commit = fail_commit
        self.transaction_open = False
        self.receipt_written_inside_transaction = False
        self.transaction_closed = False

    @contextmanager
    def runtime_ingestion_transaction(self) -> Iterator[None]:
        self.transaction_open = True
        try:
            yield
            if self.fail_commit:
                raise RuntimeError("simulated commit failure")
        finally:
            self.transaction_open = False
            self.transaction_closed = True

    def write_runtime_outbox_receipt(self, receipt: dict) -> None:
        self.receipt_written_inside_transaction = self.transaction_open
        super().write_runtime_outbox_receipt(receipt)


def test_ao57_ct_011_runtime_receipt_is_written_inside_repository_transaction():
    repository = _TransactionProbeRepository()

    receipt = ingest_runtime_events(_fixture_batch(), repository)

    assert receipt["accepted_count"] == 2
    assert repository.receipt_written_inside_transaction is True
    assert repository.transaction_closed is True


def test_ao57_ct_012_runtime_ingestion_does_not_return_receipt_when_commit_fails():
    repository = _TransactionProbeRepository(fail_commit=True)

    with pytest.raises(RuntimeError, match="simulated commit failure"):
        ingest_runtime_events(_fixture_batch(), repository)

    assert repository.transaction_closed is True


def test_ao57_ct_013_restarted_repository_reads_trace_receipt_and_console_snapshot():
    repository = InMemoryRepository()
    first = ingest_runtime_events(_fixture_batch(), repository)
    replay = ingest_runtime_events(_fixture_batch(), repository)
    restarted = _clone_runtime_store(repository)

    snapshot = build_console_snapshot(repository=restarted)
    workbench = snapshot["consoleData"]["sdlcRunWorkbench"]

    assert first["accepted_count"] == 2
    assert replay["deduplicated_count"] == 2
    assert restarted.trace_span_count() == 2
    assert workbench["taskGuard"][0]["run_id"] == "run_sdlc_001"
    assert workbench["outboxReceipts"][0]["outbox_id"] == first["outbox_id"]
    assert workbench["evidenceReadiness"][0]["raw_payload_state"] == "summary_only"
    assert "allowed_paths" not in json.dumps(restarted.trace_span_records())


def test_ao57_ct_014_http_restart_readback_uses_persisted_runtime_facts():
    repository = InMemoryRepository()
    ingest_server = ThreadingHTTPServer(
        ("127.0.0.1", 0), create_http_handler(repository)
    )
    ingest_thread = Thread(target=ingest_server.serve_forever, daemon=True)
    ingest_thread.start()
    try:
        status, receipt = _json_request(
            ingest_server, "POST", "/v1/runtime/events", _fixture_batch()
        )
    finally:
        ingest_server.shutdown()
        ingest_server.server_close()
        ingest_thread.join(timeout=5)

    restarted = _clone_runtime_store(repository)
    read_server = ThreadingHTTPServer(("127.0.0.1", 0), create_http_handler(restarted))
    read_thread = Thread(target=read_server.serve_forever, daemon=True)
    read_thread.start()
    try:
        trace_status, trace = _json_request(
            read_server, "GET", "/v1/runtime/runs/run_sdlc_001/trace"
        )
        evidence_status, evidence = _json_request(
            read_server, "GET", "/v1/runtime/runs/run_sdlc_001/evidence-summary"
        )
    finally:
        read_server.shutdown()
        read_server.server_close()
        read_thread.join(timeout=5)

    assert status == 202
    assert receipt["accepted_count"] == 2
    assert trace_status == 200
    assert trace["aggregate"]["span_count"] == 2
    assert evidence_status == 200
    assert evidence["raw_access_state"] == "summary_only"
