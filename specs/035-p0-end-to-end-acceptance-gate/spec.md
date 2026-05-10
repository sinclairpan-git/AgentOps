# 功能规格：P0 End-to-End Acceptance Gate

**功能编号**：`035-p0-end-to-end-acceptance-gate`
**创建日期**：2026-05-09
**状态**：实现中
**输入**：承接 `specs/031-agentops-runtime-governance-foundation/agentops-p0-p2-backlog.md` 中 `AO-P0-13`，串联 031/032/033/034 已落地的 Runtime 上报、Run Detail、Trace Timeline、Evidence/Health Summary、Policy/Grant/Guardrail 和 Agent Store 回显。

**范围**：新增只读 P0 验收门 projection，用同一个 `run_id` 聚合现有事实并输出机器可判定的 `p0_acceptance_gate.v1`。本工作项不新增执行器、不调度 Agent、不读取 raw payload、不替代 Runtime / Ai_AutoSDLC / Agent Store 的事实源职责。

## 用户场景与测试

### 用户故事 1 - P0 治理闭环可一次性验收（优先级：P0）

作为 AgentOps 管理员，我希望能对单个 Runtime run 生成 P0 acceptance gate，确认 Runtime / Ai_AutoSDLC 上报、运行详情、链路、证据、健康、策略授权、guardrail 和 Store 回显全部闭环，以便 P0 不只是分散合同测试通过，而是有端到端验收结果。

**独立测试**：构造完整 run，写入 RuntimeRun、TraceSpan、GuardrailResult、SDLC trace event、PolicyDecision、CapabilityGrant consumption 和 Agent Store metadata，验证 gate 为 `passed` 且所有 required_checks 通过。

**验收场景**：

1. **Given** 同一 run 已完成 runtime facts、trace spans、guardrail 和 SDLC bridge 上报，**When** 构建 P0 acceptance gate，**Then** gate 返回 `gate_status=passed`。
2. **Given** EvidenceSummary 为 L5 且 HealthSummary 推荐 `usable`，**When** Store 回显同一 run，**Then** gate 包含 fresh Store echo 和 Ops deep link。
3. **Given** PolicyDecision 允许受约束动作且 CapabilityGrant 已绑定并消费，**When** gate 检查治理控制，**Then** policy/grant checks 通过且不要求 AgentOps 执行 Runtime。

### 用户故事 2 - P0 缺口必须可解释失败（优先级：P0）

作为集成维护者，我希望验收门在 trace、evidence、Store、outbox、policy/grant 或 SDLC bridge 缺失时明确失败项，而不是把局部成功误报为 P0 完成。

**独立测试**：构造只有 RuntimeRun、没有 trace span 的 run，验证 gate 为 `failed`，并返回 `trace_timeline_complete`、`evidence_summary_l5`、`agent_store_echo_fresh` 等失败 check。

**验收场景**：

1. **Given** run fact 已接收但 trace 未上报，**When** 构建 gate，**Then** trace 和 evidence checks 失败，reason_code 可解释。
2. **Given** outbox receipt 没有 accepted event 或含 diagnostic，**When** 构建 gate，**Then** outbox check 失败。
3. **Given** 返回 projection，**When** 序列化结果，**Then** 不包含 raw payload、prompt、token secret、credential secret 或 device key。

## 需求

- **FR-001**：系统必须登记 `p0_acceptance_gate.v1` contract，包含 gate_id、run_id、agent_id、version、gate_status、required_checks、summary 和 audit_id。
- **FR-002**：acceptance gate 必须只读聚合现有 Runtime、Evidence、Health、Policy、Grant、Guardrail、SDLC bridge 和 Store 回显事实。
- **FR-003**：完整 P0 闭环必须要求 clean outbox receipt、succeeded runtime run、完整 trace timeline、L5 EvidenceSummary、usable HealthSummary、可接受 PolicyDecision、已绑定并审计的 CapabilityGrant、guardrail 投影、SDLC bridge span 和 fresh Store echo。
- **FR-004**：任一 P0 条件缺失时，gate_status 必须为 `failed`，summary 必须列出 failed_check_ids。
- **FR-005**：acceptance gate 不得包含 raw payload、prompt、credential secret、token secret、device key 或 Evidence Vault 原文。

## 成功标准

- **SC-001**：AO35 contract tests 覆盖 contract registry、完整 P0 pass、缺 trace/evidence/store 的 fail。
- **SC-002**：AO31/AO32/AO33/AO34 定向回归继续通过。
- **SC-003**：`uv run ruff check src tests` 与 `uv run ai-sdlc verify constraints` 通过。
