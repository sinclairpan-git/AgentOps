"""Runtime evidence and health summary projections for AO32."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from typing import Any

from agentops.core.errors import AgentOpsError
from agentops.storage.repository import InMemoryRepository

REQUIRED_SPAN_KINDS = ("model", "tool", "guardrail", "artifact")
SUMMARY_VALIDITY = timedelta(days=1)
HEALTH_WINDOW_LIMIT = 20


def build_runtime_evidence_summary(
    repository: InMemoryRepository,
    run_id: str,
    *,
    request_raw: bool = False,
    raw_access_allowed: bool = False,
    now: datetime | None = None,
    valid_until: datetime | None = None,
) -> dict[str, Any]:
    if request_raw and not raw_access_allowed:
        raise AgentOpsError(
            "RAW_ACCESS_REQUIRED",
            "Raw runtime evidence requires Evidence Vault approval.",
            audit_id=f"audit_runtime_evidence_{run_id}",
            request_id=f"req_runtime_evidence_{run_id}",
            denied_scope="runtime.evidence.raw",
            request_access_url="/v1/evidence/raw-access-requests",
        )

    run = repository.get_runtime_run_fact(run_id)
    if run is None:
        raise AgentOpsError(
            "RUNTIME_RUN_NOT_FOUND",
            "Runtime run fact was not found.",
            audit_id=f"audit_runtime_evidence_{run_id}",
            request_id=f"req_runtime_evidence_{run_id}",
        )

    calculated_at = _coerce_datetime(now) or datetime.now(UTC)
    expires_at = _coerce_datetime(valid_until) or calculated_at + SUMMARY_VALIDITY
    spans = list(
        repository.trace_span_records_for_run(run_id, attempt_no=run.get("attempt_no"))
    )
    missing_dimensions = _missing_evidence_dimensions(spans)
    completeness = _evidence_completeness(missing_dimensions)
    expired = expires_at <= calculated_at
    trace_id = str(spans[0].get("trace_id") or "") if spans else ""
    degraded_reason = _degraded_reason(missing_dimensions, expired)

    return {
        "schema_version": "evidence_summary.v1",
        "run_id": str(run_id),
        "trace_id": trace_id,
        "evidence_level": _evidence_level(run, missing_dimensions, expired),
        "source_event_ids": _source_event_ids(run, spans),
        "freshness": "expired" if expired else "fresh",
        "calculated_at": _iso(calculated_at),
        "valid_until": _iso(expires_at),
        "confidence": _evidence_confidence(run, completeness, expired),
        "completeness": completeness,
        "missing_dimensions": missing_dimensions,
        "missing_evidence": missing_dimensions,
        "redaction_state": "raw" if raw_access_allowed else "summary_only",
        "raw_access_state": "approved_limited"
        if raw_access_allowed
        else "summary_only",
        "redaction_policy": "repo_default",
        "data_classification": "internal",
        "source_trust": "verified" if run.get("event_id") else "declared",
        "degraded_reason": degraded_reason,
        "request_access_url": "/v1/evidence/raw-access-requests",
    }


def build_runtime_health_summary(
    repository: InMemoryRepository,
    agent_id: str,
    version: str,
    *,
    now: datetime | None = None,
    valid_until: datetime | None = None,
    window_limit: int = HEALTH_WINDOW_LIMIT,
) -> dict[str, Any]:
    calculated_at = _coerce_datetime(now) or datetime.now(UTC)
    expires_at = _coerce_datetime(valid_until) or calculated_at + SUMMARY_VALIDITY
    expired = expires_at <= calculated_at
    runs = repository.runtime_run_records_for_agent_version(
        agent_id, version, limit=window_limit
    )
    sample_size = len(runs)
    succeeded = sum(1 for run in runs if run.get("status") == "succeeded")
    failed = sum(1 for run in runs if run.get("status") in {"failed", "timeout"})
    policy_block_count = sum(1 for run in runs if run.get("status") == "blocked")
    success_rate = _ratio(succeeded, sample_size)
    failure_rate = _ratio(failed, sample_size)
    evidence_completeness = _average_evidence_completeness(repository, runs)

    recommended_action = _recommended_action(
        sample_size=sample_size,
        failure_rate=failure_rate,
        policy_block_count=policy_block_count,
        evidence_completeness=evidence_completeness,
        expired=expired,
    )

    return {
        "schema_version": "health_summary.v1",
        "agent_id": agent_id,
        "version": version,
        "health_template_id": "runtime-governance-p0",
        "calculation_window": {
            "type": "recent_runs",
            "limit": window_limit,
            "run_ids": [str(run.get("run_id")) for run in runs],
        },
        "sample_size": sample_size,
        "success_rate": success_rate,
        "failure_rate": failure_rate,
        "evidence_completeness": evidence_completeness,
        "policy_block_count": policy_block_count,
        "confidence": _health_confidence(
            sample_size, failure_rate, evidence_completeness, expired
        ),
        "calculated_at": _iso(calculated_at),
        "valid_until": _iso(expires_at),
        "recommended_action": recommended_action,
        "appeal_state": "none",
    }


def summary_is_expired(summary: dict[str, Any], *, now: datetime | None = None) -> bool:
    reference_time = _coerce_datetime(now) or datetime.now(UTC)
    valid_until = _coerce_datetime(summary.get("valid_until"))
    return valid_until is not None and valid_until <= reference_time


def _missing_evidence_dimensions(spans: list[dict[str, Any]]) -> list[str]:
    if not spans:
        return ["trace_span", *[f"{kind}_span" for kind in REQUIRED_SPAN_KINDS]]
    span_kinds = {str(span.get("span_kind") or "") for span in spans}
    return [
        f"{span_kind}_span"
        for span_kind in REQUIRED_SPAN_KINDS
        if span_kind not in span_kinds
    ]


def _evidence_completeness(missing_dimensions: list[str]) -> float:
    total_dimensions = 1 + len(REQUIRED_SPAN_KINDS)
    missing_count = len(missing_dimensions)
    return round(max(0.0, (total_dimensions - missing_count) / total_dimensions), 4)


def _evidence_level(
    run: dict[str, Any], missing_dimensions: list[str], expired: bool
) -> str:
    if expired:
        return "L3"
    if "trace_span" in missing_dimensions:
        return "L3"
    if missing_dimensions or run.get("status") != "succeeded":
        return "L4"
    return "L5"


def _evidence_confidence(
    run: dict[str, Any], completeness: float, expired: bool
) -> float:
    if expired:
        return 0.0
    status_factor = 1.0 if run.get("status") == "succeeded" else 0.85
    return round(max(0.0, min(1.0, completeness * status_factor)), 4)


def _source_event_ids(run: dict[str, Any], spans: list[dict[str, Any]]) -> list[str]:
    event_ids = [str(run.get("event_id") or "")]
    event_ids.extend(
        str(span.get("event_id") or "")
        for span in sorted(spans, key=lambda item: _safe_float(item.get("sequence_no")))
    )
    return [event_id for event_id in event_ids if event_id]


def _degraded_reason(missing_dimensions: list[str], expired: bool) -> str | None:
    if expired:
        return "summary_expired"
    if "trace_span" in missing_dimensions:
        return "trace_pending"
    if missing_dimensions:
        return "missing_span_dimensions"
    return None


def _average_evidence_completeness(
    repository: InMemoryRepository, runs: tuple[dict[str, Any], ...]
) -> float:
    if not runs:
        return 0.0
    values = []
    for run in runs:
        try:
            summary = build_runtime_evidence_summary(repository, str(run["run_id"]))
        except AgentOpsError:
            values.append(0.0)
        else:
            values.append(float(summary["completeness"]))
    return round(sum(values) / len(values), 4)


def _recommended_action(
    *,
    sample_size: int,
    failure_rate: float,
    policy_block_count: int,
    evidence_completeness: float,
    expired: bool,
) -> str:
    if expired:
        return "expired"
    if sample_size == 0:
        return "watching"
    if policy_block_count > 0 or failure_rate >= 0.5:
        return "disable_recommended"
    if failure_rate > 0 or evidence_completeness < 0.8:
        return "use_with_caution"
    return "usable"


def _health_confidence(
    sample_size: int,
    failure_rate: float,
    evidence_completeness: float,
    expired: bool,
) -> float:
    if expired or sample_size == 0:
        return 0.0
    sample_factor = min(1.0, sample_size / 5)
    return round(sample_factor * evidence_completeness * (1 - failure_rate), 4)


def _ratio(numerator: int, denominator: int) -> float:
    if denominator <= 0:
        return 0.0
    return numerator / denominator


def _safe_float(value: Any) -> float:
    if isinstance(value, bool):
        return 0.0
    try:
        numeric_value = float(value)
    except (TypeError, ValueError, OverflowError):
        return 0.0
    return numeric_value


def _coerce_datetime(value: Any) -> datetime | None:
    if value is None:
        return None
    if isinstance(value, datetime):
        return value.astimezone(UTC) if value.tzinfo else value.replace(tzinfo=UTC)
    if isinstance(value, str):
        try:
            parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
        except ValueError:
            return None
        return parsed.astimezone(UTC) if parsed.tzinfo else parsed.replace(tzinfo=UTC)
    return None


def _iso(value: datetime) -> str:
    return value.astimezone(UTC).isoformat()
