# 任务执行日志：Quality Scorer External Intake

**功能编号**：`045-quality-scorer-external-intake`
**创建日期**：2026-05-11
**状态**：已完成

## 1. 归档规则

- 本文件是 `045-quality-scorer-external-intake` 的固定执行归档文件。
- 后续每完成一批任务，都在**本文件末尾追加一个新的批次章节**。
- 后续每一批任务开始前，必须先完成固定预读（PRD + 宪章 + 当前相关 spec 文档）。
- 后续每一批任务结束后，必须按固定顺序执行：
  - 先完成实现和验证
  - 再把本批结果追加归档到本文件
  - **单次提交（FR-097 / SC-022）**：将本批代码/测试与本次追加的归档段落、`tasks.md` 勾选 **合并为一次** `git commit`，避免「先写提交哈希占位、再改代码、再二次更新归档」的噪音
  - 只有在当前批次已经提交完成后，才能进入下一批任务
- 每个任务记录固定包含以下字段：
  - 任务编号
  - 任务名称
  - 改动范围
  - 改动内容
  - 新增/调整的测试
  - 执行的命令
  - 测试结果
  - 是否符合任务目标

## 2. 批次记录

## Review Fix 2026-05-11-008 | Codex external intake ambiguous lookup

### RF-010 | key-only/partial-scope idempotency lookup 拒绝 ambiguous scope

- 触发来源：PR #47 Codex review P1 inline comment。
- 问题：`quality_scorer_external_receipt_by_idempotency()` 在省略 `agent_id` 和/或 `version` 时，如果同一 `idempotency_key` 存在多个 agent/version scope，会静默返回最新 receipt，可能误关联其他 scope 的 `accepted_execution_id`。
- 改动范围：`src/agentops/storage/repository.py`、`src/agentops/core/runtime_contracts.py`、`tests/contract/test_ao45_ct_quality_scorer_external_intake.py`。
- 改动内容：可选 scope lookup 匹配到多个 lookup identity scope 时抛出 `QUALITY_SCORER_INTAKE_IDEMPOTENCY_CONFLICT`；完整 agent/version scope 查询仍按索引返回目标 receipt；新增 AO45-CT-016 覆盖 key-only 和 agent-only ambiguity。

### 统一验证命令

- `ai-sdlc adapter status`：通过，host verification passed。
- `ai-sdlc run --dry-run`：通过，`close: PASS`。
- `uv run pytest tests/contract/test_ao45_ct_quality_scorer_external_intake.py tests/contract/test_ao31_ct_runtime_governance_foundation.py::test_ao31_ct_001_contract_registry_has_required_runtime_governance_entries tests/unit/test_runtime_contracts.py::test_runtime_contract_registry_covers_p0_contracts -q`：通过，18 passed。
- `uv run pytest tests/contract/test_ao40_ct_quality_lifecycle_analytics.py tests/contract/test_ao41_ct_quality_scorer_versioning.py tests/contract/test_ao42_ct_quality_center_workbench.py tests/contract/test_ao44_ct_quality_scorer_execution_evidence.py tests/contract/test_ao45_ct_quality_scorer_external_intake.py -q`：通过，51 passed。
- `uv run pytest -q`：通过，完整测试集 passed。
- `uv run ruff check src/agentops/storage/repository.py src/agentops/core/runtime_contracts.py tests/contract/test_ao45_ct_quality_scorer_external_intake.py`：通过。
- `uv run ruff format --check src/agentops/storage/repository.py src/agentops/core/runtime_contracts.py tests/contract/test_ao45_ct_quality_scorer_external_intake.py`：通过。
- `python -m ai_sdlc program truth sync --execute --yes`：通过，45/45 mapped，snapshot 已更新。

### 代码审查结论

- 宪章/规格对齐：符合。修复收紧 external intake idempotency replay lookup，不改变 summary-only/no-auto-action 边界。
- 代码质量：符合。仅在 partial scope lookup 命中多个 lookup identity 时拒绝；完整 scope 查询保持 deterministic indexed lookup。
- 测试质量：新增 ambiguity regression，并验证完整 scope 查询仍可返回正确 receipt。
- 结论：通过。

### 任务/计划同步状态

- `tasks.md` 同步状态：045 任务仍为完成；review fix 不新增 scope。
- `plan.md` 同步状态：Phase 2 idempotency lookup semantics 已补齐 ambiguous scope guard。
- 关联 branch/worktree disposition 计划：当前分支保留待 PR review fix 推送。

