# 执行日志：020 Credential Revocation Propagation

**功能编号**：`020-credential-revocation-propagation`
**执行日期**：2026-05-07
**状态**：本地实现完成，待提交与 PR 评审

## 2026-05-07

- 已确认 adapter 仍为 `materialized/unverified`，普通终端无法证明 `verified_loaded`。
- `uv run ai-sdlc run --dry-run` 已通过。
- 已创建分支 `codex/020-credential-revocation-propagation`。
- 已完成 credential revocation propagation 的后端、前端、契约测试和 OpenAPI 初版实现。

## 阶段记录

| Task | 状态 | 记录 |
| --- | --- | --- |
| T20-01 | 完成 | 新增规格、计划、任务、执行日志和开发摘要。 |
| T20-02 | 完成 | 新增 `agentops_credential_revocation.v1`、HTTP revoke route 和 OpenAPI schema。 |
| T20-03 | 完成 | `Repository` 增加 revoked 状态写入与已知企业事件阻断。 |
| T20-04 | 完成 | Console 凭证联调工作台展示已撤销、撤销原因、撤销范围和重新签发建议。 |
| T20-05 | 完成 | 补 AO20 契约测试、前端负例测试和 `scripts/agentops-pr-review.mjs` guard。 |
| T20-06 | 完成 | 统一验证和 AI-SDLC close-check 准备完成；提交后复跑 close-check。 |

## 统一验证命令

- **验证画像**：code-change
- **改动范围**：`src/agentops/api/*`、`src/agentops/storage/repository.py`、`apps/agentops-console/src/*`、`apps/agentops-console/tests/console-contract.test.mjs`、`tests/contract/test_ao20_ct_credential_revocation_propagation.py`、`scripts/agentops-pr-review.mjs`、`tests/unit/test_github_actions_contracts.py`、`contracts/frontend/pages/credential-handoff-workbench/*`、`specs/001-agentops-trusted-loop/contracts/agentops-api.openapi.yaml`、`specs/020-credential-revocation-propagation/*`
- `uv run pytest tests/contract/test_ao20_ct_credential_revocation_propagation.py tests/contract/test_ao19_ct_console_credential_handoff_workbench.py tests/contract/test_ao4_ct_console_api.py tests/unit/test_github_actions_contracts.py -q`
- `npm test`（工作目录：`apps/agentops-console`）
- `uv run pytest tests -q`
- `uv run ruff check src tests`
- `npm run build`（工作目录：`apps/agentops-console`）
- `node scripts/agentops-pr-review.mjs --base origin/main --head HEAD`
- `uv run ai-sdlc verify constraints`
- `uv run ai-sdlc program validate`
- `uv run ai-sdlc program truth sync --execute --yes`
- `uv run ai-sdlc recover --reconcile`
- `uv run ai-sdlc run --dry-run`
- `uv run ai-sdlc workitem close-check --wi specs/020-credential-revocation-propagation --json`

## 已完成验证

- `uv run pytest tests/contract/test_ao20_ct_credential_revocation_propagation.py tests/contract/test_ao19_ct_console_credential_handoff_workbench.py tests/contract/test_ao4_ct_console_api.py tests/unit/test_github_actions_contracts.py -q`：通过。
- `npm test`：通过。
- `uv run pytest tests -q`：通过。
- `uv run ruff check src tests`：通过。
- `npm run build`：通过。
- `node scripts/agentops-pr-review.mjs --base origin/main --head HEAD`：未发现 P0/P1 阻断问题。
- `uv run ai-sdlc verify constraints`：no BLOCKERs。
- `uv run ai-sdlc program validate`：PASS，保留 `prd_path is empty` 非阻断提示。
- `uv run ai-sdlc program truth sync --execute --yes`：truth snapshot ready，100/100 mapped。
- `uv run ai-sdlc recover --reconcile`：checkpoint 已对齐到 020 close。
- `uv run ai-sdlc run --dry-run`：Stage close PASS。
- `uv run ai-sdlc workitem close-check --wi specs/020-credential-revocation-propagation --json`：提交前仅剩 `latest batch is not marked as git committed`，提交后复核。

## 代码审查

- 自检结论：revoked 是 AgentOps-owned 事实状态，Agent Store 和 Console 只能消费展示。
- 安全边界：revoked 后 `next_action` 固定为 `reissue_credential`，签名测试事件和已知企业事件不得继续接入。
- 状态边界：revoked 不构成 `verified_loaded` 或 L5，所有回显保持 `not_asserted`。
- 云端对抗 review guard：`scripts/agentops-pr-review.mjs` 已增加 AO20 检查。
- PR #20 Codex review 反馈：`validate_known_revocation_state` 在同一事件同时匹配 active 和 revoked credential 时会遇到第一个 active 后提前返回。已改为扫描所有匹配 credential，只要任一匹配项为 revoked 即拒绝，并补 `test_ao20_ct_003b_revoked_duplicate_identity_is_rejected_after_active_match` 回归测试。

## 任务/计划同步状态

- `tasks.md` 同步状态：T20-01 到 T20-06 已完成。
- `plan.md` 同步状态：步骤 1 到步骤 6 已实现。
- `program-manifest.yaml` 同步状态：已新增 `020-credential-revocation-propagation`，依赖 `019-console-credential-handoff-workbench`。
- 关联 branch/worktree disposition 计划：当前交付分支为 `codex/020-credential-revocation-propagation`，计划提交后创建 PR；GitHub checks、AgentOps 云端对抗 Review 与 `@codex review` 均通过后合入 `main`，随后删除或归档该分支。

## Git close-out

- **已完成 git 提交**：是，单次语义提交后以当前 Git HEAD 作为本批交付提交。
- **提交哈希**：见当前 Git HEAD。
- 当前分支：`codex/020-credential-revocation-propagation`
- 当前批次 branch disposition 状态：待提交和 PR。
