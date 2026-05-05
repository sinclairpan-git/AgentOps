# 数据模型：AgentOps 阶段 2 Policy / Approval / Grant / Evidence Vault

**工作项**：`002-agentops-policy-approval-vault`  
**日期**：2026-05-05  

## 1. 模型边界

阶段 2 写 AgentOps 运行治理事实，不写 Agent Store 注册事实，不写 IAM 用户/角色主数据。

AgentOps 写以下事实：RuntimePolicy、PolicyCheck、PolicyDecision、ApprovalRequest、ApprovalDecision、CapabilityGrant、GrantConsumption、EvidenceVaultSummary、RawAccessRequest、RawAccessGrant、SloSnapshot、PolicyRequirementSummary。

## 2. runtime_policies

| 字段 | 类型 | 必填 | 说明 |
|---|---|---|---|
| policy_id | string | 是 | 策略 ID |
| skill_id | string | 否 | 适用 Skill |
| action | string | 是 | write/execute/network/deploy/config_change 等 |
| risk_level | enum | 是 | low/medium/high/critical |
| fallback_action | enum | 是 | allow/warn/require_online/block |
| approval_policy | object | 否 | approver_scope、SLA、材料要求 |
| grant_ttl_seconds | int | 是 | Grant TTL |
| enforcement_mode | enum | 是 | monitor/warn/enforce |
| owner | string | 是 | 策略 Owner |
| version | string | 是 | policy_version |
| status | enum | 是 | active/disabled/archived |

**索引**：`policy_id` unique；`skill_id, action, status`；`version`。

## 3. policy_checks

| 字段 | 类型 | 必填 | 说明 |
|---|---|---|---|
| policy_check_id | string | 是 | 检查 ID |
| action | string | 是 | 动作 |
| risk_level | enum | 是 | 风险等级 |
| resource_scope | object | 高风险是 | repo/project/env/resource |
| requester | string | 是 | 调用人 |
| agent_id | string | 是 | Agent |
| agent_version | string | 是 | 版本 |
| skill_id | string | 否 | Skill |
| session_id | string | 否 | Session |
| run_id | string | 否 | Run |
| grant_id | string | 否 | 尝试消费的 Grant |
| policy_version | string | 是 | 策略版本 |
| created_at | datetime | 是 | 创建时间 |

**索引**：`policy_check_id` unique；`run_id`；`requester, created_at`；`grant_id`。

## 4. policy_decisions

| 字段 | 类型 | 必填 | 说明 |
|---|---|---|---|
| decision_id | string | 是 | 裁决 ID |
| policy_check_id | string | 是 | 关联检查 |
| decision | enum | 是 | block/approval_required/warn/conditional_allow/allow |
| fallback_action | enum | 是 | allow/warn/require_online/block |
| policy_state_known | bool | 是 | 策略状态是否确定 |
| decision_reason | string | 是 | 白话原因 |
| required_approval_id | string | 否 | 审批 ID |
| grant_id | string | 否 | Grant ID |
| policy_version | string | 是 | 策略版本 |
| valid_until | datetime | 否 | 裁决有效期 |
| denied_scope | string | 否 | 拒绝范围 |
| audit_id | string | 是 | 审计 ID |

**索引**：`decision_id` unique；`policy_check_id`；`grant_id`；`audit_id`。

## 5. approval_requests

| 字段 | 类型 | 必填 | 说明 |
|---|---|---|---|
| approval_id | string | 是 | 审批 ID |
| policy_check_id | string | 是 | 来源检查 |
| requester | string | 是 | 申请人 |
| approver_scope | string | 是 | 审批人范围 |
| reason | string | 是 | 申请原因 |
| affected_actions | list | 是 | 影响动作 |
| resource_scope | object | 是 | 资源范围 |
| supplemental_materials | list | 否 | 补充材料 |
| status | enum | 是 | pending/approved/rejected/needs_more_info/expired/escalated/revoked |
| sla_due_at | datetime | 是 | SLA 截止 |
| created_at | datetime | 是 | 创建时间 |
| decided_at | datetime | 否 | 决策时间 |
| audit_id | string | 是 | 审计 ID |

**索引**：`approval_id` unique；`requester, created_at`；`approver_scope, status, sla_due_at`；`audit_id`。

## 6. approval_decisions

| 字段 | 类型 | 必填 | 说明 |
|---|---|---|---|
| approval_decision_id | string | 是 | 审批动作 ID |
| approval_id | string | 是 | 审批 |
| actor | string | 是 | 操作人 |
| action | enum | 是 | approve/reject/request_more_info/expire/escalate/revoke |
| reason | string | 是 | 操作原因 |
| created_at | datetime | 是 | 创建时间 |
| audit_id | string | 是 | 审计 ID |

