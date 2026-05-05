# Contract Tests：AgentOps 阶段 2 Policy / Approval / Grant / Evidence Vault

## AO2-CT-001 Policy Check v2

- **正例**：active Grant 且 resource_scope 匹配时，Policy Check 返回 `conditional_allow`，包含 `grant_id`、`audit_id`、`policy_version`、`valid_until`。
- **反例**：高风险动作缺 `resource_scope` 返回 `POLICY_SCOPE_REQUIRED`；Policy Service 不可用且高风险时返回 `block` + `fallback_action=require_online`。
- **优先级红线**：即使存在 active Grant，`global_deny`、`iam_or_security_deny`、`project_scope_deny`、`agent_or_version_disabled`、`policy_block` 也必须覆盖 `conditional_allow/allow`，分别返回 deny/block 语义和 denied_scope。
- **状态/兼容性**：`policy_version` minor version 向后兼容；`policy_state_known=false` 不得显示为 allow。

## AO2-CT-002 Approval Lifecycle

- **正例**：`approval_required` 创建 ApprovalRequest，包含 requester、approver_scope、reason、affected_actions、sla_due_at、audit_id；approved 后可签发 Grant。
- **绑定红线**：Grant 签发必须与 Approval 原始 `policy_check_id`、`action`、`agent_id`、`skill_id`、`resource_scope`、`policy_version`、`requester` 完全绑定；扩大 scope、替换 action 或更换主体返回 `GRANT_SCOPE_ESCALATION_DENIED` 或 `GRANT_APPROVAL_BINDING_MISMATCH`。
- **反例**：requester 自批返回 `APPROVAL_SELF_APPROVAL_DENIED`；expired/rejected/revoked approval 不得签发 Grant。
- **状态流转**：pending -> approved / rejected / needs_more_info / expired / escalated / revoked；终态不可回到 pending。

## AO2-CT-003 Capability Grant

- **正例**：active Grant 可消费，记录 `consumed_at`、`audit_id`、`policy_version`。
- **反例**：revoked Grant 返回 `GRANT_REVOKED`；expired Grant 返回 `GRANT_EXPIRED`；scope mismatch 返回 `GRANT_SCOPE_MISMATCH`。
- **状态流转**：active -> revoked / expired；revoked 与 expired 不得再次 active。

## AO2-CT-004 Evidence Vault Summary

- **正例**：默认返回 `redacted_summary`、`payload_hash`、`raw_access_state`、`access_policy`、`retention_policy`、`audit_id`，不返回 `raw_payload`。
- **反例**：无 RawAccessGrant 请求原文返回 `RAW_ACCESS_DENIED`；redaction_failed 返回 `EVIDENCE_REDACTION_FAILED` 状态且不返回原文、不得返回不可信 `redacted_summary` 内容，只能返回 `payload_hash`、`safe_empty=true` 和告警动作。
- **限时授权**：approved RawAccessGrant 未过期时返回 approved access state；过期后返回 `RAW_ACCESS_DENIED` 或 `RAW_ACCESS_EXPIRED`。

## AO2-CT-005 Policy Requirement Summary

- **正例**：Store/CLI 获得 `required_by`、`source`、`issuer`、`policy_owner`、`policy_version`、`can_ignore`、`affected_actions`、`deep_links`、`plain_language`、`primary_action`、`secondary_action`。
- **可行动结构**：`deep_links` 必须包含 `approval_url`、`policy_url`、`evidence_url`、`return_url`；approval/block 的 `can_ignore=false`，warn 的 `can_ignore=true`。
- **反例**：consumer schema 不兼容返回 `POLICY_SUMMARY_SCHEMA_UNSUPPORTED`，不得返回半结构化字段。
- **兼容性**：schema minor version 向后兼容；warn 策略可 `can_ignore=true`，approval/block 不可忽略。

## AO2-CT-006 Stage-2 SLO & Admin Models

- **正例**：Policy Check、Approval Service、Evidence Query 的 healthy/degraded/unknown 状态可映射到 Policy Center、Approval Center、Evidence Explorer 和 Risk Triage。
- **页面模型红线**：每个页面状态必须包含 `state`、`display_name`、`plain_language`、`severity`、`primary_action`、`secondary_action`、`owner_hint`、`audit_id` 或 `request_id`；permission_denied 必须包含 `denied_scope` 且不得暴露敏感事实。
- **反例**：缺 SLO 数据不得显示 healthy；Policy Check P95 > 800ms 或错误率 > 1% 必须 degraded。
- **降级语义**：每个 degraded/unknown 状态必须包含 `degrade_action`、`owner_hint`、`request_id` 或 `audit_id`、`review_required`。
