from http.client import HTTPConnection
from http.server import ThreadingHTTPServer
import json
from threading import Thread

from agentops.api.console_snapshot import build_console_snapshot
from agentops.api.runtime import (
    get_sdlc_findings,
    get_sdlc_run_health_summary,
    get_sdlc_trends,
    ingest_runtime_events,
)
from agentops.api.server import create_http_handler
from agentops.storage.repository import InMemoryRepository


LATEST_RUN_ID = (
    "run_187_agentops_self_iteration_monitoring_run_2026_06_02T03_21_43Z_19d6465e939a"
)


def _sdlc_event(
    *,
    event_id: str,
    run_id: str,
    sequence_no: int,
    sdlc_event_type: str,
    stage_name: str,
    status: str = "passed",
    span_id: str | None = None,
    parent_span_id: str = "",
    workitem: str = "agentops-self-iteration-monitoring",
    blocking_reason: str = "",
) -> dict:
    span_id = span_id or f"{sdlc_event_type}_{sequence_no}"
    payload = {
        "sdlc_event_id": f"sdlc_{event_id}",
        "run_id": run_id,
        "trace_id": f"trace_{run_id}",
        "span_id": span_id,
        "parent_span_id": parent_span_id,
        "attempt_no": 1,
        "sdlc_event_type": sdlc_event_type,
        "stage_name": stage_name,
        "status": status,
        "started_at": f"2026-06-02T03:21:{sequence_no:02d}Z",
        "ended_at": f"2026-06-02T03:21:{sequence_no + 1:02d}Z",
        "artifact_ref": f"sha256:artifact-{sequence_no}"
        if sdlc_event_type == "artifact"
        else "",
        "evidence_ref": f"sha256:evidence-{sequence_no}",
        "violation_code": "",
        "workitem": workitem,
        "adapter_diagnostic_state": "verified_loaded",
    }
    if sdlc_event_type == "executable_task":
        payload.update(
            {
                "executable_task_id": "T65-1",
                "task_title": "Analyze Ai_AutoSDLC self-iteration run health",
                "task_guard_state": "allowed",
            }
        )
    if sdlc_event_type == "code_guard":
        payload.update(
            {
                "executable_task_id": "T65-1",
                "task_guard_state": "allowed",
                "guard_result": "allowed",
            }
        )
    if blocking_reason:
        payload["blocking_reason"] = blocking_reason
    return {
        "event_id": event_id,
        "schema_version": "event_envelope.v1",
        "event_type": "sdlc_trace_event",
        "event_type_version": "sdlc_trace_event.v1",
        "timestamp": f"2026-06-02T03:21:{sequence_no:02d}Z",
        "integration_mode": "enterprise_managed",
        "enterprise_state": "active",
        "session_id": f"session_{run_id}",
        "run_id": run_id,
        "trace_id": f"trace_{run_id}",
        "sequence_no": sequence_no,
        "idempotency_key": f"sdlc:{run_id}:{event_id}",
        "source_trust": "signed_producer",
        "signature_state": "valid",
        "signature": "sig:example",
        "producer_id": "producer.ai-sdlc.ci",
        "runtime_id": "runtime.ai-sdlc.local",
        "credential_id": "cred.ai-sdlc.example",
        "key_id": "key.ai-sdlc.example",
        "data_classification": "summary",
        "redaction_policy": "summary_only",
        "payload_hash": f"sha256:{event_id}",
        "payload_ref": f"sha256:payload-{event_id}",
        "payload": payload,
    }


def _batch(
    batch_id: str, events: list[dict], replay_reason: str = "initial_delivery"
) -> dict:
    return {
        "schema_version": "runtime.ingestion.v1",
        "batch_id": batch_id,
        "outbox_id": f"outbox_{batch_id}",
        "producer": "Ai_AutoSDLC",
        "replay_reason": replay_reason,
        "events": events,
    }


