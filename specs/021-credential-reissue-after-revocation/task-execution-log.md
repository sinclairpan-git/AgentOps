# 执行日志：021 Credential Reissue After Revocation

**功能编号**：`021-credential-reissue-after-revocation`
**执行日期**：2026-05-08
**状态**：本地实现完成，待提交与 PR 评审

## 2026-05-08

- 已确认 adapter 仍为 `materialized/unverified`，普通终端无法证明 `verified_loaded`。
- `uv run ai-sdlc run --dry-run` 已通过。
- 当前分支：`codex/021-credential-reissue-after-revocation`。
- 已完成 credential reissue after revocation 的后端、控制台、契约测试和 OpenAPI 初版实现。

## 阶段记录

| Task | 状态 | 记录 |
| --- | --- | --- |
| T21-01 | 完成 | 新增规格、计划、任务、执行日志和开发摘要。 |
| T21-02 | 完成 | 新增 `agentops_credential_reissue.v1`、HTTP reissue route 和 OpenAPI schema。 |
| T21-03 | 完成 | `Repository` 增加 reissue resolution、失败清理和 replacement token 边界。 |
| T21-04 | 完成 | Console 凭证联调工作台展示 reissued 计数、新 bootstrap id 和新 credential id。 |
| T21-05 | 完成 | 补 AO21 契约测试，覆盖重新签发、替代 id 生成、单 replacement 限制、签名测试、旧 token、新 nonce、幂等和 HTTP route。 |
| T21-06 | 完成 | 统一验证和 AI-SDLC close-check 准备完成；提交后复跑 close-check。 |

## 统一验证命令

- **验证画像**：code-change
- **改动范围**：`src/agentops/api/*`、`src/agentops/storage/repository.py`、`apps/agentops-console/src/*`、`tests/contract/test_ao21_ct_credential_reissue_after_revocation.py`、`specs/001-agentops-trusted-loop/contracts/agentops-api.openapi.yaml`、`specs/021-credential-reissue-after-revocation/*`
- `uv run pytest tests/contract/test_ao21_ct_credential_reissue_after_revocation.py tests/contract/test_ao20_ct_credential_revocation_propagation.py tests/contract/test_ao17_ct_signed_test_event_activation.py -q`
- `uv run ruff check src tests`
- `uv run pytest tests -q`
- `npm test`（工作目录：`apps/agentops-console`）
- `npm run build`（工作目录：`apps/agentops-console`）
- `uv run ai-sdlc verify constraints`
- `uv run ai-sdlc program validate`
- `uv run ai-sdlc program truth sync --execute --yes`
- `uv run ai-sdlc run --dry-run`
- `uv run ai-sdlc workitem close-check --wi specs/021-credential-reissue-after-revocation --json`

## 已完成验证

- `uv run ai-sdlc adapter status`：AGENTS.md 已安装，普通终端无法证明 loaded。
- `uv run ai-sdlc run --dry-run`：Stage close PASS。
- `uv run pytest tests/contract/test_ao21_ct_credential_reissue_after_revocation.py tests/contract/test_ao20_ct_credential_revocation_propagation.py tests/contract/test_ao17_ct_signed_test_event_activation.py -q`：通过。
- `uv run ruff check src tests`：通过。
- `uv run pytest tests/unit/test_github_actions_contracts.py tests/contract/test_ao21_ct_credential_reissue_after_revocation.py -q`：通过。
- `node scripts/agentops-pr-review.mjs --base origin/main --head HEAD`：未发现 P0/P1 阻断问题。
- `uv run pytest tests -q`：通过。
- `npm test`（工作目录：`apps/agentops-console`）：通过。
- `npm run build`（工作目录：`apps/agentops-console`）：通过。
- `uv run ai-sdlc verify constraints`：no BLOCKERs。
- `uv run ai-sdlc program validate`：PASS，保留 `prd_path is empty` 非阻断提示。

## 代码审查

- 自检结论：reissue 由 AgentOps 作为事实源签发替代 credential，Agent Store 和 Console 只显示回显事实。
- 安全边界：source credential 保持 revoked；旧 token 和随机 token 不得借同一 identity 绕过撤销。
- 状态边界：reissued 不构成 `verified_loaded` 或 L5，所有回显保持 `not_asserted`。
- PR #21 Codex review 反馈 1：source credential 已 reissued 后仍可用不同 `new_bootstrap_id` 二次重新签发。已新增 source-level guard，只允许同一 `reissue_id`/`reissued_bootstrap_id` 幂等返回同一个 replacement，并补 `test_ao21_ct_001c_reissue_source_allows_only_one_replacement` 回归测试。
- PR #21 Codex review 反馈 2：A->B->C 多次轮换时，A 的 revoked identity check 只看直接 replacement B，会误拒 C 的最新 token。已新增 replacement chain token resolution，并补 `test_ao21_ct_008_revocation_check_follows_replacement_chain` 回归测试。

## 任务/计划同步状态

- `tasks.md` 同步状态：T21-01 到 T21-06 已完成。
- `plan.md` 同步状态：步骤 1 到步骤 6 已实现。
- `program-manifest.yaml` 同步状态：已新增 `021-credential-reissue-after-revocation`，依赖 `020-credential-revocation-propagation`。
- 关联 branch/worktree disposition 计划：当前交付分支为 `codex/021-credential-reissue-after-revocation`，计划提交后创建 PR；GitHub checks、AgentOps 云端对抗 Review 与 `@codex review` 均通过后合入 `main`，随后删除或归档该分支。

## Git close-out

- **已完成 git 提交**：是，单次语义提交后以当前 Git HEAD 作为本批交付提交。
- **提交哈希**：见当前 Git HEAD。
- 当前分支：`codex/021-credential-reissue-after-revocation`
- 当前批次 branch disposition 状态：待 PR。
