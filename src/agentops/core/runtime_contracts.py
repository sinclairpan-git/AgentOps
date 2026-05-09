"""AO31 runtime governance contract and state registries."""

from __future__ import annotations

import hashlib
import json
from collections.abc import Mapping

from agentops.core.errors import AgentOpsError
from agentops.models.runtime import (
    ContractRegistryEntry,
    ErrorCodeDefinition,
    StateRegistryEntry,
)


DOMAIN_OWNERS = {
    "AgentOps",
    "Agent Runtime",
    "Agent Store",
    "Ai_AutoSDLC",
    "Contract Registry",
}

CONTRACT_PARTIES = DOMAIN_OWNERS | {"Runtime", "Ops", "Store", "Policy Service"}


def _entry(
    contract_id: str,
    *,
    domain_owner: str,
    producer: str,
    consumers: tuple[str, ...],
    schema_version: str,
    required_fields: tuple[str, ...],
    optional_fields: tuple[str, ...] = (),
    enum_fields: dict[str, tuple[str, ...]] | None = None,
    state_registry_refs: tuple[str, ...] = (),
    error_codes: tuple[str, ...],
    contract_tests: tuple[str, ...],
    compatibility_policy: str = "no_breaking_in_p0",
) -> ContractRegistryEntry:
    return ContractRegistryEntry(
        contract_id=contract_id,
        domain_owner=domain_owner,
        producer=producer,
        consumers=consumers,
        schema_version=schema_version,
        required_fields=frozenset(required_fields),
        optional_fields=frozenset(optional_fields),
        enum_fields={
            key: frozenset(values) for key, values in (enum_fields or {}).items()
        },
        state_registry_refs=state_registry_refs,
        error_codes=error_codes,
        contract_tests=contract_tests,
        compatibility_policy=compatibility_policy,
    )


