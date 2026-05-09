# 功能规格：Policy Grant Approval Minimum Control

**功能编号**：`033-policy-grant-approval-minimum-control`
**创建日期**：2026-05-09
**状态**：实现完成，PR 收口中
**输入**：承接 `specs/031-agentops-runtime-governance-foundation/agentops-p0-p2-backlog.md` 中 `AO-P0-07`、`AO-P0-08`、`AO-P0-09`。参考：`specs/002-agentops-policy-approval-vault/spec.md`、`specs/031-agentops-runtime-governance-foundation/spec.md`。

**范围**：实现 Runtime-facing 的最小 PolicyDecision API、CapabilityGrant 签发/消费/撤销审计，以及 Guardrail 结果接入。AgentOps 只治理和记录 Runtime / Ai_AutoSDLC 上报事实，不执行 Agent、不加载包、不调度 Tool/Model、不作为统一门户入口。

## 用户场景与测试

### 用户故事 1 - Runtime 获取可执行的最小策略裁决（优先级：P0）

作为 Runtime 调用方，我希望在执行高风险动作前获得结构稳定的 `policy_decision.v1`，以便明确 allow、warn、approval_required、block、policy_unavailable 五种状态和下一步义务。

**优先级说明**：这是 P0 受管治理闭环中阻止高风险动作绕过审批/策略的关键入口。

**独立测试**：构造低风险、高风险需审批、策略不可用和缺少 resource_scope 的 policy request，验证返回字段、枚举、ttl、obligations 和错误码。

**验收场景**：

1. **Given** 高风险动作缺少 `resource_scope`，**When** 请求策略裁决，**Then** 返回 `POLICY_SCOPE_REQUIRED`，不得降级为 allow。
2. **Given** 高风险动作且策略服务不可用，**When** 请求策略裁决，**Then** 返回 `policy_unavailable`、`fallback_action=require_online`、`ttl=0`。
3. **Given** 低风险动作，**When** 请求策略裁决，**Then** 返回 `allow`，并包含 `decision_id`、`reason_code`、`policy_set_version`、`obligations`。

### 用户故事 2 - 已批准审批签发最小 CapabilityGrant（优先级：P0）

作为安全/IAM 负责人，我希望 Grant 严格绑定原审批主体、动作、资源、运行上下文和使用次数，以便 Runtime 只能在授权边界内继续执行。

**优先级说明**：Grant 是 approval_required 后恢复执行的唯一 P0 授权凭据，必须防止 scope 扩大、跨 run 复用和无限使用。

**独立测试**：批准审批后签发 Grant，验证绑定字段、TTL、remaining_uses、签名占位、消费审计；再覆盖 revoked、expired、scope mismatch、uses exhausted。

**验收场景**：

1. **Given** approved approval，**When** 签发 Grant，**Then** Grant 包含 agent/version/artifact/installation/device/user/session/run/skill/resource_scope 绑定。
2. **Given** Grant 被消费，**When** policy request 与绑定完全匹配，**Then** 记录 consumption audit 并扣减 `remaining_uses`。
3. **Given** revoked、expired 或 remaining_uses=0，**When** Runtime 尝试消费，**Then** 返回拒绝错误，不得继续执行。

### 用户故事 3 - Runtime 上报 Guardrail 结果（优先级：P0）

作为治理管理员，我希望 Runtime / Ai_AutoSDLC 上报 guardrail 结果成为受管事实，并在 Run Detail / Trace Timeline 中可见，以便解释 blocked、warn 或 degraded 的原因。

**优先级说明**：Guardrail 是 P0 风险闭环的证据输入；AgentOps 只接收结果，不做复杂规则配置中心。

**独立测试**：通过 runtime ingestion 接收 `guardrail_result.v1`，验证 schema、幂等、run detail 汇总、trace timeline 引用和原文不泄露。

**验收场景**：

1. **Given** Runtime 上报 guardrail result，**When** ingestion 接收，**Then** 结果被持久到 repository 且 `item_results` 为 accepted。
2. **Given** Run Detail 查询，**When** run 包含 guardrail 结果，**Then** 返回 summary-only 的 guardrail 摘要，不返回 raw payload。
3. **Given** TraceSpan 引用 `guardrail_result_refs`，**When** 查询 timeline，**Then** span projection 可展示引用 id 和状态摘要。

### 边界情况

- `policy_unavailable` 不等于 allow；高风险动作必须 require_online/block。
- 未注册或缺少 Store metadata 的 agent 不得获得无限 Grant；本批只签发带边界的短期 Grant。
- Guardrail result 原文只以 `evidence_ref` / `payload_hash` 形式进入摘要，不暴露 raw payload。
- AgentOps 不执行 approval 后的 Runtime resume，只返回可被 Runtime 消费的治理事实。

## 需求

### 功能需求

- **FR-001**：系统必须提供 `evaluate_policy_decision_v1`，返回 `policy_decision.v1` required fields。
- **FR-002**：系统必须支持 `allow / warn / approval_required / block / policy_unavailable` 五种 P0 裁决，不把 `policy_unavailable` 展示为 allow。
- **FR-003**：PolicyDecision 必须返回 `reason_code`、`policy_set_version`、`ttl`、`fallback_action`、`obligations`、`constraints`、`audit_id`。
- **FR-004**：CapabilityGrant 必须绑定 `agent_id`、`version`、`artifact_hash`、`installation_id`、`device_id`、`user_id`、`session_id`、`run_id`、`skill_id`、`resource_scope`。
- **FR-005**：Grant 消费必须校验绑定、TTL、revoked/expired 状态和 `remaining_uses`，并记录 consumption audit。
- **FR-006**：Runtime ingestion 必须支持 `guardrail_result.v1`，校验 schema、签名、幂等和枚举。
- **FR-007**：Run Detail / Trace Timeline 必须展示 summary-only guardrail 摘要和引用，不返回 raw payload。
- **FR-008**：Contract Registry 必须登记 `guardrail_result.v1` 与 AO33 contract tests。

### 关键实体

- **PolicyDecisionV1**：面向 Runtime / Store 的最小策略裁决事实。
- **CapabilityGrantV1**：短期能力授权，绑定审批、主体、资源、运行上下文、TTL 和使用次数。
- **GrantConsumption**：Grant 每次消费的审计事实。
- **GuardrailResultV1**：Runtime / Ai_AutoSDLC 上报的 guardrail 检查结果摘要。

## 成功标准

### 可度量结果

- **SC-001**：AO33 contract tests 覆盖 PolicyDecision、Grant、Guardrail result 三条 P0 路径。
- **SC-002**：既有 AO2/AO31/AO32 contract tests 继续通过，证明本批没有破坏旧策略/审批/运行链路。
- **SC-003**：`uv run ai-sdlc verify constraints` 无 BLOCKER。
