# 功能规格：P1 Evidence Eval Cost Operations

**功能编号**：`037-p1-evidence-eval-cost-operations`
**创建日期**：2026-05-10
**状态**：冻结
**输入**：承接 `specs/031-agentops-runtime-governance-foundation/agentops-p0-p2-backlog.md` 中 P1-B：`AO-P1-04` Evidence Vault 原文申请、`AO-P1-05` EvalCase 基础闭环、`AO-P1-06` 成本/token/latency 预算、`AO-P1-07` DLQ 运维台、`AO-P1-08` OTLP/OpenInference Exporter、`AO-P1-09` Runtime SLO 运营、`AO-P1-10` Store 回显治理升级、`AO-P1-11` 失败样本沉淀、`AO-P1-12` 基础 scorer 管理。参考：`specs/032-evidence-health-summary-loop/spec.md`、`specs/034-runtime-outbox-sdlc-trace-bridge/spec.md`。

**范围**：本工作项第一批只实现 AgentOps 本体的 summary-only P1-B operation contracts 与后端投影函数；不做 Console 页面、不调用外部 exporter、不读取或返回 Evidence Vault 原文、不让 AgentOps 执行 Runtime 或 Agent 包。

## 用户场景与测试

### 用户故事 1 - Evidence 原文访问进入可审计申请流（优先级：P1）

作为 Ops 审批者，我希望看到 raw evidence 申请、理由、脱敏预览状态和审批范围，以便允许有限原文访问前能保留审计证据。

**独立测试**：提交 raw evidence access operation，验证输出只包含 evidence id、hash/ref、reason、requester、approval scope、redaction preview state 和 audit id，不包含 raw payload。

**验收场景**：

1. **Given** EvidenceSummary 处于 `summary_only`，**When** requester 创建原文访问申请，**Then** 返回 `evidence_access_operation.v1` 且 `raw_payload_access=forbidden`。
2. **Given** redaction preview failed，**When** 创建申请，**Then** operation 标记 `redaction_preview_state=failed` 且 owner notification 为 pending。

### 用户故事 2 - 失败运行可沉淀为 EvalCase 与 scorer 输入（优先级：P1）

作为质量 Owner，我希望从 failed/blocked/degraded run 生成 EvalCase 摘要，以便后续人工复核和 scorer 版本对比有稳定输入。

**独立测试**：从 failed run 生成 `eval_case.v1`，验证 privacy_class、owner_team、expected_behavior、source_run、evidence_summary 和 scorer_status。

**验收场景**：

1. **Given** run 状态为 failed，**When** 创建 EvalCase，**Then** 输出 `status=needs_review`，并引用 run_id 和 evidence_summary。
2. **Given** run 已 succeeded，**When** 创建 EvalCase，**Then** 返回 `EVAL_CASE_SOURCE_NOT_FAILED`，避免把健康运行误入失败样本池。

### 用户故事 3 - Token/成本/延迟预算可汇总（优先级：P1）

作为 Runtime SLO Owner，我希望 AgentOps 从 TraceSpan 汇总 token、cost 和 latency，以便运营面能判断预算压力，但不需要读取 prompt 或 output 原文。

**独立测试**：导入 model/tool spans 后构建 `runtime_budget_summary.v1`，验证 token、cost、latency、span_count、budget_state 和 raw leak 禁止。

**验收场景**：

1. **Given** spans 带 `token_usage`、`cost_estimate`、`start_time/end_time`，**When** 查询预算摘要，**Then** 汇总输入/输出 token、cost 和 p95 latency。
2. **Given** cost 超过预算，**When** 查询预算摘要，**Then** `budget_state=over_budget` 且 recommended_action 为 `review_budget`。

### 用户故事 4 - DLQ、Exporter、Runtime SLO 和 Store 治理有只读操作投影（优先级：P1）

作为 Ops 值班人员，我希望看到 DLQ 积压、重放/丢弃候选、exporter 配置状态、Runtime SLO 和 Store 回显治理建议，以便做人工处置而不是让系统自动写回。

