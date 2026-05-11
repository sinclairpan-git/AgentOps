# 开发总结：Quality Scorer External Intake

**编号**：`045-quality-scorer-external-intake`  
**日期**：2026-05-11  
**状态**：已完成

## 已完成

- 新建 045 formal docs，承接 044 未进入本批的真实外部 scorer execution，但范围收敛为 external summary result intake。
- 新增 `quality_scorer_external_intake.v1` runtime contract 与 error registry entries，声明 source trust、signature state、idempotency、payload hash、accepted execution id 和 no-auto-action guardrails。
- Repository 新增 external intake receipt 与 idempotency index，重复 `idempotency_key` 返回 deduplicated receipt 且不重复写 execution evidence。
- API/Core 新增 `ingest_quality_scorer_external_execution`，校验 signed/verified source、signature、EvalCase sample boundary 和 raw/secret marker。
- Accepted external result 复用 `quality_scorer_execution.v1` evidence，并被 Quality Center Workbench 聚合。
- AO45 contract tests 覆盖 contract registry、accepted intake、idempotency、untrusted/signature rejection、sample/raw boundary、Quality Center aggregation。

## 未进入本批

- 真实网络 endpoint 或 webhook server。
- AgentOps 主动执行外部 scorer。
- 自动 rollout、自动下架、自动 Store 写回或通知发送。
- raw evidence、prompt、diff、terminal 原文读取。

## 验证

- `uv run pytest tests/contract/test_ao45_ct_quality_scorer_external_intake.py -q`：通过，6 passed。
- `uv run pytest tests/contract/test_ao40_ct_quality_lifecycle_analytics.py tests/contract/test_ao41_ct_quality_scorer_versioning.py tests/contract/test_ao42_ct_quality_center_workbench.py tests/contract/test_ao44_ct_quality_scorer_execution_evidence.py tests/contract/test_ao45_ct_quality_scorer_external_intake.py -q`：通过，41 passed。
- `uv run ruff check src/agentops/core/runtime_contracts.py src/agentops/core/operations.py src/agentops/api/operations.py src/agentops/storage/repository.py tests/contract/test_ao45_ct_quality_scorer_external_intake.py`：通过。
- `uv run ruff format --check src/agentops/core/runtime_contracts.py src/agentops/core/operations.py src/agentops/api/operations.py src/agentops/storage/repository.py tests/contract/test_ao45_ct_quality_scorer_external_intake.py`：通过。
- `uv run pytest -q`：通过。

## Review Fix

- PR #47 Codex P1：external intake idempotency 现在按 agent/version lookup identity + `idempotency_key` 建作用域，避免不同 agent/version 复用同 key 时误判 deduplicated。
- PR #47 Codex P1：external intake receipt 与 scorer execution evidence 现在在 repository 同一锁内原子写入，重复 key 并发请求只会创建一条 execution evidence。
- Review fix 验证：AO45 8 passed；AO40/AO41/AO42/AO44/AO45 回归 43 passed；完整 pytest 通过；ruff check/format check 通过；AI-SDLC dry-run、truth sync、constraints 均通过。
- PR #47 Codex P1：external intake idempotency 现在保留完整 key，不再用 `_safe_label` 截断，避免 80 字符前缀相同的不同 key 碰撞。
- PR #47 Codex P1：forbidden raw material key matching 现在大小写不敏感，`Raw_Payload` 等变体会被拒绝。
- Review fix 验证：AO45 10 passed；AO40/AO41/AO42/AO44/AO45 回归 45 passed；完整 pytest 通过；ruff check/format check 通过；AI-SDLC constraints 无 BLOCKER。
- PR #47 Codex P1：scoped idempotency key 复用现在会校验 payload hash；同 key 不同 payload 返回 `QUALITY_SCORER_INTAKE_IDEMPOTENCY_CONFLICT` 且不写新 execution evidence。
- Review fix 验证：AO45 + registry 13 passed；AO40/AO41/AO42/AO44/AO45 回归 46 passed；完整 pytest 通过；ruff check/format check 通过；AI-SDLC truth sync 和 constraints 通过。
