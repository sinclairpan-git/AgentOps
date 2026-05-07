# 契约：Approval Grant Workbench

## Snapshot 字段

`consoleData.approvalWorkbench` 必须是对象，且只包含：

- `queues`：审批队列摘要。
- `grants`：Grant 影响摘要。
- `auditTrail`：审批审计轨迹。
- `guardrails`：只读处置红线。

每个集合必须与 `consoleData.approvals` 按 `approval_id` 一一对应，不允许重复、遗漏或额外行。

## 队列行

队列行必须包含 `approval_id`、`requester`、`reason`、`affected_actions`、`status`、`sla_due_at`、`sla_state`、`approver_scope`、`supplemental_materials`、`primary_action`、`secondary_action`、`audit_id`、`denied_scope` 和 `safety_note`。

`pending` 与 `escalated` 只能展示人工处置入口；`approved` 只能查看审批记录；`revoked` 必须展示撤销原因和拒绝范围。

## Grant 行

Grant 行必须包含 `approval_id`、`grant_status`、`policy_version`、`resource_scope`、`ttl_summary`、`expires_at`、`revocation_state`、`audit_id` 和 `consumption_policy`。

`pending` 不得显示有效授权；`expired` 必须提示重新审批；`revoked` 必须阻止后续策略判断继续沿用旧授权；`active` 必须展示限时 Grant 和授权时限。

## 红线

- 不展示申请原文、PR 正文、下载链接或 raw access URL。
- 不执行批准、拒绝、撤销、生产写操作或 Grant 签发。
- Grant 必须绑定原始审批编号、策略版本、资源范围、授权时限和审计编号。
- 申请人不得作为唯一审批人批准自己的高风险动作。
