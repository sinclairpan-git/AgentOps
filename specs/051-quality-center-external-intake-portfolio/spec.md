# 功能规格：Quality Center External Intake Portfolio

**功能编号**：`051-quality-center-external-intake-portfolio`  
**创建日期**：2026-05-12  
**状态**：已冻结  
**输入**：承接 `050-quality-center-external-intake-health` 的非目标“跨 agent/version summary”。继续保持 summary-only、只读、no-auto-action 边界；不执行 scorer、不 replay payload、不读取 raw evidence/prompt/diff/terminal、不自动 rollout、不写 Store、不发送通知。

**范围**：在 Quality Center workbench 中新增 `external_intake_portfolio`，跨多个 agent/version scope 汇总 external intake 健康态、缺失必需 intake 的 scope、最近 receipt index 和 scorer coverage。该能力只读取已存储 receipt 和 workbench agent_refs，不新增 HTTP route，不改变 049 scoped summary 和 050 per-agent health 行为。

## 用户场景与测试

### 用户故事 1 - 质量负责人查看 intake portfolio（优先级：P1）

作为 Quality Center 负责人，我希望在一个 workbench 结果中看到跨 agent/version 的 external intake 覆盖情况、receiving/no_receipts/needs_review 分布和最新 receipt 摘要，以便判断外部 scorer 接入是否在组合层面健康。

**独立测试**：构建包含多个 agent/version 的 workbench，其中一个 scope 有 accepted receipts、一个 scope 缺少必需 receipt、一个 scope latest receipt rejected；断言 `external_intake_portfolio.v1` 返回 scope_count、state counts、latest_receipts、required_missing_scopes 和 scorer_coverage，且不新增 scorer execution。

### 用户故事 2 - URI identity 可聚合但不泄露（优先级：P1）

作为安全负责人，我希望 URI-style agent identity 仍可参与 portfolio 聚合和 hash lookup，但 portfolio 不回显原始 URL、secret marker 或 raw 字段。

**独立测试**：使用 URI-style agent 写入 receipt 后构建 portfolio，断言该 scope 可被计数，返回的 agent_id 为 `[redacted]`，并复用 no-raw-leaks 断言。

### 用户故事 3 - portfolio 不替代人工处理和执行（优先级：P1）

作为治理负责人，我希望 portfolio 只汇总人工队列和推荐动作，不自动补跑 scorer、不触发 rollout/template switch、Store write 或通知。

**独立测试**：缺失必需 intake 时，portfolio 只增加 `required_missing_scope_count` 和 required_missing_scopes；所有 automatic action flags 为 false。

## 边界情况

- agent_refs 为空时，portfolio 返回 `portfolio_state=empty`，不制造缺口。
- 同一 scorer 在多个 scope 出现时，scorer coverage 去重计数。
- latest receipt index 最多返回每个 scope 一条最新 receipt metadata，不返回 external_result/raw payload/prompt/diff/terminal/URL/secret。
- portfolio 不创建 execution evidence，不调用 external scorer，不写 Store，不发送通知。

## 需求

### 功能需求

- **FR-001**：系统必须登记 `quality_center_external_intake_portfolio.v1` contract，并将 `external_intake_portfolio` 纳入 `quality_center_workbench.v1`。
- **FR-002**：Quality Center workbench 必须输出 portfolio scope_count、version_scope_count、state counts、receipt_count、accepted_execution_count、manual_review_queue_size、required_missing_scope_count。
- **FR-003**：Portfolio 必须返回 safe `latest_receipts` index，每个 scope 最多一条最新 receipt metadata。
- **FR-004**：Portfolio 必须返回 `required_missing_scopes`，仅列出 `external_intake_required=true` 且当前 `no_receipts` 的 scope。
- **FR-005**：URI-style identity 必须可通过 hash lookup 参与 portfolio，但 response 只回显 safe label 和 hash identity。
- **FR-006**：Portfolio 聚合必须只读，不创建新的 quality scorer execution，不触发 rollout/template switch/store write/notification。

### 关键实体

- **QualityCenterExternalIntakePortfolio**：workbench 顶层组合视图，跨 agent/version 汇总 external intake 健康、coverage、latest receipt 和 required missing scopes。
- **QualityCenterExternalIntakeHealth**：050 已定义的 per-agent 健康摘要，portfolio 以它作为输入。

## 成功标准

- **SC-001**：AO51 contract tests 覆盖 registry、multi-scope portfolio、required missing scopes、URI identity no-raw echo。
- **SC-002**：AO50/AO51 定向回归通过，证明 portfolio 不破坏 per-agent health。
- **SC-003**：`uv run ruff check`、`uv run ruff format --check`、`uv run pytest` 定向套件、AI-SDLC constraints/close-check 通过。