**独立测试**：构建 DLQ operations、exporter plan、runtime SLO summary 和 Store governance projection，验证它们都只返回 summary/ref/hash、只读建议和 audit id。

**验收场景**：

1. **Given** runtime DLQ 有 retryable 与 hard rejected item，**When** 查询 DLQ projection，**Then** 输出 retry/discard candidates 和 error code 统计，不包含原始 event payload。
2. **Given** exporter configured 为 dry-run，**When** 查询 exporter operation，**Then** `external_write_enabled=false` 且 `dispatch_state=not_started`。
3. **Given** health/budget/DLQ 存在风险，**When** 查询 Runtime SLO 与 Store governance projection，**Then** 输出 owner notification/appeal/recommended_action，但不自动 disable、merge、publish 或 replay。

### 边界情况

- raw access approval 只能产生审计 operation，不返回 raw evidence。
- EvalCase 只允许 failed、timeout、blocked、degraded 等非健康状态进入；succeeded 不能进入失败样本池。
- DLQ projection 只能展示 retry/discard 候选，不执行 replay 或 discard。
- Exporter projection 只能描述配置和 dry-run 状态，不对 OTLP/OpenInference 发出网络写入。
- Store governance upgrade 只能提供申诉、Owner 通知和替代版本建议状态，不自动下架或发布。

## 需求

### 功能需求

- **FR-001**：系统必须登记 P1-B contracts：`evidence_access_operation.v1`、`eval_case.v1`、`runtime_budget_summary.v1`、`dlq_operations_projection.v1`、`exporter_operation.v1`、`runtime_slo_summary.v1`、`store_governance_projection.v1`。
- **FR-002**：Evidence access operation 必须保留 requester、reason、approval scope、redaction preview state、raw access state、audit id，并明确 `raw_payload_access=forbidden`。
- **FR-003**：EvalCase 必须绑定 source run、agent/version、privacy_class、owner_team、expected_behavior、evidence_summary 和 scorer_status。
- **FR-004**：Runtime budget summary 必须从 TraceSpan summary 字段汇总 token、cost 和 latency，不读取 input/output 原文。
- **FR-005**：DLQ operations projection 必须按 error_code、retryable、state 统计积压，返回 replay/discard candidates 的 id/hash/ref，不返回 raw event payload。
- **FR-006**：Exporter operation 必须支持 OTLP/OpenInference 配置投影，但本批 external write 必须固定 disabled/dry-run。
- **FR-007**：Runtime SLO summary 必须组合 health、budget、DLQ backlog 与 latency 状态，输出 SLO state 和 recommended_action。
- **FR-008**：Store governance projection 必须支持 appeal_state、owner_notification_state、replacement_suggestion_state 和 summary_state，且不得自动禁用或发布。
- **FR-009**：所有 P1-B projection 必须禁止 raw payload、prompt、credential secret、token secret、device key、download/raw URL。
- **FR-010**：037 必须回归 AO32/AO34/AO35，证明 P1-B 操作面未破坏 P0 Evidence/Health、Outbox 和 Acceptance Gate。

### 关键实体

- **EvidenceAccessOperation**：原文访问申请/审批准备投影，只包含安全摘要和审计字段。
- **EvalCase**：从失败运行沉淀出的评测样本摘要。
- **RuntimeBudgetSummary**：token、cost、latency 的 summary-only 汇总。
- **DLQOperationsProjection**：DLQ 积压与候选动作的只读投影。
- **ExporterOperation**：外部 exporter 配置和 dry-run 状态投影。
- **RuntimeSLOSummary**：运行健康、预算、延迟和 backlog 的 SLO 投影。
- **StoreGovernanceProjection**：Agent Store 可消费的治理升级摘要。

## 成功标准

- **SC-001**：`tests/contract/test_ao37_ct_p1_evidence_eval_cost_operations.py` 覆盖所有新增 contracts 和核心投影。
- **SC-002**：新增 projection 序列化结果不包含 raw payload、prompt、token secret、credential secret、device key 或 raw/download URL。
- **SC-003**：AO32/AO34/AO35 定向回归通过。
- **SC-004**：`uv run ai-sdlc verify constraints` 与 037 close-check 在提交后通过。
