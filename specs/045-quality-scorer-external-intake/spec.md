# 功能规格：Quality Scorer External Intake

**功能编号**：`045-quality-scorer-external-intake`
**创建日期**：2026-05-11
**状态**：已冻结
**输入**：承接 044 未进入本批的真实外部 scorer execution，但 AgentOps 只接收外部受管 scorer 上报的 summary-only execution result；必须校验签名/幂等/source trust/scorer version/sample boundary，不执行 scorer、不读取 raw evidence/prompt/diff/terminal、不自动 rollout、不自动 Store 写回或通知发送。参考：`specs/041-quality-scorer-versioning/spec.md`、`specs/042-quality-center-workbench/spec.md`、`specs/044-quality-scorer-execution-evidence/spec.md`

**范围**：新增外部 scorer execution summary intake。AgentOps 负责校验与归档外部 scorer 的 summary-only 结果，并把可验证执行证据接入现有 Quality Center Workbench。AgentOps 不负责运行 scorer、不访问 raw evidence、不自动切换 scorer、不写 Store、不发通知。

## 用户场景与测试

### 用户故事 1 - 接收可信外部 scorer 执行结果（优先级：P0）

作为 AgentOps 管理员，我希望外部受管 scorer 完成运行后，把 summary-only 结果上报给 AgentOps，以便 Quality Center 能展示真实外部执行证据，而不需要 AgentOps 自己执行 scorer。

**优先级说明**：044 已经具备内部 summary-only execution evidence；045 是进入真实外部 scorer 闭环前的最小可信接入点。

**独立测试**：上报 signed/verified 的 external execution result，断言返回 `quality_scorer_external_intake.v1` receipt，生成 `quality_scorer_execution.v1` execution record，并被 Quality Center 聚合。

**验收场景**：

1. **Given** 已存在同 agent/version 的 EvalCase summary，**When** 外部 scorer 上报 signed execution result，**Then** AgentOps 接收结果、计算 outcome/pass_rate、存储 execution evidence，并保留 no-auto-action guardrails。
2. **Given** 同一 `idempotency_key` 重复上报，**When** 再次 intake，**Then** AgentOps 返回 deduplicated receipt，且不重复写入 execution evidence。

### 用户故事 2 - 拒绝不可信或越界 scorer 输入（优先级：P0）

作为治理负责人，我希望不可信 source trust、缺失签名、越界 EvalCase 或 raw payload 字段被拒绝，以便外部 scorer 接入不会绕过 summary-only 边界。

**优先级说明**：外部接入比内部 projection 风险更高，必须先冻结接入边界。

**独立测试**：unsigned/suspected source、空签名、未知 EvalCase、raw/prompt/terminal 字段输入均不能形成 accepted execution evidence。

**验收场景**：

1. **Given** `source_trust=unsigned`，**When** 上报 external execution result，**Then** AgentOps 返回 `QUALITY_SCORER_INTAKE_UNTRUSTED`，不写入 execution evidence。
2. **Given** result 引用不属于该 agent/version 的 EvalCase，**When** 上报，**Then** AgentOps 返回 `QUALITY_SCORER_INTAKE_SAMPLE_INVALID`。
3. **Given** payload 中出现 raw/prompt/diff/terminal 或 URL/secret marker，**When** 上报，**Then** AgentOps 拒绝或 redaction 后不泄露原文。

## 边界情况

- 外部 scorer result 只能引用本地已存在且归属同 agent/version 的 EvalCase summary。
- `source_trust` 只接受 `signed` 或 `verified`；签名字段必须非空且不含敏感 marker。
- `idempotency_key` 必须稳定；重复 key 不得生成新的 execution record。
- `sample_size` 低于最小阈值时可以接收，但 execution state 必须保持 `insufficient_evidence` 且进入人工复核。
- outcome 只接受 `passed / warning / failed / blocked`；未知 outcome 归为 `blocked`。
- 所有输出必须继续满足 summary-only：不输出 raw evidence、prompt、diff、terminal、URL、secret。

## 需求

### 功能需求

- **FR-001**：系统必须注册 `quality_scorer_external_intake.v1` contract，声明 required fields、状态枚举、错误码和 AO45 contract tests。
- **FR-002**：系统必须提供外部 scorer execution intake API/core wrapper，校验 `source_trust`、signature、idempotency、scorer id/version、EvalCase sample boundary。
- **FR-003**：系统必须把 accepted external result 转换为现有 `quality_scorer_execution.v1` summary evidence，并复用 Quality Center Workbench 聚合路径。
- **FR-004**：系统必须对重复 `idempotency_key` 返回 deduplicated receipt，且不得重复写 execution record。
- **FR-005**：系统必须拒绝不可信 source、缺签名、未知 EvalCase 或 raw/secret marker 输入。
- **FR-006**：系统必须保留 no-auto-action guardrails：不自动 rollout、不自动 template switch、不自动 Store 写回、不发送通知。

### 关键实体

- **QualityScorerExternalIntake**：外部 scorer result 接收收据，包含 intake state、source trust、signature state、payload hash、idempotency key、accepted execution id 和 summary guardrails。
- **QualityScorerExecution**：044 已有 summary-only execution evidence；045 accepted intake 必须写入该实体以复用 Quality Center。
- **EvalCase Sample Boundary**：用于校验外部 result 引用的 EvalCase 是否存在且归属目标 agent/version。

## 成功标准

### 可度量结果

- **SC-001**：AO45 contract tests 覆盖 contract registry、accepted intake、idempotent dedup、untrusted rejection、sample boundary rejection、Quality Center aggregation。
- **SC-002**：所有 accepted output 均通过 no-raw/no-secret 断言。
- **SC-003**：AO40/AO41/AO42/AO44/AO45 定向回归通过。
- **SC-004**：`uv run ruff check`、`uv run ruff format --check` 和 `uv run ai-sdlc verify constraints` 无 BLOCKER。