### 归档后动作

- **已完成 git 提交**：是，本 review fix 将作为当前提交追加。
- **提交哈希**：见当前 Git HEAD。
- 当前批次 branch disposition 状态：待 PR review fix 推送
- 当前批次 worktree disposition 状态：保留
- 是否继续下一批：否，继续 PR 收口

## Review Fix 2026-05-11-007 | Codex external intake threshold error contract

### RF-009 | min_eval_cases invalid 使用 intake-specific error code

- 触发来源：PR #47 Codex review P2 inline comment。
- 问题：`ingest_quality_scorer_external_execution()` 对 `min_eval_cases <= 0` 抛出 `QUALITY_SCORER_EXECUTION_UNAVAILABLE`，但 `quality_scorer_external_intake.v1` 只声明 intake-specific 错误码，严格 contract consumer 会收到未声明错误。
- 改动范围：`src/agentops/core/operations.py`、`src/agentops/core/runtime_contracts.py`、`tests/contract/test_ao45_ct_quality_scorer_external_intake.py`。
- 改动内容：新增并使用 `QUALITY_SCORER_INTAKE_THRESHOLD_INVALID`；contract registry 声明该错误码；新增 AO45-CT-015 验证 invalid threshold 不写 execution evidence 且返回 intake-specific error。

### 统一验证命令

- `ai-sdlc adapter status`：通过，host verification passed。
- `ai-sdlc run --dry-run`：通过，`close: PASS`。
- `uv run pytest tests/contract/test_ao45_ct_quality_scorer_external_intake.py tests/contract/test_ao31_ct_runtime_governance_foundation.py::test_ao31_ct_001_contract_registry_has_required_runtime_governance_entries tests/unit/test_runtime_contracts.py::test_runtime_contract_registry_covers_p0_contracts -q`：通过，17 passed。
- `uv run pytest tests/contract/test_ao40_ct_quality_lifecycle_analytics.py tests/contract/test_ao41_ct_quality_scorer_versioning.py tests/contract/test_ao42_ct_quality_center_workbench.py tests/contract/test_ao44_ct_quality_scorer_execution_evidence.py tests/contract/test_ao45_ct_quality_scorer_external_intake.py -q`：通过，50 passed。
- `uv run pytest -q`：通过，完整测试集 passed。
- `uv run ruff check src/agentops/core/operations.py src/agentops/core/runtime_contracts.py tests/contract/test_ao45_ct_quality_scorer_external_intake.py`：通过。
- `uv run ruff format --check src/agentops/core/operations.py src/agentops/core/runtime_contracts.py tests/contract/test_ao45_ct_quality_scorer_external_intake.py`：通过。
- `python -m ai_sdlc program truth sync --execute --yes`：通过，45/45 mapped，snapshot 已更新。

### 代码审查结论

- 宪章/规格对齐：符合。修复将 documented external intake input failure 归入 045 intake contract，不改变 scorer execution contract。
- 代码质量：符合。错误码、denied scope、contract registry 和 regression test 保持一致。
- 测试质量：新增 invalid min_eval_cases contract regression。
- 结论：通过。

### 任务/计划同步状态

- `tasks.md` 同步状态：045 任务仍为完成；review fix 不新增 scope。
- `plan.md` 同步状态：Phase 2 external intake validation error contract 已补齐。
- 关联 branch/worktree disposition 计划：当前分支保留待 PR review fix 推送。

### 归档后动作

- **已完成 git 提交**：是，本 review fix 将作为当前提交追加。
- **提交哈希**：见当前 Git HEAD。
- 当前批次 branch disposition 状态：待 PR review fix 推送
- 当前批次 worktree disposition 状态：保留
- 是否继续下一批：否，继续 PR 收口

## Review Fix 2026-05-11-006 | Codex external intake sample/hash boundary

### RF-008 | case_results sample boundary 与 execution-shaping idempotency hash

