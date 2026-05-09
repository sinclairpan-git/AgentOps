# 功能规格：Runtime Outbox and SDLC Trace Bridge

**功能编号**：`034-runtime-outbox-sdlc-trace-bridge`
**创建日期**：2026-05-09
**状态**：实现中
**输入**：承接 `specs/031-agentops-runtime-governance-foundation/agentops-p0-p2-backlog.md` 中 `AO-P0-10`、`AO-P0-14`。参考：`specs/031-agentops-runtime-governance-foundation/spec.md`、`specs/032-evidence-health-summary-loop/spec.md`、`specs/033-policy-grant-approval-minimum-control/spec.md`。

**范围**：补齐 Runtime / Reporter outbox 重放接收语义，并为 Ai_AutoSDLC 在 `enterprise_managed` 模式下上报的 stage、gate、verification、artifact、violation 事件提供 TraceSpan / Evidence 输入桥接。AgentOps 只接收、校验、去重、降级、投影和审计事实，不执行 Agent、不调度 Runtime、不读取 raw payload、不替代 Ai_AutoSDLC 判断阶段结果。

## 用户场景与测试

### 用户故事 1 - Runtime / Reporter 安全重放 outbox（优先级：P0）

作为 Runtime 或 Reporter 调用方，我希望 outbox 批次重放时同一 `idempotency_key + payload_hash` 被稳定忽略，而较旧 `sequence_no` 不覆盖新事实，以便网络重试、进程重启和重复投递不会污染 Run Detail / Trace Timeline。

**优先级说明**：这是 AO-P0-10 的最小可靠性基础；没有可验证的 outbox receipt，P0 闭环无法区分已送达、重复、乱序和拒绝。

**独立测试**：构造 runtime batch，先送达较新 sequence，再重放重复事件和较旧事件，验证 receipt 计数、item_results、repository 最新事实和 HTTP 202 语义。

**验收场景**：

1. **Given** Runtime 重放完全相同的事件，**When** AgentOps 再次接收，**Then** item result 为 `deduplicated`，事实存储不增加。
2. **Given** Runtime 先送达 `sequence_no=3` 的 run fact，**When** 之后送达同一 run/attempt 的 `sequence_no=2`，**Then** item result 为 `stale_ignored`，最新 run fact 不回退。
3. **Given** outbox batch 带 `outbox_id` 和 `replay_reason`，**When** 接收完成，**Then** receipt 返回 summary-only 的 outbox 状态和 audit id。

### 用户故事 2 - 拒绝和 DLQ 状态可解释（优先级：P0）

作为治理管理员，我希望签名失败、schema 不支持、幂等冲突和缺失父 span 的事件都留下可解释状态，而不是静默丢弃，以便排查 Runtime / Reporter 上报问题且不暴露原始载荷。

**优先级说明**：这是 AO-P0-10 对失败路径的治理要求；拒绝必须可审计，但不能把不可信 payload 提升为事实。

**独立测试**：构造签名失败、schema 不支持、idempotency conflict 和缺父 span 事件，验证 receipt 的 error_code/state/retryable、runtime DLQ/diagnostic 记录和 raw payload 隔离。

**验收场景**：

1. **Given** canonical envelope 缺少签名，**When** Runtime ingestion 接收，**Then** item result 为 `rejected`、`state=signature_failed`，repository 只保存诊断摘要。
2. **Given** 事件 schema version 不受支持，**When** AgentOps 接收，**Then** item result 为 `rejected`、`state=schema_rejected`，不得写入 runtime fact。
3. **Given** trace span 父节点缺失，**When** AgentOps 接收，**Then** item result 为 `dlq`、`retryable=true`，Trace Timeline 保持降级可解释。

### 用户故事 3 - Ai_AutoSDLC trace bridge（优先级：P0）

作为 Ai_AutoSDLC / AgentOps 集成维护者，我希望 `enterprise_managed` 模式下的 stage、gate、verification、artifact、violation 事件能映射为 AgentOps TraceSpan / Evidence 输入，以便 SDLC 流水线运行也进入同一 Run Detail、Trace Timeline 和 EvidenceSummary 口径。

**优先级说明**：这是 AO-P0-14 的最小桥接能力；它让 SDLC 阶段事实进入 AgentOps 管理闭环，但不让 AgentOps 接管 Ai_AutoSDLC 决策。

