# 开发总结：人工审批与 Grant 处置工作台

**功能编号**：`013-approval-grant-workbench`

## 已完成

- Console snapshot 新增 `approvalWorkbench` 只读数据域。
- Approval Center 新增人工审批与 Grant 工作台，展示审批队列、SLA、补充材料、Grant 影响、审批审计轨迹和处置红线。
- 前端 validator 已补充 `approvalWorkbench` strict schema、旧版 v1 安全补全和危险字段负例。
- AO13 后端契约测试已覆盖数据域、字段、安全红线、状态绑定和空仓库空态。
- AgentOps 云端对抗 Review 脚本已扩展审批 Grant 红线。

## 安全边界

- 不执行批准、拒绝、撤销、生产写操作或 Grant 签发。
- Grant 必须绑定原始审批编号、策略版本、资源范围、授权时限和审计编号。
- 申请人不得作为唯一审批人批准自己的高风险动作。
- 补充材料只展示摘要和审计引用，不展示原文、PR 正文、下载链接或 raw URL。

## 已验证

- `uv run pytest tests/contract/test_ao13_ct_approval_grant_workbench.py -q`
- `uv run pytest tests/unit/test_github_actions_contracts.py -q`
- `uv run pytest tests -q`
- `uv run ruff check src tests`
- `npm test`
- `npm run build`
- `node scripts/agentops-pr-review.mjs --base origin/main --head HEAD`
- `uv run ai-sdlc verify constraints`
- `uv run ai-sdlc program validate`
- `uv run ai-sdlc run --dry-run`

## 待完成

- GitHub PR `@codex review` 与 checks。