- 触发来源：PR #47 Codex review P1/P2 inline comments。
- 问题 1：external intake 只校验 `source_eval_cases`，但未拒绝 `case_results` 中引用其他 EvalCase 的条目，越界结果会被静默忽略。
- 问题 2：idempotency conflict 比较的 `payload_hash` 只包含 `external_result`，同 key 同结果但更换 scorer/source trust/threshold 等 execution-shaping 字段时会被误判为成功 deduplicated。
- 改动范围：`src/agentops/core/operations.py`、`src/agentops/core/runtime_contracts.py`、`tests/contract/test_ao45_ct_quality_scorer_external_intake.py`。
- 改动内容：新增 `case_results[*].eval_case_id` 必须属于 declared `source_eval_cases` 的 sample-boundary 校验；receipt `payload_hash` 改为覆盖 `external_result`、scorer、source trust、producer、`min_eval_cases`、`pass_threshold`；新增 AO45-CT-009 和 AO45-CT-010。

### 统一验证命令

- `ai-sdlc adapter status`：通过，host verification passed。
- `ai-sdlc run --dry-run`：通过，`close: PASS`。
- `uv run pytest tests/contract/test_ao45_ct_quality_scorer_external_intake.py tests/contract/test_ao31_ct_runtime_governance_foundation.py::test_ao31_ct_001_contract_registry_has_required_runtime_governance_entries tests/unit/test_runtime_contracts.py::test_runtime_contract_registry_covers_p0_contracts -q`：通过，16 passed。
- `uv run pytest tests/contract/test_ao40_ct_quality_lifecycle_analytics.py tests/contract/test_ao41_ct_quality_scorer_versioning.py tests/contract/test_ao42_ct_quality_center_workbench.py tests/contract/test_ao44_ct_quality_scorer_execution_evidence.py tests/contract/test_ao45_ct_quality_scorer_external_intake.py -q`：通过，49 passed。
- `uv run pytest -q`：通过，完整测试集 passed。
- `uv run ruff check src/agentops/core/operations.py src/agentops/core/runtime_contracts.py tests/contract/test_ao45_ct_quality_scorer_external_intake.py`：通过。
- `uv run ruff format --check src/agentops/core/operations.py src/agentops/core/runtime_contracts.py tests/contract/test_ao45_ct_quality_scorer_external_intake.py`：通过。
- `python -m ai_sdlc program truth sync --execute --yes`：通过，45/45 mapped，snapshot 已更新。

### 代码审查结论

- 宪章/规格对齐：符合。修复加强 external summary-only intake 的 sample boundary 与 idempotency replay 语义，不改变 AgentOps 不执行 scorer、不读取 raw material、不自动触发生命周期动作的边界。
- 代码质量：符合。sample validation 在 execution evidence 生成前阻断；payload hash 使用结构化 material，保持 scoped idempotency index 不变。
- 测试质量：新增越界 case result rejection 与 scorer/threshold replay conflict regression。
- 结论：通过。

### 任务/计划同步状态

- `tasks.md` 同步状态：045 任务仍为完成；review fix 不新增 scope。
- `plan.md` 同步状态：Phase 2 intake validation 与 idempotency semantics 已补强。
- 关联 branch/worktree disposition 计划：当前分支保留待 PR review fix 推送。

### 归档后动作

- **已完成 git 提交**：是，本 review fix 将作为当前提交追加。
- **提交哈希**：见当前 Git HEAD。
- 当前批次 branch disposition 状态：待 PR review fix 推送
- 当前批次 worktree disposition 状态：保留
- 是否继续下一批：否，继续 PR 收口

## Review Fix 2026-05-11-005 | Codex checkpoint plan link

### RF-007 | checkpoint linked_plan_uri 对齐 045 work item

- 触发来源：PR #47 Codex review P1 inline comment。
- 问题：`.ai-sdlc/state/checkpoint.yml` 的 `linked_wi_id` 已切到 `045-quality-scorer-external-intake`，但 `linked_plan_uri` 仍指向 `044-quality-scorer-execution-evidence/plan.md`，resume/close 逻辑可能读取 stale plan。
- 改动范围：`.ai-sdlc/state/checkpoint.yml`、`specs/045-quality-scorer-external-intake/development-summary.md`、`specs/045-quality-scorer-external-intake/task-execution-log.md`。
- 改动内容：将 checkpoint `linked_plan_uri` 更新为 `specs/045-quality-scorer-external-intake/plan.md`，并记录本轮 review fix。

### 统一验证命令

- `ai-sdlc adapter status`：通过，host verification passed。
- `ai-sdlc run --dry-run`：通过，`close: PASS`。

### 代码审查结论

