# 任务分解：Console Evidence Vault 访问工作台

**功能编号**：`012-console-evidence-vault-workbench`

## Batch 1：规格与契约

### T11 冻结 012 规格

- **状态**：已完成
- **文件**：`spec.md`、`plan.md`、`contracts/evidence-vault-workbench-contract.md`
- **验收**：AO12-CT-001 到 AO12-CT-005 明确。

## Batch 2：后端 Evidence Vault 视图模型

### T21 扩展 Console snapshot

- **状态**：已完成
- **文件**：`src/agentops/api/console_snapshot.py`
- **验收**：snapshot 包含 `evidenceVault`，且只包含申请、授权、审计摘要和保护规则。

## Batch 3：前端证据工作台增强

### T31 新增 Evidence Vault 访问工作台

- **状态**：已完成
- **文件**：`EvidenceExplorerView.js`、`agentOpsApiClient.js`、`mockAgentOpsData.js`、`styles.css`
- **验收**：用户可在证据检索页查看原文访问申请、限时授权、审计轨迹和保护规则。

## Batch 4：验证与归档

### T41 契约与回归测试

- **状态**：已完成
- **命令**：`uv run pytest tests/contract/test_ao12_ct_console_evidence_vault_workbench.py -q`、`uv run pytest tests -q`、`npm test`、`npm run build`、`uv run ruff check src tests`、`uv run ai-sdlc verify constraints`