CONTRACT_REGISTRY: dict[str, ContractRegistryEntry] = {
    "runtime_run.v1": _entry(
        "runtime_run.v1",
        domain_owner="Agent Runtime",
        producer="Runtime",
        consumers=("AgentOps", "Agent Store"),
        schema_version="runtime_run.v1",
        required_fields=(
            "runtime_id",
            "runtime_version",
            "execution_environment",
            "session_id",
            "run_id",
            "attempt_no",
            "agent_id",
            "version",
            "trigger_source",
            "isolation_profile",
            "policy_bundle_version",
            "status",
            "terminal_reason",
        ),
        optional_fields=("parent_run_id",),
        enum_fields={
            "status": (
                "created",
                "running",
                "approval_paused",
                "succeeded",
                "failed",
                "timeout",
                "cancelled",
                "blocked",
            ),
            "execution_environment": ("local", "managed", "ci", "unknown"),
        },
        state_registry_refs=(
            "running",
            "approval_paused",
            "succeeded",
            "failed",
            "cancelled",
            "timeout",
            "blocked",
        ),
        error_codes=("RUNTIME_RUN_INVALID", "RUNTIME_RUN_STATE_INVALID"),
        contract_tests=("AO31-CT-001", "AO31-CT-003"),
    ),
    "trace_span.v1": _entry(
        "trace_span.v1",
        domain_owner="Agent Runtime",
        producer="Runtime",
        consumers=("AgentOps",),
        schema_version="trace_span.v1",
        required_fields=(
            "trace_id",
            "span_id",
            "parent_span_id",
            "run_id",
            "span_kind",
            "operation_name",
            "status_code",
            "start_time",
            "end_time",
            "attempt_no",
            "input_ref",
            "output_ref",
            "token_usage",
            "cost_estimate",
            "grant_id",
            "guardrail_result_refs",
            "error_code",
            "retryable",
        ),
        enum_fields={
            "span_kind": (
                "agent",
                "workflow",
                "model",
                "tool",
                "retrieval",
                "handoff",
                "approval",
                "guardrail",
                "artifact",
                "system",
            ),
            "status_code": ("ok", "error", "unset", "blocked", "waiting"),
        },
        state_registry_refs=("trace_pending", "degraded"),
        error_codes=("TRACE_SPAN_INVALID", "TRACE_SPAN_KIND_UNSUPPORTED"),
        contract_tests=("AO31-CT-001", "AO31-CT-004", "AO31-CT-005"),
    ),
    "event_envelope.v1": _entry(
        "event_envelope.v1",
        domain_owner="Contract Registry",
        producer="Runtime",
        consumers=("AgentOps",),
        schema_version="event_envelope.v1",
        required_fields=(
            "event_id",
            "schema_version",
            "event_type",
            "event_type_version",
            "timestamp",
            "integration_mode",
            "enterprise_state",
            "sequence_no",
            "idempotency_key",
            "source_trust",
            "signature",
            "data_classification",
            "redaction_policy",
            "payload_hash",
            "payload_ref",
        ),
        enum_fields={
            "source_trust": ("verified", "signed", "unsigned", "suspected"),
            "integration_mode": (
                "standalone",
                "enterprise_managed",
                "custom_sink",
                "unknown",
            ),
        },
        state_registry_refs=("schema_rejected", "signature_failed"),
        error_codes=(
            "EVENT_SCHEMA_UNSUPPORTED",
            "EVENT_SIGNATURE_INVALID",
            "EVENT_IDEMPOTENCY_CONFLICT",
        ),
        contract_tests=("AO31-CT-001", "AO31-CT-002"),
    ),
    "policy_decision.v1": _entry(
        "policy_decision.v1",
        domain_owner="AgentOps",
        producer="Policy Service",
        consumers=("Runtime", "Agent Store"),
        schema_version="policy_decision.v1",
        required_fields=(
            "decision_id",
            "request_id",
            "subject",
            "resource",
            "action",
            "decision",
            "reason_code",
            "policy_set_version",
            "obligations",
            "constraints",
            "ttl",
            "fallback_action",
        ),
        enum_fields={
            "decision": (
                "allow",
                "warn",
                "approval_required",
                "block",
                "policy_unavailable",
            ),
            "fallback_action": ("allow", "warn", "require_online", "block"),
        },
        state_registry_refs=("blocked", "policy_unavailable"),
        error_codes=("CONTRACT_ENUM_UNREGISTERED", "POLICY_SCOPE_REQUIRED"),
        contract_tests=("AO31-CT-001", "AO31-CT-006"),
    ),
    "capability_grant.v1": _entry(
        "capability_grant.v1",
        domain_owner="AgentOps",
        producer="Policy Service",
        consumers=("Runtime", "Agent Store"),
        schema_version="capability_grant.v1",
        required_fields=(
            "grant_id",
            "decision_id",
            "agent_id",
            "version",
            "artifact_hash",
            "installation_id",
            "device_id",
            "user_id",
            "session_id",
            "run_id",
            "skill_id",
            "resource_scope",
            "remaining_uses",
            "offline_allowed",
            "expires_at",
            "signature",
            "key_id",
        ),
        error_codes=("GRANT_EXPIRED", "GRANT_REVOKED"),
        contract_tests=("AO31-CT-001",),
    ),
    "approval.v1": _entry(
        "approval.v1",
        domain_owner="AgentOps",
        producer="AgentOps",
        consumers=("Runtime", "Agent Store", "AgentOps"),
        schema_version="approval.v1",
        required_fields=(
            "approval_id",
            "requested_by",
            "on_behalf_of",
            "approver_policy_ref",
            "resource_scope",
            "risk_reason",
            "pause_token",
            "resume_token",
            "sla_due_at",
            "decision",
            "decision_reason",
            "expires_at",
        ),
        enum_fields={
            "decision": ("pending", "approved", "rejected", "expired", "withdrawn")
        },
        state_registry_refs=("approval_paused",),
        error_codes=("APPROVAL_EXPIRED", "APPROVAL_SCOPE_DENIED"),
        contract_tests=("AO31-CT-001", "AO31-CT-006"),
    ),
    "evidence_summary.v1": _entry(
        "evidence_summary.v1",
        domain_owner="AgentOps",
        producer="AgentOps",
        consumers=("Agent Store", "Ai_AutoSDLC"),
        schema_version="evidence_summary.v1",
        required_fields=(
            "run_id",
            "trace_id",
            "evidence_level",
            "source_event_ids",
            "freshness",
            "valid_until",
            "confidence",
            "missing_dimensions",
            "redaction_state",
            "raw_access_state",
            "degraded_reason",
        ),
        error_codes=("RAW_ACCESS_REQUIRED", "EVIDENCE_SUMMARY_EXPIRED"),
        contract_tests=("AO31-CT-001",),
    ),
    "health_summary.v1": _entry(
        "health_summary.v1",
        domain_owner="AgentOps",
        producer="AgentOps",
        consumers=("Agent Store", "Runtime"),
        schema_version="health_summary.v1",
        required_fields=(
            "agent_id",
            "version",
            "health_template_id",
            "calculation_window",
            "sample_size",
            "success_rate",
            "failure_rate",
            "evidence_completeness",
            "policy_block_count",
            "confidence",
            "valid_until",
            "recommended_action",
            "appeal_state",
        ),
        enum_fields={
            "recommended_action": (
                "usable",
                "watching",
                "use_with_caution",
                "disable_recommended",
                "disabled",
                "expired",
            )
        },
        error_codes=("HEALTH_SUMMARY_EXPIRED",),
        contract_tests=("AO31-CT-001",),
    ),
}


