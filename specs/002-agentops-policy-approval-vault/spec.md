# 功能规格：AgentOps 阶段 2 Policy Check、Approval Grant 与 Evidence Vault 摘要

**功能编号**：`002-agentops-policy-approval-vault`  
**创建日期**：2026-05-05  
**状态**：对抗评审前草案  
**工作项分类**：`new_requirement`  
**继承 baseline_id**：`agent-platform-baseline-2026-05-v1.4.2`  
**上游依赖**：`001-agentops-trusted-loop` 已完成可信事件、L5 Gate、Evidence Summary、PolicyDecision 阶段 1 降级口径。  
**基线来源**：

- `/Users/sinclairpan/project/AI-Native底座开发文档/AgentOps_项目_PRD.md`
- `/Users/sinclairpan/project/AI-Native底座开发文档/Agent_Store_AgentOps_AiSDLC_应用底座顶层规划_PRD.md`
- `specs/001-agentops-trusted-loop/plan.md`

## 1. 目标与边界

### 1.1 项目目标

本工作项建设 AgentOps 阶段 2 的运行治理闭环：在阶段 1 已能证明“运行事实可信”的基础上，新增强 Policy Check、Approval Center、Capability Grant 生命周期和 Evidence Vault 摘要访问控制。

阶段 2 完成后，平台必须能够证明：

1. 高风险 Agent/Skill 动作在执行前获得确定的 `PolicyDecision`，未知或不可用状态不得显示为 allow。
2. 需要审批的动作能创建 Approval，记录审批人、原因、SLA、通知、补充材料、过期和拒绝语义。
3. 只有已批准且未过期/未撤销的 Approval 才能签发短期 Capability Grant。
4. Grant 能被 Policy Check 消费、审计、撤销和过期，过期/撤销后不得继续放行动作。
5. Evidence Vault 默认只返回脱敏摘要；原文访问必须经过审批、审计和限时授权。
6. Agent Store 和 CLI 能收到可解释的治理摘要：`required_by`、`source`、`issuer`、`policy_owner`、`policy_version`、`can_ignore`、`affected_actions`。

### 1.2 本期范围

- RuntimePolicy v1、PolicyCheckRequest、PolicyDecision v2、PolicyRequirement Summary 契约。
- `contracts/stage2-contracts.schema.yaml` 机器可读契约，冻结 PolicyCheckRequest、PolicyDecision v2、Approval、CapabilityGrant、EvidenceVaultSummary、RawAccess、PolicyRequirementSummary、SloSnapshot、Stage2ViewModel 的 required fields、枚举和错误响应。
- Policy Check 裁决优先级：`global_deny > iam_or_security_deny > project_scope_deny > agent_or_version_disabled > policy_block > approval_required > warn > conditional_allow > allow`。
- 高风险动作、resource_scope、enforcement_mode、fallback_action、policy_version 和 audit 字段。
- ApprovalRequest、ApprovalDecision、Approval Center 状态机：pending、approved、rejected、expired、revoked、needs_more_info、escalated。
- CapabilityGrant 签发、消费、撤销、过期、scope 匹配和 policy_version 绑定。
- EvidenceVaultSummary、RawAccessRequest、RawAccessGrant 的摘要访问、审批、TTL 和脱敏失败降级。
- SLO 与降级：Policy Check P95 <= 500ms、告警阈值 P95 > 800ms 或错误率 > 1%；Approval 通知 1 分钟内送达；Evidence Query P95 <= 2s。
- Approval Center、Policy Center、Evidence Explorer、Risk Triage 的阶段 2 view model 状态语义。
- AO2-CT-001 到 AO2-CT-006 的可执行 contract test。

### 1.3 本期不做

- 不自建统一 IAM；只消费 IAM/RBAC/ABAC 结果或测试替身。
- 不做生产 HTTP server、PostgreSQL 迁移或真实消息队列；本期继续提供可执行内核和契约测试层。
- 不做完整前端页面像素实现；只冻结页面模型、状态、动作、权限失败和 Store/CLI 可消费字段。
- 不改变 Ai_AutoSDLC 本地命令；只定义 Policy Check / Grant / Evidence Vault 的接入契约。
- 不实现完整质量评分引擎和生命周期下架建议。
- 不向任何无权限路径返回未脱敏原文。

## 2. 用户场景与测试

### 用户故事 1 - 高风险动作执行前获得强 Policy Check（优先级：P0）

