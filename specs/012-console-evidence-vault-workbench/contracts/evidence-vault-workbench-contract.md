# 契约：Evidence Vault 访问工作台

## AO12-CT-001 evidenceVault 数据域

`GET /v1/console/snapshot` 返回的 `consoleData.evidenceVault` 必须包含：

- `requests`
- `grants`
- `auditTrail`
- `guardrails`

## AO12-CT-002 申请、授权和审计字段

每条 `requests[]` 必须包含 `id`、`evidence_id`、`run_id`、`requester`、`reason`、`status`、`denied_scope`、`audit_id`、`ttl_summary`、`primary_action`、`safety_note`。

每条 `grants[]` 必须包含 `id`、`evidence_id`、`requester`、`status`、`scope`、`expires_at`、`audit_id`、`consumption_policy`。

每条 `auditTrail[]` 必须包含 `id`、`evidence_id`、`stage`、`occurred_at`、`summary`、`owner`、`status`、`audit_id`。

## AO12-CT-003 原文访问红线

`evidenceVault` 任意层级不得包含：

- `raw_payload`
- `download_url`
- `raw_url`
- `original_url`
- `raw_access_url`
- URL 字符串
- PR 原文、diff、patch 或代码片段字段

## AO12-CT-004 红线状态下一步

- `redaction_failed` 只能给出“仅查看哈希告警”等安全动作。
- `permission_denied` 只能给出“补充申请理由”等申请动作。
- `approved_limited` 只能展示授权记录和到期信息，不展示原文。

## AO12-CT-005 前端契约

证据检索页必须展示：

- “原文访问申请”
- “限时授权”
- “审计轨迹”
- “默认不展示原文”

前端 validator 必须拒绝 malformed `evidenceVault`、危险 URL、raw 字段、PR 原文类字段和自动批准/自动写回动作。
