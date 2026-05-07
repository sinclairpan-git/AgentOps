# 任务分解：Console 质量与采纳洞察

**功能编号**：`011-console-quality-adoption-insights`

## Batch 1：规格与契约

### T11 冻结 011 规格

- **状态**：已完成
- **文件**：`spec.md`、`plan.md`、`contracts/quality-adoption-insights-contract.md`
- **验收**：AO11-CT-001 到 AO11-CT-005 明确。

## Batch 2：后端质量采纳视图模型

### T21 扩展 Console snapshot

- **状态**：已完成
- **文件**：`src/agentops/api/console_snapshot.py`
- **验收**：snapshot 包含 `adoption`，且只包含安全摘要。

## Batch 3：前端质量中心增强

### T31 新增采纳洞察体验

- **状态**：已完成
- **文件**：`QualityCenterView.js`、`agentOpsApiClient.js`、`mockAgentOpsData.js`、`styles.css`
- **验收**：用户可在质量中心查看采纳概览、质量解释链和复核队列。

## Batch 4：验证与归档

### T41 契约与回归测试

- **状态**：已完成
- **命令**：`uv run pytest tests/contract/test_ao11_ct_console_quality_adoption_insights.py -q`、`npm test`、`npm run build`、`uv run ruff check src tests`、`uv run ai-sdlc verify constraints`