作为 SDK/Wrapper 调用方，我希望在执行高风险 Skill 前请求 AgentOps Policy Check，以便系统能 block、要求审批、给出 warn/conditional_allow 或签发可审计 Grant。

**优先级说明**：阶段 2 的核心价值是把阶段 1 的“策略未知降级”推进为可执行治理；没有强 Policy Check，就没有审批和 Grant 闭环。

**独立测试**：构造 deploy/network/config_change 三类高风险动作，覆盖 allow、approval_required、block、service_unavailable 降级和缺 resource_scope 错误码。

**验收场景**：

1. **Given** 高风险动作缺少 resource_scope，**When** 调用 Policy Check，**Then** 返回 `POLICY_SCOPE_REQUIRED`，不得签发 Grant。
2. **Given** Policy Service 不可用且动作为高风险，**When** 调用 Policy Check，**Then** 返回 `block` + `fallback_action=require_online`。
3. **Given** 已存在 active Grant 且 scope 匹配，**When** 调用 Policy Check，**Then** 返回 `conditional_allow`，包含 grant_id、audit_id 和 valid_until。

---

### 用户故事 2 - 审批人处理高风险 Approval（优先级：P0）

作为安全/IAM 审批人，我希望在 Approval Center 看到审批原因、影响动作、申请人、补充材料、SLA 和审计 ID，以便批准、拒绝、要求补充材料或升级。

**优先级说明**：Grant 必须来自可审计 Approval；审批状态不完整会直接破坏高风险动作的治理证明。

**独立测试**：创建 ApprovalRequest，分别执行 approve、reject、request_more_info、expire/escalate，验证状态、审计字段和通知 SLA。

**验收场景**：

1. **Given** Policy Check 返回 approval_required，**When** 创建 ApprovalRequest，**Then** 记录 requester、approver_scope、reason、affected_actions、sla_due_at、audit_id。
2. **Given** Approval 被批准，**When** 签发 Grant，**Then** Grant 继承 approval_id、resource_scope、policy_version、expires_at。
3. **Given** Approval 超过 SLA 未处理，**When** 运行审批状态计算，**Then** 状态进入 escalated 或 expired，并生成 reminder/escalation action。

---

### 用户故事 3 - 安全/IAM 撤销或过期 Grant（优先级：P0）

作为安全/IAM 负责人，我希望可以撤销 Grant，并让后续 Policy Check 立刻失去授权，以便应对凭证泄露、审批误判或风险升级。

**优先级说明**：Grant 是运行时授权事实源；撤销不生效会造成越权执行。

**独立测试**：签发 active Grant 后分别消费、撤销、过期和 scope mismatch，验证 Policy Check 的返回状态和错误码。

**验收场景**：

1. **Given** active Grant 未过期且 scope 匹配，**When** 消费 Grant，**Then** 返回 allowed_usage 并记录 consumed_at/audit_id。
2. **Given** Grant 已 revoked，**When** 再次 Policy Check，**Then** 返回 `block` 或 `approval_required`，不得 conditional_allow。
3. **Given** Grant scope 与请求资源不匹配，**When** Policy Check 消费，**Then** 返回 `GRANT_SCOPE_MISMATCH`。

---

### 用户故事 4 - Evidence Vault 原文访问受审批和限时控制（优先级：P0）

作为 AgentOps 管理员，我希望默认只看脱敏摘要，并在需要原文时通过 Evidence Vault 申请审批，以便满足审计、隐私和最小权限原则。

**优先级说明**：PRD 明确原文访问必须审批、审计和限时；任何默认泄露原文都会阻断阶段 2。

**独立测试**：使用 summary_only、pending、approved、expired、redaction_failed 五类 Evidence Vault 状态，验证摘要、原文访问拒绝、限时授权和脱敏失败降级。

**验收场景**：

1. **Given** 用户无 raw grant，**When** 请求 Evidence Vault Summary，**Then** 只返回 redacted_summary、payload_hash、raw_access_state，不返回 raw_payload。
2. **Given** RawAccessGrant 已批准且未过期，**When** 请求 raw access，**Then** 返回限时 access_state、audit_id 和 expires_at，不在摘要接口返回原文。
3. **Given** redaction_failed，**When** 请求摘要或原文，**Then** 只返回 hash/告警状态，禁止导出原文。

---

### 用户故事 5 - Store/CLI 能解释治理要求（优先级：P1）

作为 Agent Store 或 CLI 消费方，我希望拿到可解释的 PolicyRequirement Summary，以便向用户说明是谁要求接入、哪些动作受影响、能否忽略以及下一步是什么。

