# 任务执行日志：Policy Grant Approval Minimum Control

**功能编号**：`033-policy-grant-approval-minimum-control`
**创建日期**：2026-05-09
**状态**：实现完成，PR 收口中

## 1. 归档规则

- 本文件是 `033-policy-grant-approval-minimum-control` 的固定执行归档文件。
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

### Batch 2026-05-09-001 | T11-T41

#### 2.1 批次范围

- 覆盖任务：`T11`、`T12`、`T21`、`T22`、`T31`、`T32`、`T41`
- 覆盖阶段：AO33 formal baseline、PolicyDecision v1、CapabilityGrant P0 绑定/消费、Guardrail result 接入、收口验证
- 预读范围：
  - `specs/031-agentops-runtime-governance-foundation/agentops-p0-p2-backlog.md`
  - `specs/002-agentops-policy-approval-vault/spec.md`
  - `specs/031-agentops-runtime-governance-foundation/spec.md`
  - `AGENTS.md`
- 激活的规则：AI-SDLC dry-run 入口、Contract-first、AgentOps 不执行 Runtime、不暴露 raw payload、单批归档后提交

#### 2.2 统一验证命令

- `R1`（红灯验证，如有 TDD）
  - 命令：`uv run pytest tests/contract/test_ao33_ct_policy_grant_guardrail_control.py -q`
  - 结果：失败，`evaluate_policy_decision_v1` 尚不存在，红灯生效。
- `V1`（定向验证）
  - 命令：`uv run pytest tests/contract/test_ao33_ct_policy_grant_guardrail_control.py tests/contract/test_ao2_ct_001_policy_check.py tests/contract/test_ao2_ct_002_approval_lifecycle.py tests/contract/test_ao2_ct_003_capability_grant.py tests/unit/test_policy_engine.py tests/unit/test_grant_scope.py tests/contract/test_ao31_ct_runtime_governance_foundation.py tests/contract/test_ao32_ct_evidence_health_summary_loop.py -q`
  - 结果：通过，92 tests。
- `V2`（全量回归）
  - 命令：`uv run ruff check src tests`
  - 结果：通过。
  - 命令：`uv run ruff format --check src/agentops/api/policy.py src/agentops/core/grants.py src/agentops/core/approvals.py src/agentops/core/runtime_contracts.py src/agentops/core/runtime_ingestion.py src/agentops/api/view_models.py src/agentops/storage/repository.py tests/contract/test_ao33_ct_policy_grant_guardrail_control.py`
  - 结果：通过。
  - 说明：`uv run ruff format --check src tests` 暴露既有未触碰的 AO25/AO28/AO29 三个测试文件格式漂移，本批未改动这些文件，采用触达文件格式门禁。
  - 命令：`uv run ai-sdlc verify constraints`
  - 结果：通过，no BLOCKERs。
  - 命令：`uv run ai-sdlc program truth sync --execute --yes`
  - 结果：通过，snapshot hash `5193e0045622f5511f4541d3ea00cfc046cba72532031bdf98384a7aec60a7bd`。

#### 2.3 任务记录

##### T11 | 冻结 AO33 formal docs

- 改动范围：`spec.md`、`plan.md`、`tasks.md`
- 改动内容：将 AI-SDLC 生成占位模板替换为 AO-P0-07/08/09 真实规格，明确 PolicyDecision、Grant、Guardrail result 的 P0 范围和不做项。
- 新增/调整的测试：无代码测试；由 Program Truth Sync 和 constraints 校验覆盖文档真值。
- 执行的命令：`uv run ai-sdlc workitem init ...`、`uv run ai-sdlc program truth sync --execute --yes`
- 测试结果：通过。
- 是否符合任务目标：符合。

##### T12 | 实现 PolicyDecision v1 最小裁决

- 改动范围：`src/agentops/api/policy.py`、`src/agentops/models/policy.py`
- 改动内容：新增 `evaluate_policy_decision_v1`，输出 `policy_decision.v1` required fields；将旧 `conditional_allow` 对 Runtime-facing P0 表达映射为 `allow`，将高风险策略不可用映射为 `policy_unavailable` 且 `ttl=0`。
- 新增/调整的测试：AO33-CT-001、AO33-CT-002。
- 执行的命令：AO33 contract tests。
- 测试结果：通过。
- 是否符合任务目标：符合。

