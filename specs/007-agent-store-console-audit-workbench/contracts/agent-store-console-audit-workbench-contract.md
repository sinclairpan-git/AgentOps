# Agent Store 发现与运行审计控制台契约

## Snapshot 数据

`consoleData.agentStore` 必须存在，并包含：

- `discoveryGaps[]`：`gap_id`、`gap_type`、`agent_id`、`version`、`skill_id`、`state`、`severity`、`affected_runs`、`owner_hint`、`primary_action`、`audit_id`。
- `runAudits[]`：`audit_id`、`run_id`、`agent_id`、`version`、`registration_state`、`event_count`、`discovery_gap_ids`、`related_agent_versions`、`deep_links`。
- `storeSummaries[]`：`agent_id`、`agent_version`、`metadata_state`、`risk_state`、`evidence_level`、`confidence`、`policy_requirement`、`discovery_gap_ids`、`run_audit`、`calculated_at`、`valid_until`。
- `registryMap[]`：`agent_id`、`version`、`metadata_state`、`fact_owner`、`skill_count`。

## 前端路由

必须存在路由：

- `id`: `agent-store-audit`
- `label`: `Agent Store 审计`

## 安全约束

- 不得出现 `raw_payload` 字段。
- `fact_owner` 和 `registry_fact_owner` 必须保持 `Agent Store`。
- 页面不提供注册、上架、编辑按钮。
- 状态为 `materialized` 或 `unverified` 时，不得展示为已激活。

## 验收命令

- `uv run pytest tests/contract/test_ao7_ct_agent_store_console_audit_workbench.py -q`
- `npm test`
- `npm run build`
