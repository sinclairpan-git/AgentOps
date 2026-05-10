# 功能规格：P1 Approval Policy Grant Operations

**功能编号**：`036-p1-approval-policy-grant-operations`
**创建日期**：2026-05-10
**状态**：草稿
**输入**：承接 `specs/031-agentops-runtime-governance-foundation/agentops-p0-p2-backlog.md` 中 P1-A：`AO-P1-01` Approval Center 完整版、`AO-P1-02` Policy 管理台、`AO-P1-03` Grant 生命周期管理。参考 `002`、`013`、`033` 已落地的 P0 审批、策略、授权和 Console 工作台能力。

**范围**：在 P0 governance baseline 之上新增可运营、可恢复、可审计的审批、策略和授权操作面。AgentOps 仍只管理治理事实、策略版本、审批队列、授权生命周期和审计摘要，不执行 Runtime、不调度 Agent、不替代 IAM/Policy 引擎的事实源职责。

## 用户场景与测试

### 用户故事 1 - Approval Center 可运营审批队列（优先级：P1）

作为 Security/IAM 审批负责人，我希望审批中心支持补充材料、批准、拒绝、过期、撤回、升级和 SLA 状态，以便高风险动作不会停留在只能 approve/reject 的 P0 最小状态。

**独立测试**：构造 pending approval，执行补材料、升级、撤回、过期和审批动作，验证状态机、SLA、审计事件和 self-approval 防线。

**验收场景**：

1. **Given** pending approval 缺少影响范围材料，**When** 审批负责人请求补充材料，**Then** approval 进入 `needs_input`，保留 requester、required_materials、sla_due_at 和 audit_id。
2. **Given** pending approval 超过 SLA，**When** 系统执行到期检查，**Then** approval 进入 `expired` 或 `escalated`，并写入可查询审计事件。
3. **Given** requester 尝试自行 approve，**When** 调用审批动作，**Then** 返回 `APPROVAL_SELF_APPROVAL_DENIED`，不得签发 Grant。

### 用户故事 2 - Policy 管理台可解释版本变更（优先级：P1）

作为策略管理员，我希望看到 policy set 版本、灰度、回滚、risk template、fallback_action 和 deny 优先级解释，以便策略变更可以被审计和回滚，而不是只在 PolicyDecision 结果里出现版本号。

**独立测试**：登记 policy set 版本，发布灰度、回滚到上一版本，验证 active/canary/rolled_back 状态、deny 优先级和 fallback_action 摘要。

**验收场景**：

1. **Given** 新 policy set 版本处于 canary，**When** 管理台读取 policy operations projection，**Then** 返回 rollout_state、traffic_scope、risk_templates、fallback_action 和 audit_id。
2. **Given** policy version 被回滚，**When** 后续 PolicyDecision 需要解释策略状态，**Then** projection 能展示 rollback_from、rollback_reason 和 active_version。
3. **Given** deny 优先级高于 active Grant，**When** 管理台展示策略解释，**Then** 必须明确 `deny_overrides_grant=true`。

### 用户故事 3 - Grant 生命周期可查询、吊销和影响分析（优先级：P1）

作为治理运维人员，我希望查询 Grant 的状态、TTL、remaining_uses、离线授权、消费记录、吊销原因和影响范围，以便在风险出现时可以安全撤销授权并通知受影响 Owner。

**独立测试**：签发 active Grant，消费一次后查询生命周期摘要；执行 revoke/expire，验证后续消费失败、影响范围和 audit trail 完整。

**验收场景**：

1. **Given** active Grant 绑定 agent/version/artifact/device/user/run，**When** 查询 Grant lifecycle，**Then** 返回绑定字段、remaining_uses、expires_at、offline_allowed、consumption_count 和 audit_id。
2. **Given** Grant 被吊销，**When** Runtime 后续尝试消费，**Then** 返回 `GRANT_REVOKED`，projection 展示 revoked_by、revoked_at、revocation_reason。
3. **Given** 离线授权存在，**When** 生成影响分析，**Then** 必须列出 offline_allowed、affected_runs、affected_sessions 和 owner_notification_state。

### 边界情况

- Approval Center 不发送真实通知，只输出 notification intent 和 audit trail。
- Policy 管理台不执行策略评估引擎变更，只登记、解释和投影 policy set 版本状态。
- Grant 生命周期不绕过原 approval binding；任何 revoke/expire/query 都不得扩大 resource_scope。
- 所有 projection 仅返回摘要、状态、引用和 audit_id，不返回 raw payload、token secret、credential secret 或 Evidence Vault 原文。

## 需求

### 功能需求

- **FR-001**：系统必须登记 P1 governance operations contract，覆盖 approval operation、policy set version 和 grant lifecycle projection。
- **FR-002**：Approval Center 必须支持 `pending / needs_input / approved / rejected / expired / withdrawn / escalated` 状态和合法转换。
- **FR-003**：Approval Center 必须记录 supplemental_materials、resume_token_ref、pause_token_ref、sla_due_at、sla_state、actor、reason 和 audit_id。
- **FR-004**：审批动作必须继续拒绝 requester self-approval，除非显式 break_glass 且写入 break_glass audit reason。
- **FR-005**：Policy 管理台必须返回 active/canary/rolled_back policy set 版本、risk templates、fallback_action、deny priority 和 rollback 摘要。
- **FR-006**：Policy operations projection 必须明确 deny 优先级不可被 active Grant 覆盖。
- **FR-007**：Grant 生命周期必须支持查询 active/revoked/expired/exhausted 状态、remaining_uses、consumption history、offline_allowed 和绑定上下文。
- **FR-008**：Grant revoke/expire 必须写入 actor、reason、revoked_at/expired_at、affected_scope 和 audit_id。
- **FR-009**：任一 P1 operation projection 不得包含 raw payload、prompt、credential secret、token secret、device key 或 Evidence Vault 原文。
- **FR-010**：036 必须回归 AO2/AO13/AO33/AO35，证明 P0 策略、审批、Grant 和 acceptance gate 未被 P1 操作面破坏。

### 关键实体

- **ApprovalOperation**：审批动作请求和审计事件，包含 approval_id、operation、actor、reason、materials、sla_state、audit_id。
- **PolicySetVersion**：策略版本摘要，包含 version、state、traffic_scope、risk_templates、fallback_action、rollback metadata。
- **GrantLifecycleView**：授权生命周期投影，包含 grant_id、status、binding、ttl、remaining_uses、consumptions、revocation/expiry、impact summary。

## 成功标准

- **SC-001**：AO36 contract tests 覆盖 approval operation 状态机、policy version projection、grant lifecycle query/revoke/impact。
- **SC-002**：AO2/AO13/AO33/AO35 定向回归继续通过。
- **SC-003**：`uv run ruff check src tests` 与 `uv run ai-sdlc verify constraints` 通过。