- 宪章/规格对齐：符合。修复仅同步 AI-SDLC checkpoint 元数据，不改变 045 功能 scope。
- 代码质量：符合。checkpoint 的 work item 和 plan URI 恢复一致。
- 测试质量：本轮为治理状态元数据修复，无代码路径变更。
- 结论：通过。

### 任务/计划同步状态

- `tasks.md` 同步状态：045 任务仍为完成；review fix 不新增 scope。
- `plan.md` 同步状态：checkpoint linked plan 已指向当前 045 plan。
- 关联 branch/worktree disposition 计划：当前分支保留待 PR review fix 推送。

### 归档后动作

- **已完成 git 提交**：是，本 review fix 将作为当前提交追加。
- **提交哈希**：见当前 Git HEAD。
- 当前批次 branch disposition 状态：待 PR review fix 推送
- 当前批次 worktree disposition 状态：保留
- 是否继续下一批：否，继续 PR 收口

### Batch 2026-05-11-001 | T11-T31

#### 2.1 批次范围

- 覆盖任务：`T11`、`T12`、`T21`、`T22`、`T31`
- 覆盖阶段：Batch 1-3 external scorer intake
- 预读范围：`spec.md`、`plan.md`、`tasks.md`、041/042/044 summary-only scorer chain
- 激活的规则：`FR-086`、`FR-091`、`FR-097`、summary-only/no-auto-action guardrails

#### 2.2 统一验证命令

- **验证画像**：code-change
- **改动范围**：`specs/045-quality-scorer-external-intake/*`, `program-manifest.yaml`, `.ai-sdlc/project/config/project-state.yaml`, `src/agentops/core/runtime_contracts.py`, `src/agentops/core/operations.py`, `src/agentops/api/operations.py`, `src/agentops/storage/repository.py`, `tests/contract/test_ao45_ct_quality_scorer_external_intake.py`
- `R1`（红灯验证，如有 TDD）
  - 命令：不单独保留红灯提交；先新增 AO45 contract tests 后完成实现
  - 结果：AO45 focused tests PASS
- `V1`（定向验证）
  - 命令：`uv run pytest tests/contract/test_ao45_ct_quality_scorer_external_intake.py -q`
  - 结果：6 passed
- `V2`（全量回归）
  - 命令：`uv run pytest tests/contract/test_ao40_ct_quality_lifecycle_analytics.py tests/contract/test_ao41_ct_quality_scorer_versioning.py tests/contract/test_ao42_ct_quality_center_workbench.py tests/contract/test_ao44_ct_quality_scorer_execution_evidence.py tests/contract/test_ao45_ct_quality_scorer_external_intake.py -q`
  - 结果：41 passed
  - 命令：`uv run pytest -q`
  - 结果：通过
- `V3`（格式与 lint）
  - 命令：`uv run ruff check src/agentops/core/runtime_contracts.py src/agentops/core/operations.py src/agentops/api/operations.py src/agentops/storage/repository.py tests/contract/test_ao45_ct_quality_scorer_external_intake.py`
  - 结果：All checks passed
  - 命令：`uv run ruff format --check src/agentops/core/runtime_contracts.py src/agentops/core/operations.py src/agentops/api/operations.py src/agentops/storage/repository.py tests/contract/test_ao45_ct_quality_scorer_external_intake.py`
  - 结果：5 files already formatted
- `V4`（治理）
  - 命令：`python -m ai_sdlc program truth sync --execute --yes`
  - 结果：ready，45/45 mapped
  - 命令：`uv run ai-sdlc verify constraints`
  - 结果：no BLOCKERs

#### 2.3 任务记录

##### T11 | 045 formal scope freeze

- 改动范围：`specs/045-quality-scorer-external-intake/spec.md`、`plan.md`、`tasks.md`
- 改动内容：将 generated scaffold 改写为真实 045 scope：external scorer result intake，AgentOps 不执行 scorer、不读 raw、不自动 rollout/Store/通知。
- 新增/调整的测试：无，文档冻结。
- 执行的命令：`ai-sdlc workitem init ...`
- 测试结果：文档已物化并进入 manifest。
- 是否符合任务目标：是。

##### T12 | quality_scorer_external_intake contract

- 改动范围：`src/agentops/core/runtime_contracts.py`
- 改动内容：新增 `quality_scorer_external_intake.v1`，包含 source trust、signature state、intake state、payload hash、accepted execution id、summary guardrails、AO45 tests 和对应 error registry entries。
- 新增/调整的测试：AO45-CT-001。
- 执行的命令：`uv run pytest tests/contract/test_ao45_ct_quality_scorer_external_intake.py -q`
- 测试结果：6 passed。
- 是否符合任务目标：是。