**优先级说明**：治理如果只返回机器枚举，会让用户无法理解为什么被阻断或需要审批。

**独立测试**：生成 policy requirement summary，验证 required_by、source、issuer、policy_owner、policy_version、can_ignore、affected_actions、deep links 必填。

**验收场景**：

1. **Given** Policy Check 返回 approval_required，**When** Store/CLI 查询摘要，**Then** 返回白话说明、影响范围、审批 deep link 和 can_ignore=false。
2. **Given** warn 类型策略，**When** Store/CLI 查询摘要，**Then** 返回 can_ignore=true、secondary_action 和 audit_id。

---

### 用户故事 6 - 管理员看到阶段 2 SLO 与降级状态（优先级：P1）

作为 AgentOps 管理员，我希望看到 Policy Check、Approval Service、Evidence Query 的健康状态、SLO、降级动作和复盘要求，以便快速处理风险和积压。

**优先级说明**：阶段 2 开始 Policy Check 纳入强 SLO，必须能解释超时、错误率和降级。

**独立测试**：构造健康、告警、降级三类 SLO 快照，验证 Risk Triage / Policy Center / Approval Center / Evidence Explorer view model。

**验收场景**：

1. **Given** Policy Check P95 > 800ms，**When** 构建管理员视图，**Then** 展示 degraded、require_online/block 降级动作和 incident_review_required。
2. **Given** Approval 通知超过 1 分钟未送达，**When** 构建 Approval Center，**Then** 展示 overdue/escalate 主动作。

## 3. 边界情况

- 未注册 Skill 不签发正式 Grant，只能返回 suspected/discovered/notified 或 approval_required 降级说明。
- 统一 IAM 返回 deny 时优先级高于 AgentOps allow。
- 多策略冲突时 deny/block 优先于 approval_required，approval_required 优先于 warn/conditional_allow/allow。
- 缺 resource_scope、policy_version、requester、approver_scope、reason 的高风险请求必须拒绝。
- Approval requester 不得作为唯一 approver 批准自己的高风险动作。
- Approval 已 rejected/expired/revoked 时不得签发 Grant。
- Grant 已 expired/revoked 或 scope mismatch 时不得继续 conditional_allow。
- Policy Service 不可用时，高风险动作必须 require_online/block，低风险可 warn/allow 但要标记 policy_state_known=false。
- Evidence Vault 脱敏失败时不得展示或导出原文，只保留 hash、告警和补救动作。
- Evidence raw access grant 不得通过 Store Summary 泄露给无权限用户。
- SLO 快照缺失时不得显示 healthy，必须展示 unknown/degraded 和 request_id。

## 4. 功能需求

