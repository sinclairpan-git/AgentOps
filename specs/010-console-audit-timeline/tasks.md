# 任务分解：Console 处置审计时间线

**功能编号**：`010-console-audit-timeline`

## Batch 1：规格与契约

### T11 冻结 010 规格

- **状态**：已完成
- **文件**：`spec.md`、`plan.md`、`contracts/audit-timeline-contract.md`
- **验收**：AO10-CT-001 到 AO10-CT-005 明确。

## Batch 2：后端处置审计视图模型

### T21 扩展 Action Detail

- **状态**：已完成
- **文件**：`src/agentops/api/console_snapshot.py`
- **验收**：每条 detail 生成 `timeline` 与 `audit_packet`，不包含 `raw_payload`。

## Batch 3：前端抽屉展示

### T31 新增时间线与审计包摘要

- **状态**：已完成
- **文件**：`AppShell.js`、`agentOpsApiClient.js`、`mockAgentOpsData.js`、`styles.css`
- **验收**：用户可在处置详情抽屉中查看中文时间线和只读复核包摘要。

## Batch 4：验证与归档

### T41 契约与回归测试

- **状态**：进行中
- **命令**：`uv run pytest tests/contract/test_ao10_ct_console_audit_timeline.py -q`、`npm test`、`npm run build`、`uv run ruff check src tests`、`uv run ai-sdlc verify constraints`