##### T21-T22 | repository/core/API external intake

- 改动范围：`src/agentops/storage/repository.py`、`src/agentops/core/operations.py`、`src/agentops/api/operations.py`
- 改动内容：新增 intake receipt/idempotency 存储；实现 `ingest_quality_scorer_external_execution`，校验 source trust、signature、idempotency、EvalCase sample boundary 和 raw marker；accepted result 写入既有 `quality_scorer_execution.v1` evidence。
- 新增/调整的测试：AO45-CT-002 至 AO45-CT-005。
- 执行的命令：`uv run pytest tests/contract/test_ao45_ct_quality_scorer_external_intake.py -q`
- 测试结果：6 passed。
- 是否符合任务目标：是。

##### T31 | Quality Center aggregation regression

- 改动范围：`tests/contract/test_ao45_ct_quality_scorer_external_intake.py`
- 改动内容：证明 external intake 写入的 execution evidence 被 `get_quality_center_workbench()` 聚合，且 no-auto-action guardrails 保持。
- 新增/调整的测试：AO45-CT-006。
- 执行的命令：AO40/AO41/AO42/AO44/AO45 定向回归。
- 测试结果：41 passed。
- 是否符合任务目标：是。

#### 2.4 代码审查结论（Mandatory）

- 宪章/规格对齐：符合。045 只接收外部 summary-only scorer result，不执行 scorer，不读取 raw evidence/prompt/diff/terminal，不自动触发生命周期动作。
- 代码质量：实现复用 044 execution evidence 与 Quality Center 聚合路径；新增 idempotency receipt 避免重复写入。
- 测试质量：覆盖 registry、accepted intake、dedup、untrusted/signature rejection、sample/raw boundary、Workbench aggregation。
- 结论：通过。

#### 2.5 任务/计划同步状态（Mandatory）

- `tasks.md` 同步状态：T11/T12/T21/T22/T31 均已标记完成。
- `related_plan`（如存在）同步状态：045 承接 044 未进入本批的真实外部 scorer execution，并保持不执行 scorer 的 AgentOps 边界。
- 关联 branch/worktree disposition 计划：当前实现将收敛到 `codex/045-quality-scorer-external-intake` 并创建 PR；临时 docs 分支不单独保留。
- 说明：后续收口时创建 PR 并触发 Codex review/Compatibility Gate。

#### 2.6 自动决策记录（如有）

无

#### 2.7 批次结论

- 045 external scorer intake 已完成最小闭环：可信外部 result -> receipt -> execution evidence -> Quality Center aggregation。

#### 2.8 归档后动作

- **已完成 git 提交**：是，本批实现、测试和归档将在当前提交中一并提交。
- **提交哈希**：见当前 Git HEAD。
- 当前批次 branch disposition 状态：待提交/PR
- 当前批次 worktree disposition 状态：保留
- 是否继续下一批：否，本工作项进入 close verification。

## Review Fix 2026-05-11-001 | Codex external intake idempotency scope

### RF-001 | 按 agent/version 隔离 external intake idempotency

- 触发来源：PR #47 Codex review P1 inline comment。
- 问题：external intake receipt index 只使用 `idempotency_key`，不同 `agent_id`/`version` 复用同 key 时会误返回第一条 receipt，导致合法 scorer execution 被丢弃并可能跨 agent 误归因。
- 改动范围：`src/agentops/storage/repository.py`、`src/agentops/core/operations.py`、`tests/contract/test_ao45_ct_quality_scorer_external_intake.py`、`src/agentops/core/runtime_contracts.py`。
- 改动内容：repository idempotency scope 改为 agent/version lookup hash + `idempotency_key`；core 查询 dedup 时传入 agent/version；新增 AO45-CT-007 验证同 key 在不同 agent/version 下分别 accepted。

### RF-002 | 原子化 receipt/execution check-and-write

- 触发来源：PR #47 Codex review P1 inline comment。
- 问题：core 先检查 idempotency，再分两步写 execution 和 receipt；并发同 key 请求可能同时通过检查并写入重复 execution evidence。
- 改动范围：`src/agentops/storage/repository.py`、`src/agentops/core/operations.py`、`tests/contract/test_ao45_ct_quality_scorer_external_intake.py`。
- 改动内容：新增 `store_quality_scorer_external_intake()`，在 repository 单个锁内完成 idempotency check、execution 写入、receipt 写入和 index 更新；core 改为构建 execution/receipt 后一次性提交；新增 AO45-CT-008 并发重复 key regression。