def _state(
    machine_value: str,
    *,
    display_name: str,
    plain_language_explanation: str,
    severity: str,
    primary_action: str,
    secondary_action: str | None = None,
    terminal_state: bool = False,
    allowed_next_states: tuple[str, ...] = (),
    audit_required: bool = True,
    owner: str = "AgentOps",
) -> StateRegistryEntry:
    return StateRegistryEntry(
        machine_value=machine_value,
        display_name=display_name,
        plain_language_explanation=plain_language_explanation,
        severity=severity,
        primary_action=primary_action,
        secondary_action=secondary_action,
        terminal_state=terminal_state,
        allowed_next_states=allowed_next_states,
        audit_required=audit_required,
        owner=owner,
        expected_display_name=display_name,
    )


STATE_REGISTRY: dict[str, StateRegistryEntry] = {
    "running": _state(
        "running",
        display_name="运行中",
        plain_language_explanation="Agent 正在 Runtime 中执行。",
        severity="info",
        primary_action="查看链路",
        allowed_next_states=(
            "approval_paused",
            "succeeded",
            "failed",
            "cancelled",
            "timeout",
            "blocked",
        ),
        owner="Agent Runtime",
    ),
    "approval_paused": _state(
        "approval_paused",
        display_name="等待审批",
        plain_language_explanation="运行已暂停，等待审批通过后才能继续。",
        severity="warning",
        primary_action="查看审批进度",
        secondary_action="撤回申请",
        allowed_next_states=("running", "blocked", "failed"),
    ),
    "succeeded": _state(
        "succeeded",
        display_name="成功",
        plain_language_explanation="本次运行已经完成。",
        severity="success",
        primary_action="查看摘要",
        terminal_state=True,
        owner="Agent Runtime",
    ),
    "failed": _state(
        "failed",
        display_name="失败",
        plain_language_explanation="本次运行失败，需要查看错误和重试条件。",
        severity="critical",
        primary_action="查看错误",
        terminal_state=True,
        owner="Agent Runtime",
    ),
    "cancelled": _state(
        "cancelled",
        display_name="已取消",
        plain_language_explanation="本次运行已被用户或系统取消。",
        severity="info",
        primary_action="查看记录",
        terminal_state=True,
        owner="Agent Runtime",
    ),
    "timeout": _state(
        "timeout",
        display_name="已超时",
        plain_language_explanation="本次运行超过允许时间。",
        severity="warning",
        primary_action="查看超时原因",
        terminal_state=True,
        owner="Agent Runtime",
    ),
    "blocked": _state(
        "blocked",
        display_name="已阻断",
        plain_language_explanation="运行被策略、权限或安全规则阻断。",
        severity="critical",
        primary_action="查看原因",
        secondary_action="发起申诉",
        terminal_state=True,
    ),
    "trace_pending": _state(
        "trace_pending",
        display_name="执行记录待上报",
        plain_language_explanation="Runtime 已产生运行记录，但链路还未完整送达 AgentOps。",
        severity="warning",
        primary_action="重试上报",
        secondary_action="查看诊断",
        audit_required=False,
    ),
    "degraded": _state(
        "degraded",
        display_name="已降级",
        plain_language_explanation="由于证据、签名、链路或权限不完整，只能按降级事实展示。",
        severity="warning",
        primary_action="查看降级原因",
    ),
    "schema_rejected": _state(
        "schema_rejected",
        display_name="格式被拒绝",
        plain_language_explanation="上报内容不符合当前支持的 schema。",
        severity="critical",
        primary_action="查看字段错误",
    ),
    "signature_failed": _state(
        "signature_failed",
        display_name="签名失败",
        plain_language_explanation="上报签名缺失或验证失败，不能进入可信事实。",
        severity="critical",
        primary_action="重新签名上报",
    ),
    "policy_unavailable": _state(
        "policy_unavailable",
        display_name="运行规则服务不可用",
        plain_language_explanation="策略服务暂时不可用，高风险动作不能默认为安全。",
        severity="warning",
        primary_action="稍后重试",
    ),
}


