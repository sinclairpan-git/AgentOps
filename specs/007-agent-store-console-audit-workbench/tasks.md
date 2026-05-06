# 任务分解：Agent Store 发现与运行审计控制台

**功能编号**：`007-agent-store-console-audit-workbench`

## Batch 1：契约与文档

### T11 冻结 007 规格

- **状态**：已完成
- **文件**：`spec.md`、`plan.md`、`contracts/agent-store-console-audit-workbench-contract.md`
- **验收**：AO7-CT-001 到 AO7-CT-006 明确。

## Batch 2：后端工作台数据

### T21 扩展 Console snapshot

- **状态**：已完成
- **文件**：`src/agentops/api/console_snapshot.py`
- **验收**：snapshot 包含 `agentStore`，不暴露 raw payload。

## Batch 3：前端工作台

### T31 新增 Agent Store 审计页面

- **状态**：已完成
- **文件**：`apps/agentops-console/src/views/AgentStoreAuditView.js`、`App.js`、`mockAgentOpsData.js`、`agentOpsApiClient.js`
- **验收**：导航可进入“Agent Store 审计”，展示发现队列、运行审计和回显摘要。

## Batch 4：验证与交付

### T41 契约与回归测试

- **状态**：已完成
- **命令**：`uv run pytest tests/contract/test_ao7_ct_agent_store_console_audit_workbench.py -q`、`uv run pytest tests -q`、`uv run ruff check src tests`、`npm test`、`npm run build`、`uv run ai-sdlc verify constraints`
- **验收**：全部通过后推送 PR。