**独立测试**：通过 runtime ingestion 接收 `sdlc_trace_event.v1`，验证只允许 `enterprise_managed` canonical envelope，stage/gate/verification/artifact/violation 映射为 summary-only TraceSpan，EvidenceSummary 使用这些 span 计算缺失维度。

**验收场景**：

1. **Given** Ai_AutoSDLC 上报 stage/gate/verification/artifact/violation 事件，**When** AgentOps 接收，**Then** repository 写入对应 TraceSpan，span_kind 和 status_code 稳定映射。
2. **Given** `sdlc_trace_event.v1` 未使用 `enterprise_managed` integration mode，**When** AgentOps 接收，**Then** 事件被拒绝为 `SDLC_TRACE_EVENT_INVALID`。
3. **Given** SDLC artifact 事件只携带 `artifact_ref` 和 `payload_hash`，**When** Run Detail / EvidenceSummary 查询，**Then** 只展示引用和摘要，不返回 raw payload。

### 边界情况

- Outbox receipt 成功不等价于 L5；它只证明接收语义和诊断状态，不证明治理激活。
- `stale_ignored` 事件不得覆盖已接收的新事实，但可以被记录为已处理，后续同一重放应 deduplicated。
- 签名失败、schema 拒绝和幂等冲突不得写入 runtime_runs、trace_spans、guardrail_results 或 EvidenceSummary source facts。
- `sdlc_trace_event.v1` 只在 canonical `event_envelope.v1` 且 `integration_mode=enterprise_managed` 时启用。
- AgentOps 不读取 Ai_AutoSDLC artifact 原文；artifact、verification、violation 只进入引用、hash、状态和错误码摘要。

## 需求

### 功能需求

- **FR-001**：系统必须登记 `runtime_outbox_receipt.v1`，返回 batch_id、outbox_id、producer、accepted/deduplicated/stale/rejected/dlq 计数、item_results 和 audit_id。
- **FR-002**：Runtime ingestion 必须在 `idempotency_key + payload_hash` 相同重放时返回 `deduplicated`，不得重复写事实。
- **FR-003**：Runtime ingestion 必须在较旧 sequence 送达时返回 `stale_ignored`，不得覆盖同一 run/attempt、trace/span 或 guardrail result 的较新事实。
- **FR-004**：签名失败、schema 不支持、幂等冲突和 DLQ 事件必须留下 summary-only diagnostic，不保存 raw payload。
- **FR-005**：系统必须登记 `sdlc_trace_event.v1`，支持 stage、gate、verification、artifact、violation 五种 SDLC event type。
- **FR-006**：`sdlc_trace_event.v1` 必须映射为 `trace_span.v1`，并保留 evidence_ref、artifact_ref、violation_code、payload_hash 等 summary-only 引用。
- **FR-007**：SDLC trace bridge 必须只接受 `event_envelope.v1` + `enterprise_managed`，不得把 standalone 或 legacy 事件伪装成托管事实。
- **FR-008**：Run Detail、Trace Timeline、EvidenceSummary 必须能消费 SDLC 映射 span，且不返回 raw payload。

### 关键实体

- **RuntimeOutboxReceiptV1**：Runtime ingestion 对 outbox batch 的接收回执和 item-level 结果。
- **RuntimeOutboxDiagnostic**：拒绝、DLQ、乱序忽略等非成功路径的 summary-only 诊断记录。
- **SdlcTraceEventV1**：Ai_AutoSDLC 上报的阶段、门禁、验证、产物和违规事件摘要。
- **MappedTraceSpanV1**：由 `sdlc_trace_event.v1` 派生出的 AgentOps TraceSpan 事实。

## 成功标准

### 可度量结果

- **SC-001**：AO34 contract tests 覆盖 outbox dedup、stale ignored、signature/schema diagnostic、idempotency conflict 和 SDLC trace bridge。
- **SC-002**：AO31/AO32/AO33 contract tests 继续通过，证明 runtime ingestion、EvidenceSummary 和 Guardrail 投影未回退。
- **SC-003**：`uv run ruff check src tests` 与 `uv run ai-sdlc verify constraints` 无 BLOCKER。