### 统一验证命令

- `ai-sdlc adapter status`：通过，host verification passed。
- `ai-sdlc run --dry-run`：checkpoint 指向 044 时暂停，提示需 `ai-sdlc recover --reconcile`；执行 reconcile 后复跑通过，`close: PASS`。
- `uv run pytest tests/contract/test_ao45_ct_quality_scorer_external_intake.py -q`：通过，8 passed。
- `uv run pytest tests/contract/test_ao40_ct_quality_lifecycle_analytics.py tests/contract/test_ao41_ct_quality_scorer_versioning.py tests/contract/test_ao42_ct_quality_center_workbench.py tests/contract/test_ao44_ct_quality_scorer_execution_evidence.py tests/contract/test_ao45_ct_quality_scorer_external_intake.py -q`：通过，43 passed。
- `uv run pytest -q`：通过。
- `uv run ruff check src/agentops/core/operations.py src/agentops/storage/repository.py tests/contract/test_ao45_ct_quality_scorer_external_intake.py`：通过。
- `uv run ruff format --check src/agentops/core/runtime_contracts.py src/agentops/core/operations.py src/agentops/storage/repository.py tests/contract/test_ao45_ct_quality_scorer_external_intake.py`：通过。
- `python -m ai_sdlc program truth sync --execute --yes`：ready，45/45 mapped。
- `uv run ai-sdlc verify constraints`：通过，无 BLOCKER。

### 代码审查结论

- 宪章/规格对齐：符合。修复只增强 external intake 幂等与并发安全，不改变 summary-only/no-auto-action 边界。
- 代码质量：符合。作用域键使用不可逆 lookup hash，原子写入集中在 repository 锁内，core 不再分步持久化。
- 测试质量：新增跨 agent/version 同 key 与并发重复 key regression。
- 结论：通过。

### 任务/计划同步状态

- `tasks.md` 同步状态：045 任务仍为完成；review fix 不新增 scope。
- `plan.md` 同步状态：Phase 2 repository/core/API external intake 的 idempotency 要求已补强。
- 关联 branch/worktree disposition 计划：当前分支保留待 PR review fix 推送。

### 归档后动作

- **已完成 git 提交**：是，本 review fix 将作为当前提交追加。
- **提交哈希**：见当前 Git HEAD。
- 当前批次 branch disposition 状态：待 PR review fix 推送
- 当前批次 worktree disposition 状态：保留
- 是否继续下一批：否，继续 PR 收口

## Review Fix 2026-05-11-004 | Codex external intake optional lookup

### RF-006 | idempotency lookup 支持可选 agent/version scope

- 触发来源：PR #47 Codex review P2 inline comment。
- 问题：`quality_scorer_external_receipt_by_idempotency()` 的 `agent_id`/`version` 参数声明为可选，但省略时会用 `None` 生成 lookup hash，导致 key-only lookup 永远找不到已存 receipt。
- 改动范围：`src/agentops/storage/repository.py`、`src/agentops/core/runtime_contracts.py`、`tests/contract/test_ao45_ct_quality_scorer_external_intake.py`。
- 改动内容：当 agent/version 任一缺省时，repository 按 `idempotency_key` 扫描 receipt，并对提供的可选 scope 做 hash 过滤；新增 AO45-CT-008 验证 key-only、agent-only、version-only lookup。

### 统一验证命令

- `ai-sdlc adapter status`：通过，host verification passed。
- `ai-sdlc run --dry-run`：通过，`close: PASS`。
- `uv run pytest tests/contract/test_ao45_ct_quality_scorer_external_intake.py tests/contract/test_ao31_ct_runtime_governance_foundation.py::test_ao31_ct_001_contract_registry_has_required_runtime_governance_entries tests/unit/test_runtime_contracts.py::test_runtime_contract_registry_covers_p0_contracts -q`：通过，14 passed。
- `uv run pytest tests/contract/test_ao40_ct_quality_lifecycle_analytics.py tests/contract/test_ao41_ct_quality_scorer_versioning.py tests/contract/test_ao42_ct_quality_center_workbench.py tests/contract/test_ao44_ct_quality_scorer_execution_evidence.py tests/contract/test_ao45_ct_quality_scorer_external_intake.py -q`：通过，47 passed。
- `uv run pytest -q`：通过，完整测试集 passed。
- `uv run ruff check src/agentops/core/runtime_contracts.py src/agentops/storage/repository.py tests/contract/test_ao45_ct_quality_scorer_external_intake.py`：通过。
- `uv run ruff format --check src/agentops/core/runtime_contracts.py src/agentops/storage/repository.py tests/contract/test_ao45_ct_quality_scorer_external_intake.py`：通过。
- `python -m ai_sdlc program truth sync --execute --yes`：通过，45/45 mapped，snapshot 已更新。
- `uv run ai-sdlc verify constraints`：通过，无 BLOCKER。

