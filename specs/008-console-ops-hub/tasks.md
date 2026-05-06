# 任务分解：Console 运营工作台基础层

**功能编号**：`008-console-ops-hub`

## Batch 1：规格与契约

### T11 冻结 008 规格

- **状态**：已完成
- **文件**：`spec.md`、`plan.md`、`contracts/console-ops-hub-contract.md`
- **验收**：AO8-CT-001 到 AO8-CT-004 明确。

## Batch 2：后端运营视图模型

### T21 扩展 Console snapshot

- **状态**：已完成
- **文件**：`src/agentops/api/console_snapshot.py`
- **验收**：snapshot 包含 `operationCenter.notifications/todos/searchIndex`。

## Batch 3：前端 Shell

### T31 新增搜索、通知、待办入口

- **状态**：已完成
- **文件**：`apps/agentops-console/src/components/AppShell.js`、`styles.css`
- **验收**：用户可在顶部搜索并进入相关治理页面，可打开通知中心和待办中心。

## Batch 4：验证

### T41 契约与回归测试

- **状态**：已完成
- **命令**：`uv run pytest tests/contract/test_ao8_ct_console_ops_hub.py -q`、`uv run pytest tests -q`、`uv run ruff check src tests`、`npm test`、`npm run build`、`uv run ai-sdlc verify constraints`