##### T21-T22 | CapabilityGrant P0 绑定、消费和审计

- 改动范围：`src/agentops/core/approvals.py`、`src/agentops/core/grants.py`、`src/agentops/models/grants.py`、`src/agentops/storage/repository.py`
- 改动内容：Grant 签发补齐 version/artifact/installation/device/user/session/run/remaining_uses/offline_allowed/signature/key_id；签发时拒绝替换 approval 已知上下文；消费时校验上下文、TTL、revoked/expired/exhausted，并扣减 `remaining_uses`、写入 consumption audit。
- 新增/调整的测试：AO33-CT-003、AO33-CT-004；AO2 Grant 回归。
- 执行的命令：AO33 + AO2 policy/approval/grant + unit 回归。
- 测试结果：通过。
- 是否符合任务目标：符合。

##### T31-T32 | Guardrail result 接入和 Runtime 投影

- 改动范围：`src/agentops/core/runtime_contracts.py`、`src/agentops/core/runtime_ingestion.py`、`src/agentops/storage/repository.py`、`src/agentops/api/view_models.py`
- 改动内容：Contract Registry 新增 `guardrail_result.v1`；runtime ingestion 接收 `guardrail_result` event；repository 按 run/attempt 保存结果；Run Detail 和 Trace Timeline 输出 summary-only guardrail 摘要和 span 引用。
- 新增/调整的测试：AO33-CT-005、AO33-CT-006；AO31/AO32 回归。
- 执行的命令：AO33 + AO31/AO32 contract tests。
- 测试结果：通过。
- 是否符合任务目标：符合。

##### T41 | 验证、归档和 PR 准备

- 改动范围：`task-execution-log.md`、`program-manifest.yaml`
- 改动内容：记录本批验证和 Program Truth Sync；准备提交与 PR。
- 新增/调整的测试：无。
- 执行的命令：ruff、AI-SDLC constraints、Program Truth Sync、本地对抗 review。
- 测试结果：通过；本地 `node scripts/agentops-pr-review.mjs --base origin/main --head HEAD` 在未提交状态下未看到 diff，提交后 PR 云端对抗 review 仍会按 GitHub Actions 重新执行。
- 是否符合任务目标：符合。

#### 2.4 代码审查结论（Mandatory）

- 宪章/规格对齐：符合 AO-P0-07/08/09；没有让 AgentOps 执行 Runtime，没有暴露 raw payload，没有做 P1 管理台。
- 代码质量：增量集中在 policy/grant/runtime ingestion/projection；旧 `evaluate_policy_check` 与 AO2 行为保留，新增 Runtime-facing v1 包装。
- 测试质量：AO33 7 条 contract tests 覆盖新 P0 路径，并回归 AO2/AO31/AO32。
- 结论：未发现本地 P0/P1 阻断；进入 PR 收口后继续接受云端对抗 review 和 Codex review。

#### 2.5 任务/计划同步状态（Mandatory）

- `tasks.md` 同步状态：T11-T41 已按本批实现完成。
- `related_plan`（如存在）同步状态：无外部 related_plan；related_doc 仅作为参考输入。
- 关联 branch/worktree disposition 计划：当前 `feature/033-policy-grant-approval-minimum-control-docs` 承载 AO33 docs + 实现；误创建的 `codex/033-policy-grant-control` 无独立改动，后续可删除或保留，不影响交付。
- 说明：本批将代码、测试、任务归档、Program Truth 作为一次提交收口。

#### 2.6 自动决策记录（如有）

无

#### 2.7 批次结论

- AO33 PolicyDecision / CapabilityGrant / Guardrail result 最小控制闭环已完成本地实现和定向验证，可提交并提 PR。

#### 2.8 归档后动作