### 代码审查结论

- 宪章/规格对齐：符合。修复只补齐 repository lookup helper 语义，不改变 external intake contract。
- 代码质量：符合。精确 scope 仍走 indexed lookup；缺省 scope 才扫描 receipt，并支持部分 scope filter。
- 测试质量：新增 key-only/agent-only/version-only lookup regression。
- 结论：通过。

### 任务/计划同步状态

- `tasks.md` 同步状态：045 任务仍为完成；review fix 不新增 scope。
- `plan.md` 同步状态：Phase 2 repository idempotency helper 语义已补齐。
- 关联 branch/worktree disposition 计划：当前分支保留待 PR review fix 推送。

### 归档后动作

- **已完成 git 提交**：是，本 review fix 将作为当前提交追加。
- **提交哈希**：见当前 Git HEAD。
- 当前批次 branch disposition 状态：待 PR review fix 推送
- 当前批次 worktree disposition 状态：保留
- 是否继续下一批：否，继续 PR 收口

## Review Fix 2026-05-11-003 | Codex external intake idempotency conflict

### RF-005 | 同 scoped idempotency key 不同 payload 需拒绝

- 触发来源：PR #47 Codex review P1 inline comment。
- 问题：repository dedup 只检查 scoped idempotency key 是否存在，不校验新请求 payload 是否与原请求一致；同 agent/version 下复用 key 但提交不同 `external_result` 会静默返回旧 receipt，导致新的 scorer output 被丢弃。
- 改动范围：`src/agentops/storage/repository.py`、`src/agentops/core/runtime_contracts.py`、`tests/contract/test_ao45_ct_quality_scorer_external_intake.py`。
- 改动内容：repository dedup path 比较 stored/incoming `payload_hash`；不一致时抛出 `QUALITY_SCORER_INTAKE_IDEMPOTENCY_CONFLICT`，不写新 execution evidence；contract registry 增加错误码；新增 AO45-CT-007 regression。

### 统一验证命令

- `ai-sdlc adapter status`：通过，host verification passed。
- `ai-sdlc run --dry-run`：通过，`close: PASS`。
- `uv run pytest tests/contract/test_ao45_ct_quality_scorer_external_intake.py tests/contract/test_ao31_ct_runtime_governance_foundation.py::test_ao31_ct_001_contract_registry_has_required_runtime_governance_entries tests/unit/test_runtime_contracts.py::test_runtime_contract_registry_covers_p0_contracts -q`：通过，13 passed。
- `uv run pytest tests/contract/test_ao40_ct_quality_lifecycle_analytics.py tests/contract/test_ao41_ct_quality_scorer_versioning.py tests/contract/test_ao42_ct_quality_center_workbench.py tests/contract/test_ao44_ct_quality_scorer_execution_evidence.py tests/contract/test_ao45_ct_quality_scorer_external_intake.py -q`：通过，46 passed。
- `uv run pytest -q`：通过。
- `uv run ruff check src/agentops/core/runtime_contracts.py src/agentops/storage/repository.py tests/contract/test_ao45_ct_quality_scorer_external_intake.py`：通过。
- `uv run ruff format --check src/agentops/core/runtime_contracts.py src/agentops/storage/repository.py tests/contract/test_ao45_ct_quality_scorer_external_intake.py`：通过。
- `python -m ai_sdlc program truth sync --execute --yes`：ready，45/45 mapped。
- `uv run ai-sdlc verify constraints`：通过，无 BLOCKER。

### 代码审查结论

