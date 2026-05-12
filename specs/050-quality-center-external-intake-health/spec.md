# 功能规格：Quality Center External Intake Health

**功能编号**：`050-quality-center-external-intake-health`  
**创建日期**：2026-05-11  
**状态**：已冻结  
**输入**：承接 049 已完成的 external scorer intake summary，将外部 scorer intake 健康态接入 Quality Center backend workbench。继续保持 summary-only、只读、no-auto-action 边界；不执行 scorer、不 replay payload、不读取 raw evidence/prompt/diff/terminal、不自动 rollout、不写 Store、不发送通知。

**范围**：扩展 `quality_center_workbench.v1`，在每个 agent summary 中加入 `external_intake_health`，并新增全局 `external_intake_panel`。该能力只读取已存储 external intake receipts，按 agent/version hash scope 汇总 receipt_count、health_state、latest receipt metadata、source trust/intake state counts 和 scorer refs。

## 用户场景与测试

### 用户故事 1 - Quality Center 查看外部 scorer intake 健康（优先级：P1）

作为 Quality Center 运维负责人，我希望在统一 workbench 中看到每个 agent/version 的外部 scorer intake 是否仍在接收、最近 receipt 数量与 accepted execution 数，以便把 scorer rollout 判断和外部输入健康放在同一视图中。

**独立测试**：先写入两条 external intake receipts，再构建 Quality Center workbench，断言 `external_intake_health.health_state=receiving`、receipt/source/state counts 正确、latest intake 指向最新 receipt，并且 workbench 查询前后 execution record 数不变。

### 用户故事 2 - 缺少必需 external intake 时进入人工队列（优先级：P1）

作为治理负责人，我希望当某个 agent/version 被标记为必须有 external intake，但当前没有 receipts 时，Quality Center 只生成人工复核项，而不自动补跑 scorer 或触发通知。

**独立测试**：构建包含 `external_intake_required=true` 的 agent_ref 且无 receipt，断言 `health_state=no_receipts`、`manual_review_required=true`、review queue 出现 `external_intake` 项，且所有 automatic action flags 为 false。

### 用户故事 3 - URI identity 可匹配但不泄露（优先级：P1）

作为安全负责人，我希望 URI-style agent identity 仍可通过 hash lookup 汇总 receipts，但 workbench 不回显原始 URL、secret marker 或 raw 字段。

**独立测试**：使用 URI-style agent id 写入 external intake，再构建 workbench，断言 receipt 可匹配、agent id response 为 `[redacted]`，并复用 no-raw-leaks 断言。

## 边界情况

- 未配置 external intake requirement 且无 receipt 时，健康态为 `no_receipts`，但不默认进入人工队列。
- 配置 `external_intake_required=true` 且无 receipt 时，进入人工队列，推荐动作仅为 `connect_external_scorer`。
- 最近 receipt 非 accepted 时，健康态为 `needs_review`。
- 所有输出必须是 summary-only metadata，不包含 external_result、raw payload、prompt、diff、terminal、URL 或 secret。
- Workbench 聚合不得创建新的 scorer execution、rollout、Store write、notification 或 publish action。

## 需求

### 功能需求

- **FR-001**：系统必须登记 `quality_center_external_intake_health.v1` nested contract，并将 `external_intake_panel` 纳入 `quality_center_workbench.v1`。
- **FR-002**：Quality Center workbench 必须为每个 agent/version 生成 `external_intake_health`，包含 health_state、receipt_count、latest metadata、state/source counts、accepted_execution_count、scorer_refs、manual_review_required 与 recommendation。
- **FR-003**：Workbench 必须生成全局 `external_intake_panel`，汇总 monitored agent 数、receiving/no_receipts/needs_review 数、receipt_count、accepted_execution_count 和 manual_review_queue_size。
- **FR-004**：`external_intake_required=true` 且无 receipt 时，必须生成 `external_intake` manual review item；默认未要求时不得制造额外人工队列。
- **FR-005**：URI-style identity 必须可通过 hash lookup 匹配 receipt，但 response 只回显 safe label/redacted identity。
- **FR-006**：Workbench 聚合必须只读，不创建新的 quality scorer execution，不触发 rollout/template switch/store write/notification。

### 关键实体

- **QualityCenterExternalIntakeHealth**：嵌套健康摘要，包含 external intake receipt 聚合、manual review 信号和 no-auto-action summary。
- **QualityCenterExternalIntakePanel**：workbench 顶层聚合，展示所有 agent summary 的 intake 健康计数。
- **QualityCenterReviewItem**：已有人工队列实体，新增 `review_type=external_intake`。

## 成功标准

- **SC-001**：AO50 contract tests 覆盖 registry、receiving receipts 汇总、required intake absence manual review、URI identity no-raw echo。
- **SC-002**：AO42/AO49/AO50 定向回归通过，证明新增字段不破坏既有 Quality Center 和 external intake summary 行为。
- **SC-003**：`uv run ruff check`、`uv run ruff format --check`、`uv run pytest` 定向套件、AI-SDLC constraints/truth/close-check 通过。