- **验证画像**：code-change
- **已完成 git 提交**：是，本批实现与归档已在当前 close-out 提交中一并提交。
- **提交哈希**：见当前 Git HEAD。
- 当前批次 branch disposition 状态：PR 收口后删除或保留按 GitHub 分支策略处理
- 当前批次 worktree disposition 状态：当前工作区继续用于 PR 收口
- 是否继续下一批：否，本批进入提交、PR、checks 与 review 收口。

## 3. PR Review Fix 2026-05-09-001 | Codex grant binding and policy request hardening

### 3.1 触发来源

- 来源：PR #34 Codex Review
- Reviewed commit：`565c119db2`
- 反馈类型：P1 grant artifact hash 绑定漏洞；P2 low-risk policy decision 缺省 `run_id` 崩溃。

### 3.2 修复内容

#### RF-001 | 占位 artifact hash 不再跨 artifact 复用

- 改动范围：`src/agentops/core/grants.py`
- 改动内容：将 Grant context 匹配从“`sha256:unknown` 完全跳过匹配”改为“仅兼容旧请求未携带 artifact_hash；若 Runtime 请求携带具体 artifact_hash，则必须与 Grant 绑定值一致”。这保留 AO2 旧兼容路径，同时阻断 PR review 指出的跨 artifact 复用。
- 新增/调整测试：`test_ao33_ct_004_grant_consumption_rejects_placeholder_artifact_hash_reuse`
- 是否符合任务目标：符合 AO-P0-08 CapabilityGrant 最小控制闭环，Grant 不得越过审批上下文。

#### RF-002 | PolicyDecision low-risk 请求不再依赖 run_id 必填

- 改动范围：`src/agentops/api/policy.py`
- 改动内容：`evaluate_policy_decision_v1` 的 request_id 生成改为使用 `request.get("run_id", "unknown")`，避免低风险读类请求未携带 run_id 时出现 raw `KeyError`。
- 新增/调整测试：`test_ao33_ct_001_policy_decision_v1_allows_low_risk_without_run_id`
- 是否符合任务目标：符合 AO-P0-07 PolicyDecision 最小可用接口，低风险允许路径必须稳定返回结构化决策。

### 3.3 验证记录

- `uv run ai-sdlc recover --reconcile`：通过，checkpoint 对齐到 AO33 execute。
- `uv run ai-sdlc run --dry-run`：通过安全预演，close gate 剩余 `development-summary.md not found` 已在本次修复补齐。
- `uv run pytest tests/contract/test_ao33_ct_policy_grant_guardrail_control.py tests/contract/test_ao2_ct_003_capability_grant.py tests/unit/test_grant_scope.py tests/contract/test_ao2_ct_001_policy_check.py tests/unit/test_policy_engine.py -q`：通过，27 tests。
- `uv run pytest tests/contract/test_ao33_ct_policy_grant_guardrail_control.py tests/contract/test_ao2_ct_001_policy_check.py tests/contract/test_ao2_ct_002_approval_lifecycle.py tests/contract/test_ao2_ct_003_capability_grant.py tests/unit/test_policy_engine.py tests/unit/test_grant_scope.py tests/contract/test_ao31_ct_runtime_governance_foundation.py tests/contract/test_ao32_ct_evidence_health_summary_loop.py -q`：通过，94 tests。
- `uv run ruff check src/agentops/api/policy.py src/agentops/core/grants.py tests/contract/test_ao33_ct_policy_grant_guardrail_control.py`：通过。
- `uv run ruff check src tests`：通过。
- `uv run ruff format --check src/agentops/api/policy.py src/agentops/core/grants.py tests/contract/test_ao33_ct_policy_grant_guardrail_control.py`：通过。

### 3.4 结论

- Codex review 两条 actionable feedback 已修复并纳入合同测试。
- 本修复将提交、推送，并重新触发 PR #34 `@codex review`。

## 4. PR Review Fix 2026-05-09-002 | AI-SDLC checkpoint metadata alignment

### 4.1 触发来源

- 来源：PR #34 Codex Review
- Reviewed commit：`9fc45f6d5a`
- 反馈类型：P2 checkpoint metadata drift。

### 4.2 修复内容

#### RF-003 | linked_plan_uri 与 033 work item 对齐