ERROR_CODE_REGISTRY: dict[str, ErrorCodeDefinition] = {
    "CONTRACT_OWNER_REQUIRED": ErrorCodeDefinition(
        "CONTRACT_OWNER_REQUIRED",
        500,
        False,
        "契约缺少负责人。",
        "Contract registry entries require domain_owner.",
        True,
    ),
    "CONTRACT_PARTY_UNREGISTERED": ErrorCodeDefinition(
        "CONTRACT_PARTY_UNREGISTERED",
        500,
        False,
        "契约生产方或消费方未登记。",
        "Contract producer/consumer must be registered.",
        True,
    ),
    "CONTRACT_ENUM_UNREGISTERED": ErrorCodeDefinition(
        "CONTRACT_ENUM_UNREGISTERED",
        400,
        False,
        "字段值未登记。",
        "Field value is outside the registered enum.",
        True,
    ),
    "STATE_DISPLAY_MISMATCH": ErrorCodeDefinition(
        "STATE_DISPLAY_MISMATCH",
        500,
        False,
        "状态展示定义不一致。",
        "State registry display name drift detected.",
        True,
    ),
    "EVENT_SCHEMA_UNSUPPORTED": ErrorCodeDefinition(
        "EVENT_SCHEMA_UNSUPPORTED",
        400,
        False,
        "事件格式版本不支持。",
        "Unsupported event schema_version.",
        True,
    ),
    "EVENT_SIGNATURE_INVALID": ErrorCodeDefinition(
        "EVENT_SIGNATURE_INVALID",
        401,
        False,
        "事件签名无效。",
        "Invalid runtime event signature.",
        True,
    ),
    "EVENT_IDEMPOTENCY_CONFLICT": ErrorCodeDefinition(
        "EVENT_IDEMPOTENCY_CONFLICT",
        409,
        False,
        "幂等键冲突。",
        "Idempotency key maps to a different payload.",
        True,
    ),
    "TRACE_PARENT_MISSING": ErrorCodeDefinition(
        "TRACE_PARENT_MISSING",
        202,
        True,
        "执行链路缺少父步骤。",
        "Trace span parent is missing; timeline must be degraded.",
        False,
    ),
    "TRACE_SPAN_KIND_UNSUPPORTED": ErrorCodeDefinition(
        "TRACE_SPAN_KIND_UNSUPPORTED",
        400,
        False,
        "执行步骤类型不支持。",
        "Trace span_kind is not registered.",
        True,
    ),
}


