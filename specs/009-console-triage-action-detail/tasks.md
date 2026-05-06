# 任务分解：Console 处置详情与行动面板

**功能编号**：`009-console-triage-action-detail`

## Batch 1：规格与契约

### T11 冻结 009 规格

- **状态**：已完成
- **文件**：`spec.md`、`plan.md`、`contracts/triage-action-detail-contract.md`
- **验收**：AO9-CT-001 到 AO9-CT-005 明确。

## Batch 2：后端处置详情视图模型

### T21 扩展 Console snapshot

- **状态**：已完成
- **文件**：`src/agentops/api/console_snapshot.py`
- **验收**：snapshot 包含 `actionWorkbench.details`，并与 `operationCenter` 可关联。

## Batch 3：前端处置详情抽屉

### T31 新增只读处置详情体验

- **状态**：已完成
- **文件**：`App.js`、`AppShell.js`、风险/审批/证据页面、`styles.css`
- **验收**：用户可从风险、审批、证据、通知、待办、搜索打开中文处置详情。

## Batch 4：验证与归档

### T41 契约与回归测试

- **状态**：已完成
- **命令**：`uv run pytest tests/contract/test_ao9_ct_console_triage_action_detail.py -q`、`uv run pytest tests -q`、`uv run ruff check src tests`、`npm test`、`npm run build`、`uv run ai-sdlc verify constraints`