- 改动范围：`.ai-sdlc/state/checkpoint.yml`、`.ai-sdlc/state/checkpoint.yml.bak`、`.ai-sdlc/state/resume-pack.yaml`、`.ai-sdlc/work-items/033-policy-grant-approval-minimum-control/resume-pack.yaml`
- 改动内容：在 `linked_wi_id` 已切到 `033-policy-grant-approval-minimum-control` 后，将 `linked_plan_uri` 从 AO32 plan 修正为 AO33 plan，并通过 AI-SDLC recover/reconcile 重新生成 close 阶段 resume-pack 指纹。
- 新增/调整测试：无代码测试；由 AI-SDLC dry-run、constraints、workitem close-check 覆盖治理状态。
- 是否符合任务目标：符合 AI-SDLC 框架约束，避免后续 resume/close-check 读取错误计划。

### 4.3 验证记录

- `uv run ai-sdlc run --dry-run`：进入状态诊断，提示 checkpoint 需 reconcile 到 close。
- `uv run ai-sdlc recover --reconcile`：通过，checkpoint 对齐到 AO33 close。
- `uv run ai-sdlc run --dry-run`：通过，Stage close PASS。
- `uv run ai-sdlc verify constraints`：通过，无 BLOCKER。
- `uv run ai-sdlc program truth sync --execute --yes`：通过，snapshot hash `f54988eaad99d038bef40ccc053882e3930eaba5c8751261d499da1b0a07c070`。
- `uv run ai-sdlc workitem close-check --wi specs/033-policy-grant-approval-minimum-control`：除当前待提交导致的 git closure 外，其余门禁通过；提交后复跑。

### 4.4 结论

- Codex review 最新 P2 metadata drift 已修复，将重新验证、提交、推送并触发 PR #34 `@codex review`。

## 5. PR Review Fix 2026-05-09-003 | Policy summary and partial guardrail projection

### 5.1 触发来源

- 来源：PR #34 Codex Review
- Reviewed commit：`8f8aa0334b`
- 反馈类型：P2 policy summary rendering gap；P2 partial guardrail result projection gap。

### 5.2 修复内容

#### RF-004 | policy_unavailable 可生成用户摘要

- 改动范围：`src/agentops/api/policy.py`
- 改动内容：为 `_policy_plain_language` 增加 `policy_unavailable` 中文文案，避免 degraded-policy 场景在生成 requirement summary 时抛出 `KeyError`。
- 新增/调整测试：`test_policy_unavailable_summary_has_plain_language`
- 是否符合任务目标：符合 AO-P0-07 PolicyDecision 降级路径稳定可解释要求。

#### RF-005 | guardrail summary 保留未解析 span

- 改动范围：`src/agentops/api/view_models.py`
- 改动内容：Run Detail 的 `guardrail_summary` 不再在存在任意 `guardrail_result` 时短路返回结果列表，而是同时追加尚未匹配到 result 的 guardrail span 摘要，避免部分 ingestion 场景隐藏治理证据缺口。
- 新增/调整测试：`test_ao33_ct_006_runtime_views_include_guardrail_summary_without_raw_payload`
- 是否符合任务目标：符合 AO-P0-09 Guardrail result 只读摘要和 evidence gap 可见要求。

### 5.3 验证记录

- `uv run ai-sdlc run --dry-run`：通过，Stage close PASS。
- `uv run pytest tests/contract/test_ao2_ct_005_policy_summary.py tests/contract/test_ao33_ct_policy_grant_guardrail_control.py tests/contract/test_ao31_ct_runtime_governance_foundation.py -q`：通过，61 tests。
- `uv run pytest tests/contract/test_ao2_ct_001_policy_check.py tests/contract/test_ao2_ct_005_policy_summary.py tests/contract/test_ao31_ct_runtime_governance_foundation.py tests/contract/test_ao32_ct_evidence_health_summary_loop.py tests/contract/test_ao33_ct_policy_grant_guardrail_control.py tests/unit/test_policy_engine.py -q`：通过，85 tests。
- `uv run ruff check src/agentops/api/policy.py src/agentops/api/view_models.py tests/contract/test_ao2_ct_005_policy_summary.py tests/contract/test_ao33_ct_policy_grant_guardrail_control.py`：通过。
- `uv run ruff check src tests`：通过。
- `uv run ruff format --check src/agentops/api/policy.py src/agentops/api/view_models.py tests/contract/test_ao2_ct_005_policy_summary.py tests/contract/test_ao33_ct_policy_grant_guardrail_control.py`：通过。
- `uv run ai-sdlc verify constraints`：通过，无 BLOCKER。
- `uv run ai-sdlc program truth sync --execute --yes`：通过，Program Truth snapshot 已刷新。

