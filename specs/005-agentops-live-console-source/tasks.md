# 任务分解：AgentOps Console 运行事实数据源

**功能编号**：`005-agentops-live-console-source`

## Batch 1：契约与文档

### T11 冻结 005 规格

- **状态**：已完成
- **文件**：`spec.md`、`plan.md`、`contracts/live-console-source-contract.md`
- **验收**：AO5-CT-001 到 AO5-CT-005 明确。

## Batch 2：后端 live snapshot

### T21 扩展 repository-backed snapshot

- **状态**：已完成
- **文件**：`src/agentops/api/console_snapshot.py`
- **验收**：完整 L5 事件链可生成健康运行、证据摘要和质量信号。

### T22 新增事件接入 HTTP 入口

- **状态**：已完成
- **文件**：`src/agentops/api/server.py`
- **验收**：`POST /v1/events` 复用 `ingest_events_batch`，错误返回 JSON。

## Batch 3：前端状态

### T31 支持事实快照状态

- **状态**：已完成
- **文件**：`apps/agentops-console/src/data/agentOpsApiClient.js`、`components/StatusBadge.js`
- **验收**：repository-backed 快照展示“后端事实快照已连接”，`empty` 有中文标签。

## Batch 4：验证

### T41 契约与回归测试

- **状态**：已完成
- **命令**：`npm test`、`npm run build`、`uv run pytest tests -q`、`uv run ruff check src tests`
- **验收**：全部通过。
