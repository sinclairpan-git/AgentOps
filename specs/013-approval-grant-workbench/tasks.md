# 任务分解：人工审批与 Grant 处置工作台

**功能编号**：`013-approval-grant-workbench`

## Batch 1：规格与契约

### T11 冻结 013 规格

- **状态**：已完成
- **文件**：`spec.md`、`plan.md`、`contracts/approval-grant-workbench-contract.md`
- **验收**：AO13-CT-001 到 AO13-CT-005 明确。

## Batch 2：后端审批工作台视图模型

### T21 扩展 Console snapshot

- **状态**：已完成
- **文件**：`src/agentops/api/console_snapshot.py`
- **验收**：snapshot 包含 `approvalWorkbench`，且只包含审批队列、Grant 影响、审计轨迹和保护规则。

## Batch 3：前端审批中心增强

### T31 新增人工审批与 Grant 工作台

- **状态**：已完成
- **文件**：`ApprovalCenterView.js`、`agentOpsApiClient.js`、`mockAgentOpsData.js`
- **验收**：用户可在审批中心查看审批队列、SLA、补充材料、Grant 影响、审计轨迹和只读红线。

## Batch 4：云端对抗 Review 与验证

### T41 契约与回归测试

- **状态**：已完成
- **文件**：`tests/contract/test_ao13_ct_approval_grant_workbench.py`、`apps/agentops-console/tests/console-contract.test.mjs`、`scripts/agentops-pr-review.mjs`
- **命令**：`uv run pytest tests/contract/test_ao13_ct_approval_grant_workbench.py -q`、`uv run pytest tests -q`、`uv run ruff check src tests`、`npm test`、`npm run build`、`node scripts/agentops-pr-review.mjs --base origin/main --head HEAD`、`uv run ai-sdlc verify constraints`、`uv run ai-sdlc program validate`