- **FR-001**：系统必须提供 PolicyCheckRequest v1，覆盖 action、risk_level、resource_scope、agent_id、agent_version、skill_id、requester、session_id、run_id、policy_version、enforcement_mode、grant_id。
- **FR-002**：系统必须提供 PolicyDecision v2，覆盖 decision、fallback_action、policy_state_known、decision_reason、required_approval_id、grant_id、policy_version、audit_id、valid_until、denied_scope。
- **FR-003**：系统必须按裁决优先级合成 IAM、Security、Project Scope、Agent/Version、RuntimePolicy 和 Grant 状态。
- **FR-003a**：即使请求携带 active Grant，只要存在 global_deny、iam_or_security_deny、project_scope_deny、agent_or_version_disabled 或 policy_block，系统仍必须返回更高优先级 deny/block，不得 conditional_allow。
- **FR-004**：高风险动作缺 resource_scope 必须返回 `POLICY_SCOPE_REQUIRED`。
- **FR-005**：Policy Service 不可用时，高风险动作必须返回 `block` + `require_online`，并标记 degraded。
- **FR-006**：已存在 active Grant 且 scope 匹配时，Policy Check 可返回 `conditional_allow`，并记录 grant 消费审计。
- **FR-007**：系统必须提供 RuntimePolicy v1，覆盖 policy_id、skill_id、risk_override、fallback_action、approval_policy、grant_ttl_seconds、enforcement_mode、owner、version、status。
- **FR-008**：系统必须提供 ApprovalRequest API，创建 approval_required 状态并记录 requester、approver_scope、reason、affected_actions、supplemental_materials、sla_due_at、audit_id。
- **FR-009**：系统必须提供 ApprovalDecision API，支持 approve、reject、request_more_info、revoke、expire、escalate。
- **FR-010**：Approval 被批准后必须可以签发 CapabilityGrant；未 approved 的 Approval 不得签发 Grant。
- **FR-010a**：CapabilityGrant 必须绑定 Approval 原始 policy_check_id、action、agent_id、skill_id、resource_scope、policy_version、requester，签发时不得扩大 scope 或替换动作/主体。
- **FR-011**：系统必须防止 requester 单人批准自己的高风险 Approval，除非 IAM 显式给出 break_glass 审计字段。
- **FR-012**：系统必须提供 CapabilityGrant v1，覆盖 grant_id、approval_id、agent_id、skill_id、resource_scope、policy_version、issued_at、expires_at、status、revoked_at、audit_id。
- **FR-013**：Grant 消费必须校验 status、expires_at、policy_version 和 resource_scope。
- **FR-014**：Grant 过期或撤销后，后续 Policy Check 不得返回 conditional_allow。
- **FR-015**：系统必须提供 EvidenceVaultSummary，默认返回脱敏摘要、payload_hash、raw_access_state、access_policy、retention_policy、audit_id，不返回 raw_payload。
- **FR-016**：系统必须提供 RawAccessRequest，原文访问必须绑定 evidence_id、requester、reason、approver_scope、ttl_seconds、audit_id。
- **FR-017**：系统必须提供 RawAccessGrant，只有 approved 且未过期时才返回 raw_access_state=approved。
- **FR-018**：redaction_failed 时必须返回 `EVIDENCE_REDACTION_FAILED` 状态，不展示原文、不导出，只保留 payload_hash、安全空摘要占位和告警动作；不得返回未验证的 redacted_summary 内容。
- **FR-019**：系统必须输出 PolicyRequirement Summary，包含 required_by、source、issuer、policy_owner、policy_version、can_ignore、affected_actions、deep_links。
- **FR-019a**：PolicyRequirement Summary 的 deep_links 必须是结构化对象，至少包含 approval_url、policy_url、evidence_url、return_url；必须包含 plain_language、primary_action、secondary_action。
- **FR-020**：系统必须提供阶段 2 SLO Snapshot，覆盖 Policy Check、Approval Service、Evidence Query 的 p95、error_rate、status、degrade_action、review_required。
- **FR-021**：Approval Center view model 必须覆盖 pending、needs_more_info、approved、rejected、expired、revoked、escalated、permission_denied。
- **FR-022**：Policy Center view model 必须展示 policy priority、fallback_action、enforcement_mode、Grant TTL、degraded 和权限失败。
- **FR-023**：Evidence Explorer view model 必须展示 summary_only、pending_approval、approved_limited、expired、redaction_failed、permission_denied。
- **FR-023a**：阶段 2 页面模型必须为 Approval Center、Policy Center、Evidence Explorer、Risk Triage 逐页输出 state、display_name、plain_language、severity、primary_action、secondary_action、owner_hint、audit_id 或 request_id、permission_denied.denied_scope、degrade_action。
- **FR-024**：所有权限失败必须返回 denied_scope、audit_id 或 request_id。
- **FR-025**：AO2-CT-001 到 AO2-CT-006 必须包含正例、反例错误码、幂等/状态流转或兼容性断言。

## 5. 关键实体

- **RuntimePolicy**：运行时策略，定义 risk、fallback、approval policy、grant TTL、enforcement mode。
- **PolicyCheckRequest**：执行前策略检查请求，绑定 action、scope、agent、skill、requester、run/session。
- **PolicyDecision**：策略裁决事实，记录 decision、fallback_action、policy_state_known、audit_id、grant/approval 关联。
- **ApprovalRequest**：高风险动作审批请求，记录原因、影响动作、补充材料、SLA 和通知状态。
- **ApprovalDecision**：审批动作事实，记录 approve/reject/more_info/escalate/revoke、actor、reason、audit_id。
- **CapabilityGrant**：短期能力授权，绑定 approval、scope、policy_version、TTL、状态、撤销与消费审计。
- **EvidenceVaultSummary**：Evidence Vault 摘要视图，不包含原文。
- **RawAccessRequest**：原文访问申请，必须有 reason、approver_scope、ttl、audit_id。
- **RawAccessGrant**：限时原文访问授权，不通过摘要接口返回 raw_payload。
- **SloSnapshot**：阶段 2 链路健康快照，驱动降级和复盘。

## 6. 契约测试矩阵