### 5.4 结论

- Codex review 最新两条 P2 已修复并纳入合同测试，将同步 Program Truth、close-check、提交推送并触发 PR #34 `@codex review`。

## 6. PR Review Fix 2026-05-09-004 | Grant TTL cap and atomic consumption

### 6.1 触发来源

- 来源：PR #34 Codex Review
- Reviewed commit：`96d91c0926`
- 反馈类型：P1 grant valid_until TTL overrun；P1 remaining_uses concurrent consumption race。

### 6.2 修复内容

#### RF-006 | PolicyDecision TTL 不超过 grant valid_until

- 改动范围：`src/agentops/api/policy.py`
- 改动内容：`evaluate_policy_decision_v1` 在命中 capability grant 时使用 `valid_until` 截断 TTL，避免 Runtime 按固定 900 秒缓存而越过 Grant 过期时间。
- 新增/调整测试：`test_ao33_ct_001_policy_decision_v1_caps_grant_ttl_by_valid_until`
- 是否符合任务目标：符合 AO-P0-07/AO-P0-08，授权决策缓存不得扩展 Grant 窗口。

#### RF-007 | Grant remaining_uses 仓储级原子扣减

- 改动范围：`src/agentops/core/grants.py`、`src/agentops/storage/repository.py`
- 改动内容：新增 `consume_grant_atomically`，在 repository lock 内完成读取、校验、扣减和写回；`consume_capability_grant` 只在原子扣减成功后写入 consumption audit。
- 新增/调整测试：`test_ao33_ct_004_grant_consumption_is_atomic_for_remaining_uses`
- 是否符合任务目标：符合 AO-P0-08，`remaining_uses=1` 在并发消费时只能成功一次。

### 6.3 验证记录

- `uv run ai-sdlc run --dry-run`：通过，Stage close PASS。
- `uv run pytest tests/contract/test_ao33_ct_policy_grant_guardrail_control.py tests/contract/test_ao2_ct_001_policy_check.py tests/contract/test_ao2_ct_003_capability_grant.py tests/unit/test_policy_engine.py tests/unit/test_grant_scope.py -q`：通过，29 tests。
- `uv run pytest tests/contract/test_ao33_ct_policy_grant_guardrail_control.py tests/contract/test_ao2_ct_001_policy_check.py tests/contract/test_ao2_ct_002_approval_lifecycle.py tests/contract/test_ao2_ct_003_capability_grant.py tests/contract/test_ao2_ct_005_policy_summary.py tests/unit/test_policy_engine.py tests/unit/test_grant_scope.py tests/contract/test_ao31_ct_runtime_governance_foundation.py tests/contract/test_ao32_ct_evidence_health_summary_loop.py -q`：通过，100 tests。
- `uv run ruff check src/agentops/api/policy.py src/agentops/core/grants.py src/agentops/storage/repository.py tests/contract/test_ao33_ct_policy_grant_guardrail_control.py`：通过。
- `uv run ruff check src tests`：通过。
- `uv run ruff format --check src/agentops/api/policy.py src/agentops/core/grants.py src/agentops/storage/repository.py tests/contract/test_ao33_ct_policy_grant_guardrail_control.py`：通过。
- `uv run ai-sdlc verify constraints`：通过，无 BLOCKER。

### 6.4 结论

- Codex review 最新两条 P1 已修复并纳入合同测试，将同步 Program Truth、close-check、提交推送并触发 PR #34 `@codex review`。
