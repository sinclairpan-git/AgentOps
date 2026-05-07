# Connector Health Workbench Contract

## AO14-CT-001 connectorWorkbench 数据域

`GET /v1/console/snapshot` 返回的 `consoleData.connectorWorkbench` 必须只包含：

- `health`
- `dlq`
- `syncTrail`
- `guardrails`

三类行必须与 `consoleData.connectors[]` 一一对应，并通过 `connector_id` 绑定原始连接器。

## AO14-CT-002 健康摘要

`health[]` 每行必须包含连接器、状态、新鲜度、限流状态、降级动作、证据影响、负责人、请求编号和只读安全说明。`materialized` 只能提示补齐 `verified_loaded` 机器证明。

## AO14-CT-003 DLQ 与 Outbox Replay

`dlq[]` 每行必须包含积压深度、最旧事件年龄、回放状态、回放窗口、降级策略、请求编号、审计编号和只读安全说明。回放只允许描述人工审批后的后端流程，本页不执行回放。

## AO14-CT-004 同步轨迹

`syncTrail[]` 每行必须包含阶段、发生时间、同步摘要、负责人、状态和请求编号。轨迹不得暴露原始事件、外部 URL 或下载入口。

## AO14-CT-005 红线

工作台任意层级不得包含：

- `raw_payload`
- `download_url`
- `raw_url`
- `raw_access_url`
- `original_url`
- `pullRequestBody`
- `pull_request_body`
- 外部 `http://` 或 `https://` 字符串

## AO14-CT-006 前端校验

前端 validator 必须拒绝 malformed `connectorWorkbench`、危险字段、伪 `verified_loaded`、降级连接器被篡改为健康、DLQ 回放状态被篡改为已完成等快照。
