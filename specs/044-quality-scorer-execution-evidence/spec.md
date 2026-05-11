# 功能规格：Quality Scorer Execution Evidence

**功能编号**：`044-quality-scorer-execution-evidence`
**创建日期**：2026-05-11
**状态**：已冻结
**输入**：承接 043 Quality Center Console UI 的后续能力，新增 summary-only scorer execution evidence，使 Quality Center 能展示可机验的 scorer run 摘要，并继续禁止 raw evidence、prompt、diff、terminal 原文泄露和自动 rollout / Store 写回 / 通知发送。
**参考**：`specs/041-quality-scorer-versioning/spec.md`、`specs/042-quality-center-workbench/spec.md`、`specs/043-quality-center-console-ui/spec.md`

**范围**：

- 覆盖 scorer execution summary contract、API builder、内存 repository 存取、Quality Center 聚合字段和 contract tests。
- 不覆盖真实模型/外部 scorer 执行、自动 rollout、自动下架、自动 Store 写回、自动通知发送、raw evidence/prompt/diff/terminal 读取。

## 用户场景与测试（必填）

### 用户故事 1 - 质量负责人查看 scorer 执行证据（优先级：P1）

作为质量负责人，我希望看到每个候选 scorer 的执行摘要、样本窗口、通过率和证据边界，以便决定是否进入人工 rollout 审批。

**优先级说明**：041 已有 scorer version/comparison，042/043 已有 Quality Center 聚合与 UI；scorer execution evidence 是下一段缺失的可机验证据层，但必须保持人工决策。

**独立测试**：AO44 contract test 创建 EvalCase 与 scorer run summary，验证 schema、状态、聚合和无 raw 泄露。

**验收场景**：

1. **Given** 已存在 agent/version 的 EvalCase summary，**When** 记录 candidate scorer 的 summary-only execution，**Then** 返回 `quality_scorer_execution.v1`，包含 run outcome、sample window、score summary、manual approval guardrail 和 audit id。
2. **Given** Quality Center 请求包含 agent_refs，**When** 已有 scorer execution summary，**Then** agent summary 和 scorer rollout panel 必须显示 execution evidence counts，且自动动作均为 false。

---

### 用户故事 2 - 稀疏或不安全 scorer evidence 进入人工复核（优先级：P1）

作为平台维护者，我希望稀疏样本、不通过状态或潜在敏感字段被降级为人工 review，而不是被当作可自动发布的信号。

**优先级说明**：该能力直接保护 AO41/AO42 的 no-auto-rollout 边界，是 scorer execution 引入后的安全前置条件。

**独立测试**：传入稀疏样本和包含 raw/prompt/url 等 marker 的 labels，验证输出 redaction、`manual_review_required=true` 和 no auto action。

**验收场景**：

1. **Given** scorer execution sample size 低于阈值，**When** 生成 execution summary，**Then** `execution_state=insufficient_evidence` 且 recommended action 为 `collect_more_samples`。
2. **Given** 输入包含 forbidden marker，**When** 输出 scorer execution summary，**Then** 输出不得包含 forbidden key/value，且 audit summary 保持 summary-only。

---

### 边界情况

- `min_eval_cases <= 0` 必须拒绝并返回 `QUALITY_SCORER_EXECUTION_UNAVAILABLE`。
- 没有 matching EvalCase 时必须返回 `insufficient_evidence`，不能伪造通过率。
- failed/blocked scorer outcome 必须进入人工复核，不能触发 lifecycle 或 rollout 自动动作。
- 输出不得包含 raw payload、prompt、diff、terminal output、URL、credential/token/device secret markers。

## 需求（必填）

### 功能需求

- **FR-001**：系统必须注册 `quality_scorer_execution.v1` contract，声明 required fields、状态枚举、错误码和 AO44 contract tests。
- **FR-002**：系统必须提供 summary-only scorer execution builder/API，基于 EvalCase summary 与 scorer version/comparison 信息生成 deterministic summary。
- **FR-003**：系统必须把 scorer execution records 存入 repository，并可按 agent/version/scorer 查询最近记录。
- **FR-004**：Quality Center Workbench 必须聚合 scorer execution evidence，包含 last execution state、pass rate、sample size、manual review flag 和 no-auto-action guardrails。
- **FR-005**：所有 scorer execution 输出必须通过 redaction/sanitization，禁止 raw evidence/prompt/diff/terminal/url/secret marker 泄露。
- **FR-006**：scorer execution evidence 只能产生人工建议，必须显式声明 automatic rollout/store write/notification/lifecycle action 均未执行。

### 关键实体（如涉及数据则必填）

- **QualityScorerExecution**：scorer run 的 summary-only 结果，包含 agent/version、scorer ref、sample window、outcome counts、pass rate、execution state、manual recommendation 和 audit id。
- **ScorerExecutionWindow**：执行证据窗口，包含来源 EvalCase ids、minimum required、sample size 和 input boundary。
- **QualityCenterExecutionSummary**：Quality Center 中每个 agent/scorer 的最新 execution evidence 摘要。

## 成功标准（必填）

### 可度量结果

- **SC-001**：AO44 contract tests 覆盖 contract registry、happy path、insufficient evidence、redaction/no-auto-action 和 Quality Center aggregation。
- **SC-002**：AO40/AO41/AO42/AO44 focused contract tests 全部通过。
- **SC-003**：`uv run ai-sdlc verify constraints` 无 BLOCKER。