**索引**：`approval_decision_id` unique；`approval_id, created_at`；`actor, created_at`。

## 7. capability_grants

| 字段 | 类型 | 必填 | 说明 |
|---|---|---|---|
| grant_id | string | 是 | Grant ID |
| approval_id | string | 是 | 来源 Approval |
| policy_check_id | string | 是 | 原始 PolicyCheck |
| action | string | 是 | 原始动作 |
| requester | string | 是 | 原始申请人 |
| agent_id | string | 是 | Agent |
| skill_id | string | 否 | Skill |
| resource_scope | object | 是 | 授权范围 |
| policy_version | string | 是 | 策略版本 |
| issued_at | datetime | 是 | 签发时间 |
| expires_at | datetime | 是 | 过期时间 |
| status | enum | 是 | active/expired/revoked |
| revoked_at | datetime | 否 | 撤销时间 |
| audit_id | string | 是 | 审计 ID |

**索引**：`grant_id` unique；`approval_id`；`policy_check_id`；`agent_id, skill_id, status`；`requester, expires_at`。

## 8. grant_consumptions

| 字段 | 类型 | 必填 | 说明 |
|---|---|---|---|
| consumption_id | string | 是 | 消费 ID |
| grant_id | string | 是 | Grant |
| policy_check_id | string | 是 | 检查 |
| consumed_at | datetime | 是 | 消费时间 |
| resource_scope | object | 是 | 实际请求范围 |
| audit_id | string | 是 | 审计 ID |

**索引**：`consumption_id` unique；`grant_id, consumed_at`；`policy_check_id`。

## 9. evidence_vault_summaries

| 字段 | 类型 | 必填 | 说明 |
|---|---|---|---|
| evidence_id | string | 是 | Evidence |
| run_id | string | 是 | Run |
| redacted_summary | object | 条件必填 | redaction_state=ok 时必填；failed 时不得返回摘要内容，只能返回 safe_empty 占位 |
| payload_hash | string | 是 | 原文 hash |
| raw_access_state | enum | 是 | summary_only/pending_approval/approved/expired/denied/redaction_failed |
| access_policy | string | 是 | 访问策略 |
| retention_policy | string | 是 | 保留策略 |
| redaction_state | enum | 是 | ok/failed |
| safe_empty | bool | 否 | redaction_state=failed 时必须为 true |
| audit_id | string | 是 | 审计 ID |

**索引**：`evidence_id` unique；`run_id`；`raw_access_state`。

## 10. raw_access_requests

| 字段 | 类型 | 必填 | 说明 |
|---|---|---|---|
| request_id | string | 是 | 申请 ID |
| evidence_id | string | 是 | Evidence |
| requester | string | 是 | 申请人 |
| reason | string | 是 | 原因 |
| approver_scope | string | 是 | 审批范围 |
| ttl_seconds | int | 是 | 授权 TTL |
| status | enum | 是 | pending/approved/rejected/expired |
| audit_id | string | 是 | 审计 ID |

**索引**：`request_id` unique；`evidence_id, status`；`requester, created_at`。

## 11. raw_access_grants

| 字段 | 类型 | 必填 | 说明 |
|---|---|---|---|
| raw_grant_id | string | 是 | Raw access grant |
| request_id | string | 是 | 原文申请 |
| evidence_id | string | 是 | Evidence |
| requester | string | 是 | 授权用户 |
| issued_at | datetime | 是 | 签发时间 |
| expires_at | datetime | 是 | 过期时间 |
| status | enum | 是 | active/expired/revoked |
| audit_id | string | 是 | 审计 ID |

**索引**：`raw_grant_id` unique；`request_id`；`evidence_id, requester, status`。

## 12. slo_snapshots

| 字段 | 类型 | 必填 | 说明 |
|---|---|---|---|
| snapshot_id | string | 是 | 快照 |
| service | enum | 是 | policy_check/approval_service/evidence_query |
| p95_ms | int | 否 | P95 |
| error_rate | float | 否 | 错误率 |
| status | enum | 是 | healthy/degraded/unknown |
| degrade_action | string | 是 | 降级动作 |
| review_required | bool | 是 | 是否需要复盘 |
| owner | string | 是 | Owner |
| request_id | string | 是 | 请求 ID |
| captured_at | datetime | 是 | 采集时间 |

**索引**：`snapshot_id` unique；`service, captured_at`；`status`。
