# 任务分解：AgentOps Console API 快照与联调闭环

**功能编号**：`004-agentops-console-api-snapshot`  
**日期**：2026-05-06

## Batch 1：契约与后端快照

### T11 冻结 Console API 契约

- **优先级**：P0
- **文件**：`spec.md`、`plan.md`、`contracts/console-api-contract.md`
- **验收**：AO4-CT-001 到 AO4-CT-006 明确字段、安全红线和验证命令。

### T12 实现 Console snapshot builder

- **优先级**：P0
- **文件**：`src/agentops/api/console_snapshot.py`
- **验收**：返回 `schema_version`、`generated_at`、`source`、`routes`、`consoleData`，且不含 `raw_payload`。

## Batch 2：HTTP API 入口

### T21 实现标准库 HTTP server

- **优先级**：P0
- **文件**：`src/agentops/api/server.py`
- **验收**：`/v1/health`、`/v1/console/snapshot`、404 JSON、CORS 可测试。

### T22 补齐 Python contract tests

- **优先级**：P0
- **文件**：`tests/contract/test_ao4_ct_console_api.py`
- **验收**：AO4-CT-001 到 AO4-CT-005 自动化断言通过。

## Batch 3：Vue2 runtime data adapter

### T31 实现前端 API client

- **优先级**：P0
- **文件**：`apps/agentops-console/src/data/agentOpsApiClient.js`
- **验收**：API 成功返回 api_snapshot，失败返回 mock_fallback。

### T32 接入 App Shell 数据来源状态

- **优先级**：P0
- **文件**：`apps/agentops-console/src/App.js`、`components/AppShell.js`
- **验收**：加载、已连接、后端不可用三种中文状态可见。

### T33 补齐前端 contract tests

- **优先级**：P0
- **文件**：`apps/agentops-console/tests/console-contract.test.mjs`
- **验收**：AO4-CT-006 和中文错误提示断言通过。

## Batch 4：验证、评审与 close

### T41 本地验证

- **优先级**：P0
- **验收命令**：`npm test`、`npm run build`、`uv run pytest tests -q`、`uv run ruff check src tests`。

### T42 对抗评审与归档

- **优先级**：P0
- **文件**：`task-execution-log.md`、`development-summary.md`
- **验收**：UX 与 AI-Native/SDLC 对抗 agent 无 P0/P1 阻断意见。
