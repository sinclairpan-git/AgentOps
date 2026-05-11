# 开发总结：Quality Scorer Versioning

**编号**：`041-quality-scorer-versioning`  
**日期**：2026-05-10  
**状态**：实现完成，等待提交与 PR 收口

## 已完成

- 新增 AO41 contracts：
  - `quality_scorer_version.v1`
  - `quality_scorer_comparison.v1`
- 新增后端 projection builders 与 API wrappers：
  - Scorer version：scorer/template/version、required evidence、input boundary、rollout state
  - Scorer comparison：baseline/candidate、source EvalCases、alignment delta、safety impact、recommendation
- 新增 AO41 contract tests，覆盖 registry、summary-only boundary、unsafe label redaction、EvalCase 过滤、低样本保护和非法门槛拒绝。

## 未进入本批

- 真实 scorer execution。
- Console UI。
- 自动 rollout、自动禁用、自动 Store 写回。
- 真实通知发送。

## 验证

- `uv run pytest tests/contract/test_ao41_ct_quality_scorer_versioning.py -q`：6 passed。
- `uv run pytest tests/contract/test_ao37_ct_p1_evidence_eval_cost_operations.py tests/contract/test_ao40_ct_quality_lifecycle_analytics.py tests/contract/test_ao41_ct_quality_scorer_versioning.py -q`：34 passed。
- `uv run pytest -q`：通过。
- `uv run ruff check src/agentops/core/operations.py src/agentops/api/operations.py src/agentops/core/runtime_contracts.py tests/contract/test_ao41_ct_quality_scorer_versioning.py`：通过。
- `uv run ruff format --check src/agentops/core/operations.py src/agentops/api/operations.py src/agentops/core/runtime_contracts.py tests/contract/test_ao41_ct_quality_scorer_versioning.py`：通过。
- `python -m ai_sdlc program truth sync --execute --yes`：ready，41/41 mapped。
- `uv run ai-sdlc verify constraints`：no BLOCKERs。
- `python -m ai_sdlc workitem close-check --wi specs/041-quality-scorer-versioning --json`：提交前仅 git closure 阻塞；提交后复跑。

## Review Fix

- PR #43 Codex P1/P2：scorer version 现在保留显式空 `required_evidence=[]`，comparison 会将其视为 evidence regression；显式 0 scorer policy 权重不再被默认值覆盖。
- Review fix 验证：AO41 8 passed；AO37/AO40/AO41 回归 36 passed；完整 pytest 通过；ruff check/format check 通过；AI-SDLC constraints 无 BLOCKER。
- PR #43 Codex P2：`quality_scorer_comparison.v1` 现在在 `needs_human_review` 时也要求 `manual_approval_required=true`，避免 unsafe/ambiguous comparison 跳过人工路由。
- Review fix 验证：AO41 8 passed；AO37/AO40/AO41 回归 36 passed；ruff check/format check 通过；AI-SDLC constraints 无 BLOCKER。
- PR #43 Codex P2：partial scorer policy 现在保留 scorer-specific default weights，candidate 缺失字段不会回落到 baseline/global 20/25。
- Review fix 验证：AO41 9 passed；AO37/AO40/AO41 回归 37 passed；ruff check/format check 通过；AI-SDLC constraints 无 BLOCKER。