- 宪章/规格对齐：符合。修复只加强 external intake idempotency contract，不改变 summary-only/no-auto-action 边界。
- 代码质量：符合。payload hash conflict 在 repository 原子锁内判断，避免 stale execution evidence 静默复用。
- 测试质量：新增同 key 不同 payload conflict regression，并覆盖 registry error code。
- 结论：通过。

### 任务/计划同步状态

- `tasks.md` 同步状态：045 任务仍为完成；review fix 不新增 scope。
- `plan.md` 同步状态：Phase 2 idempotency 要求已补强为 same-key/same-payload dedup。
- 关联 branch/worktree disposition 计划：当前分支保留待 PR review fix 推送。

### 归档后动作

- **已完成 git 提交**：是，本 review fix 将作为当前提交追加。
- **提交哈希**：见当前 Git HEAD。
- 当前批次 branch disposition 状态：待 PR review fix 推送
- 当前批次 worktree disposition 状态：保留
- 是否继续下一批：否，继续 PR 收口

## Review Fix 2026-05-11-002 | Codex external intake key/raw boundary

### RF-003 | 保留完整 idempotency key

- 触发来源：PR #47 Codex review P1 inline comment。
- 问题：external intake 使用 `_safe_label(idempotency_key)` 后会把 key 截断到 80 字符，两个前 80 字符相同但后缀不同的 key 会被误判为重复 intake。
- 改动范围：`src/agentops/core/operations.py`、`tests/contract/test_ao45_ct_quality_scorer_external_intake.py`、`src/agentops/core/runtime_contracts.py`。
- 改动内容：core 改为保留完整 `idempotency_key` 用于 lookup/storage；新增 AO45-CT-005 验证 `k*80 + A/B` 不碰撞。

### RF-004 | raw material key 匹配大小写不敏感

- 触发来源：PR #47 Codex review P1 inline comment。
- 问题：`_contains_forbidden_material()` 对 dict key 进行大小写敏感比较，`Raw_Payload` 等变体可绕过 summary-only 边界。
- 改动范围：`src/agentops/core/operations.py`、`tests/contract/test_ao45_ct_quality_scorer_external_intake.py`、`src/agentops/core/runtime_contracts.py`。
- 改动内容：forbidden key 检测改为 lower-case 比对；新增 AO45-CT-009 验证 case-variant raw key 被拒绝。

### 统一验证命令

- `ai-sdlc adapter status`：通过，host verification passed。
- `ai-sdlc run --dry-run`：通过，`close: PASS`。
- `uv run pytest tests/contract/test_ao45_ct_quality_scorer_external_intake.py -q`：通过，10 passed。
- `uv run pytest tests/contract/test_ao40_ct_quality_lifecycle_analytics.py tests/contract/test_ao41_ct_quality_scorer_versioning.py tests/contract/test_ao42_ct_quality_center_workbench.py tests/contract/test_ao44_ct_quality_scorer_execution_evidence.py tests/contract/test_ao45_ct_quality_scorer_external_intake.py -q`：通过，45 passed。
- `uv run pytest -q`：通过。
- `uv run ruff check src/agentops/core/runtime_contracts.py src/agentops/core/operations.py tests/contract/test_ao45_ct_quality_scorer_external_intake.py`：通过。
- `uv run ruff format --check src/agentops/core/runtime_contracts.py src/agentops/core/operations.py tests/contract/test_ao45_ct_quality_scorer_external_intake.py`：通过。
- `uv run ai-sdlc verify constraints`：通过，无 BLOCKER。

### 代码审查结论

- 宪章/规格对齐：符合。修复只加强 idempotency 精度与 raw boundary，不改变 external summary-only intake 范围。
- 代码质量：符合。idempotency key 不再被展示层 redaction helper 截断；raw key guard 与 text marker guard 均大小写安全。
- 测试质量：新增长 key collision 与 case-variant raw payload regression。
- 结论：通过。

### 任务/计划同步状态

- `tasks.md` 同步状态：045 任务仍为完成；review fix 不新增 scope。
- `plan.md` 同步状态：Phase 2 source/idempotency/raw boundary 要求已补强。
- 关联 branch/worktree disposition 计划：当前分支保留待 PR review fix 推送。

### 归档后动作

- **已完成 git 提交**：是，本 review fix 将作为当前提交追加。
- **提交哈希**：见当前 Git HEAD。
- 当前批次 branch disposition 状态：待 PR review fix 推送
- 当前批次 worktree disposition 状态：保留
- 是否继续下一批：否，继续 PR 收口