def get_contract(contract_id: str) -> ContractRegistryEntry:
    return CONTRACT_REGISTRY[contract_id]


def get_state(machine_value: str) -> StateRegistryEntry:
    return STATE_REGISTRY[machine_value]


def validate_contract_registry(
    registry: Mapping[str, ContractRegistryEntry],
) -> None:
    for contract_id, entry in registry.items():
        if not entry.domain_owner:
            raise AgentOpsError(
                "CONTRACT_OWNER_REQUIRED",
                f"{contract_id} requires a domain owner.",
            )
        if entry.domain_owner not in DOMAIN_OWNERS:
            raise AgentOpsError(
                "CONTRACT_OWNER_REQUIRED",
                f"{contract_id} has an unregistered domain owner.",
            )
        parties = (entry.producer, *entry.consumers)
        if any(party not in CONTRACT_PARTIES for party in parties):
            raise AgentOpsError(
                "CONTRACT_PARTY_UNREGISTERED",
                f"{contract_id} references an unregistered producer or consumer.",
            )
        if not entry.required_fields or not entry.contract_tests:
            raise AgentOpsError(
                "CONTRACT_OWNER_REQUIRED",
                f"{contract_id} requires fields and contract tests.",
            )
        for error_code in entry.error_codes:
            if error_code not in ERROR_CODE_REGISTRY and not _is_existing_error(
                error_code
            ):
                raise AgentOpsError(
                    "CONTRACT_ENUM_UNREGISTERED",
                    f"{contract_id} references unknown error code {error_code}.",
                )


def validate_contract_value(contract_id: str, field_name: str, value: str) -> None:
    entry = get_contract(contract_id)
    allowed = entry.enum_fields.get(field_name)
    if allowed is None:
        raise AgentOpsError(
            "CONTRACT_ENUM_UNREGISTERED",
            f"{field_name} is not a registered enum field.",
        )
    if value not in allowed:
        raise AgentOpsError(
            "CONTRACT_ENUM_UNREGISTERED",
            f"{value} is not allowed for {contract_id}.{field_name}.",
        )


def validate_state_registry(registry: Mapping[str, StateRegistryEntry]) -> None:
    for machine_value, entry in registry.items():
        if machine_value != entry.machine_value:
            raise AgentOpsError(
                "STATE_DISPLAY_MISMATCH",
                "State registry key and machine_value diverged.",
            )
        expected = entry.expected_display_name or entry.display_name
        if entry.display_name != expected:
            raise AgentOpsError(
                "STATE_DISPLAY_MISMATCH",
                f"{machine_value} display name changed from {expected}.",
            )
        if not entry.display_name or not entry.plain_language_explanation:
            raise AgentOpsError(
                "STATE_DISPLAY_MISMATCH",
                f"{machine_value} requires user-facing state text.",
            )


def contract_registry_hash(registry: Mapping[str, ContractRegistryEntry]) -> str:
    payload = {
        contract_id: entry.to_stable_dict()
        for contract_id, entry in sorted(registry.items())
    }
    serialized = json.dumps(payload, ensure_ascii=False, sort_keys=True)
    return hashlib.sha256(serialized.encode("utf-8")).hexdigest()


def _is_existing_error(error_code: str) -> bool:
    prefixes = (
        "POLICY_",
        "GRANT_",
        "APPROVAL_",
        "RAW_ACCESS_",
        "EVIDENCE_",
        "HEALTH_",
        "RUNTIME_",
        "TRACE_",
    )
    return error_code.startswith(prefixes)