| test_id | 契约 | 正例 | 反例/错误码 | 状态/兼容性 |
|---|---|---|---|---|
| AO2-CT-001 | Policy Check v2 | active Grant scope 匹配返回 conditional_allow | 缺 resource_scope 返回 `POLICY_SCOPE_REQUIRED`；服务不可用高风险返回 block | policy_version minor 兼容 |
| AO2-CT-001a | Policy Priority | active Grant 存在时更高优先级 deny/block 仍覆盖 conditional_allow | global_deny/IAM deny/project_scope_deny/agent disabled/policy_block 不得被 Grant 绕过 | deny priority 固定 |
| AO2-CT-002 | Approval Lifecycle | approval_required 创建 Approval，approve 后可按原始请求签发 Grant | requester 自批返回 `APPROVAL_SELF_APPROVAL_DENIED`；过期 approval 不签发 Grant；扩大 scope 返回 `GRANT_SCOPE_ESCALATION_DENIED` | pending -> approved/rejected/expired/escalated |
| AO2-CT-003 | Capability Grant | active grant 可消费并审计 | revoked/expired/scope mismatch 不放行 | grant status 流转不可逆 |
| AO2-CT-004 | Evidence Vault Summary | 默认返回脱敏摘要和 raw_access_state | 无 raw grant 返回 `RAW_ACCESS_DENIED`；redaction_failed 不返回原文或不可信 redacted_summary | approved raw grant 限时有效 |
| AO2-CT-005 | Policy Requirement Summary | Store/CLI 获得 required_by/source/issuer/owner/version/actions/deep_links/plain_language/actions | schema 不兼容返回 `POLICY_SUMMARY_SCHEMA_UNSUPPORTED` | minor version 向后兼容 |
| AO2-CT-006 | Stage-2 SLO & Admin Models | SLO healthy/degraded/unknown 映射 Approval/Policy/Evidence/Risk 页面状态 | 缺 SLO 数据不得显示 healthy；permission_denied 必须有 denied_scope | 降级动作和 review_required 可解释 |

## 7. 成功标准

- **SC-001**：AO2-CT-001 到 AO2-CT-006 均有可执行 contract test。
- **SC-002**：高风险动作缺 resource_scope、Policy Service 不可用、Grant revoked/expired/scope mismatch 在测试中 100% 不返回 allow。
- **SC-003**：Approval approved 前不得签发 Grant；approved 后签发的 Grant 100% 绑定 approval_id、scope、policy_version 和 expires_at。
- **SC-004**：Evidence Vault 摘要接口 100% 不返回 raw_payload；redaction_failed 100% 只返回 hash/告警。
- **SC-005**：Policy Requirement Summary 必填字段覆盖率 100%，包含 Store/CLI deep links。
- **SC-006**：SLO 快照能区分 healthy、degraded、unknown，并给出降级动作和复盘标记。
- **SC-007**：`uv run pytest tests -q`、`uv run ruff check`、`uv run ai-sdlc verify constraints` 通过。
- **SC-008**：两个常驻对抗 agent 均无 P0/P1 阻断，AI-SDLC close-check 返回 ok true。

## 8. AI 决策与假设

| 编号 | 决策 | 理由 | 风险控制 |
|---|---|---|---|
| AD2-001 | 阶段 2 先实现可执行内核和契约测试，不上真实 HTTP/Postgres | 延续 001 的 contract-first 路径，避免在 IAM/Store API 未稳定前扩大集成面 | API/实体/错误码先冻结，生产化在后续工作项替换 repository |
| AD2-002 | Grant 只从 approved Approval 签发 | 防止绕过审批直接获得高风险授权 | contract test 覆盖 pending/rejected/expired/revoked |
| AD2-003 | Evidence Vault 摘要接口永不返回原文 | 隐私红线优先于调试便利 | raw access 只返回限时 access_state/audit，不把 raw_payload 放入 summary |

## 9. 开放问题

| 问题 | 当前处理 | 阻塞阶段 |
|---|---|---|
| 统一 IAM 的真实 ABAC/RBAC API 尚未提供 | 阶段 2 使用 IAM decision 输入对象和 contract test mock | 真实联调前 |
| Agent Store/CLI 的最终 policy summary 展示字段可能微调 | 本期冻结兼容字段和 schema version | Store 联调前 |
| Evidence Vault 原文存储后端未定 | 本期只实现摘要、申请和限时 access_state，不落真实原文 | 生产存储实现前 |