def _repository_with_sdlc_runs() -> InMemoryRepository:
    repository = InMemoryRepository()
    ingest_runtime_events(
        _batch(
            "batch_failed_close_gate",
            [
                _sdlc_event(
                    event_id="evt_failed_task",
                    run_id="run_186_agentops_self_iteration_monitoring_run",
                    sequence_no=1,
                    sdlc_event_type="executable_task",
                    stage_name="execute",
                ),
                _sdlc_event(
                    event_id="evt_failed_close_gate",
                    run_id="run_186_agentops_self_iteration_monitoring_run",
                    sequence_no=2,
                    sdlc_event_type="gate",
                    stage_name="close",
                    status="failed",
                    span_id="close_gate",
                    parent_span_id="executable_task_1",
                ),
            ],
        ),
        repository,
    )
    ingest_runtime_events(
        _batch(
            "batch_latest_real_run",
            [
                _sdlc_event(
                    event_id="evt_latest_task",
                    run_id=LATEST_RUN_ID,
                    sequence_no=1,
                    sdlc_event_type="executable_task",
                    stage_name="execute",
                ),
                _sdlc_event(
                    event_id="evt_latest_gate",
                    run_id=LATEST_RUN_ID,
                    sequence_no=2,
                    sdlc_event_type="gate",
                    stage_name="close",
                    span_id="close_gate",
                    parent_span_id="executable_task_1",
                ),
                _sdlc_event(
                    event_id="evt_latest_verification",
                    run_id=LATEST_RUN_ID,
                    sequence_no=3,
                    sdlc_event_type="verification",
                    stage_name="verify",
                    span_id="verification",
                    parent_span_id="close_gate",
                ),
                _sdlc_event(
                    event_id="evt_latest_artifact",
                    run_id=LATEST_RUN_ID,
                    sequence_no=4,
                    sdlc_event_type="artifact",
                    stage_name="artifact",
                    status="emitted",
                    span_id="artifact",
                    parent_span_id="verification",
                ),
            ],
        ),
        repository,
    )
    return repository


def _json_request(server: ThreadingHTTPServer, path: str) -> tuple[int, dict]:
    connection = HTTPConnection(
        server.server_address[0], server.server_address[1], timeout=5
    )
    try:
        connection.request("GET", path)
        response = connection.getresponse()
        body = response.read().decode("utf-8")
        return response.status, json.loads(body) if body else {}
    finally:
        connection.close()


def test_ao65_ct_001_latest_real_run_health_summary_outputs_conclusion():
    repository = _repository_with_sdlc_runs()

    summary = get_sdlc_run_health_summary(repository, LATEST_RUN_ID)

    assert summary["schema_version"] == "agentops_sdlc_run_health_summary.v1"
    assert summary["run_id"] == LATEST_RUN_ID
    assert summary["run_type"] == "real_run"
    assert summary["delivered_state"] == "delivered"
    assert summary["accepted"] == 4
    assert summary["failed_span_count"] == 0
    assert summary["overall_status"] == "succeeded"
    assert summary["next_action"] == "保持观测；将该真实自迭代 run 作为健康基线样本。"
    assert summary["raw_access_state"] == "summary_only"


def test_ao65_ct_002_failed_close_gate_generates_structured_finding_and_trend():
    repository = _repository_with_sdlc_runs()

    findings = get_sdlc_findings(repository)["findings"]
    trends = get_sdlc_trends(repository)

    failed_finding = next(
        item
        for item in findings
        if item["run_id"] == "run_186_agentops_self_iteration_monitoring_run"
    )
    assert failed_finding["schema_version"] == "agentops_sdlc_finding.v1"
    assert failed_finding["category"] in {
        "close_gate_failure",
        "missing_failure_reason",
    }
    assert "close" in failed_finding["evidence_summary"]
    assert trends["summary"]["run_count"] == 2
    assert trends["summary"]["failed_count"] == 1
    assert trends["by_stage"]
    assert trends["by_run_type"][0]["run_type"] == "real_run"


def test_ao65_ct_003_console_snapshot_includes_sdlc_findings_trends_and_recommendations():
    repository = _repository_with_sdlc_runs()

    data = build_console_snapshot(repository=repository)["consoleData"]
    workbench = data["sdlcRunWorkbench"]

    assert data["sdlcFindings"]
    assert data["sdlcTrends"]["summary"]["run_count"] == 2
    assert data["sdlcRecommendations"]
    assert workbench["latestRealReport"]["run_id"] == LATEST_RUN_ID
    assert workbench["latestRealReport"]["accepted"] == 4
    assert workbench["latestRealReport"]["failed_span_count"] == 0
    assert any(item["run_type"] == "real_run" for item in workbench["runTypeTags"])
    assert workbench["topFindings"]
    assert workbench["sdlcRecommendations"] == data["sdlcRecommendations"]
    serialized = json.dumps(workbench)
    assert '"raw_payload"' not in serialized
    assert ":///" not in json.dumps(data)


def test_ao65_ct_004_http_readonly_sdlc_analysis_endpoints():
    repository = _repository_with_sdlc_runs()
    server = ThreadingHTTPServer(("127.0.0.1", 0), create_http_handler(repository))
    thread = Thread(target=server.serve_forever, daemon=True)
    thread.start()
    try:
        health_status, health = _json_request(
            server,
            f"/v1/runtime/sdlc/runs/{LATEST_RUN_ID}/health-summary",
        )
        findings_status, findings = _json_request(server, "/v1/runtime/sdlc/findings")
        trends_status, trends = _json_request(server, "/v1/runtime/sdlc/trends")
    finally:
        server.shutdown()
        server.server_close()
        thread.join(timeout=5)

    assert health_status == 200
    assert health["accepted"] == 4
    assert findings_status == 200
    assert findings["findings"]
    assert trends_status == 200
    assert trends["summary"]["run_count"] == 2
