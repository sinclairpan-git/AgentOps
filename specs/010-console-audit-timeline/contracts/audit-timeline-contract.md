# 契约：Console 处置审计时间线

## AO10-CT-001 时间线字段

每个 `actionWorkbench.details[]` 必须包含 `timeline` 数组，且每个节点包含：

- `id`
- `stage`
- `occurred_at`
- `title`
- `body`
- `owner`
- `status`

节点不得包含 `raw_payload`、下载地址或 Evidence Vault 原文。

## AO10-CT-002 审计包摘要

每个 `actionWorkbench.details[]` 必须包含 `audit_packet` 对象，字段为：

- `packet_id`
- `summary`
- `export_state`
- `evidence_refs`
- `echo_targets`
- `retention_policy`
- `safety_note`

`export_state` 必须是只读状态，不能表示真实文件已下载。

## AO10-CT-003 三类高价值处置覆盖

以下详情必须生成时间线和审计包：

- `action_approval_*`
- `action_evidence_*`
- `action_gap_*`

## AO10-CT-004 前端中文展示

处置抽屉必须展示：

- 处置时间线
- 审计包摘要
- 导出状态
- 回显目标
- 只读复核包

## AO10-CT-005 Schema 安全回退

前端 schema 校验必须拒绝缺少 `timeline` 或 `audit_packet` 的后端快照，避免用户看到半截处置上下文。
