# 功能规格：AgentOps Console MVP 前端界面

**功能编号**：`003-agentops-console-mvp`  
**创建日期**：2026-05-05  
**状态**：对抗评审前草案  
**工作项分类**：`new_requirement`  
**继承 baseline_id**：`agent-platform-baseline-2026-05-v1.4.2`  
**上游依赖**：`001-agentops-trusted-loop` 与 `002-agentops-policy-approval-vault` 已完成可信事件、Evidence Summary、L5 Gate、Policy Check v2、Approval、Capability Grant、Evidence Vault Summary、SLO 与管理员 view model 契约。  
**框架约束来源**：

- `/Users/sinclairpan/project/Ai_AutoSDLC/specs/016-frontend-enterprise-vue2-provider-baseline/spec.md`
- `/Users/sinclairpan/project/Ai_AutoSDLC/README.md` 的 Frontend Managed Delivery Loop
- `/Users/sinclairpan/project/前端组件库1` 作为 SDLC 企业 Vue2 组件库本地来源

## 1. 目标与边界

### 1.1 项目目标

本工作项把 AgentOps 从“可执行后端内核 + 页面模型契约”推进为“可打开、可交互、可验收的治理控制台 MVP”。AgentOps 不能只作为后台服务存在；阶段 3 必须让平台管理员、安全/IAM 审批人、Agent Store 运营者和 AI-SDLC 负责人能在同一个前端入口看到运行事实、风险、审批、策略、证据与连接器状态。

阶段 3 完成后，平台必须能够证明：

1. AgentOps Console 以 Vue 2 为技术栈，并使用 SDLC 企业 Vue2 组件库的白名单包装入口。
2. 控制台首屏可展示 AgentOps 总览、L5 Gate、Policy/SLO、审批积压、证据健康和连接器状态。
3. Runs、Evidence Explorer、Approval Center、Policy Center、Quality Center、Risk Triage、Connector Status、Ai_AutoSDLC Runs 都有可交互 MVP 页面。
4. 页面消费 001/002 已冻结的 view model、PolicyDecision、EvidenceVaultSummary、Approval、CapabilityGrant、SloSnapshot 与 PolicyRequirement Summary 语义，不重新发明业务状态。
5. 权限失败、降级、unknown、empty、pending、redaction_failed、approval_required 等状态有明确 UI 表达，不把未知显示为 healthy/allow。
6. 前端交付包含可执行浏览器验证与截图证据，为后续 managed-delivery/browser-gate 接入留出稳定入口。

### 1.2 本期范围

- `apps/agentops-console/` Vue 2 控制台应用骨架、路由/导航、页面布局、状态管理与 mock data adapter。
- 企业 Vue2 组件库 Provider 约束：只允许白名单包装的组件入口，不允许默认全量 `Vue.use`。
- `@sxf/er-components` 本地组件库来源声明：`/Users/sinclairpan/project/前端组件库1`。
- AgentOps Console 信息架构：Overview、Runs、Evidence Explorer、Approval Center、Policy Center、Quality Center、Risk Triage、Connector Status、Ai_AutoSDLC Runs。
- 管理员工作流：查看总览 -> 定位风险 -> 查看 evidence -> 处理 approval -> 检查 policy/grant -> 回到 run。
- 安全降级 UI：unknown/degraded/permission_denied/redaction_failed 不得展示为 healthy 或 allow。
- `contracts/frontend-console-contract.md`：冻结页面、状态、数据字段、组件白名单、交互和浏览器验收口径。
- 最小浏览器验证：桌面与移动视口可打开、主导航可切换、关键状态可见、页面无明显重叠或空白。

### 1.3 本期不做

- 不做真实生产 HTTP API、登录系统、IAM 集成或多租户权限后端。
- 不做完整设计系统建设，不修改 SDLC 企业 Vue2 组件库源码。
- 不使用全量 `Vue.use(@sxf/er-components)` 作为默认入口。
- 不把 Evidence 原文展示在无权限页面；只展示脱敏摘要、hash、审批状态和受控入口。
- 不在本期实现完整 Agent Store 前端，只提供 Agent Store 摘要与 deep link 可落地的 Console 侧入口。
- 不替换 001/002 已实现的 Python 内核契约；前端只消费和呈现其语义。

## 2. 用户场景与测试

### 用户故事 1 - 管理员打开 AgentOps 总览（优先级：P0）

作为 AgentOps 管理员，我希望打开一个可交互控制台，直接看到运行健康、L5 Gate、Policy/SLO、审批积压、证据风险和连接器状态，以便快速判断系统是否处于可信治理状态。

**优先级说明**：没有控制台入口，AgentOps 会停留在后台服务和测试报告层，无法满足“应用底座可运营”的目标。

**独立测试**：启动 `apps/agentops-console`，打开首页，验证总览指标、风险列表、审批入口、证据入口和连接器状态均可见。

**验收场景**：

1. **Given** 管理员打开 Console，**When** 首页加载，**Then** 看到 runs、evidence、policy、approval、connector、Ai_AutoSDLC 六类治理摘要。
2. **Given** Policy Check SLO unknown，**When** 首页渲染，**Then** 显示 unknown/degraded 提示，不显示 healthy。
3. **Given** 存在 approval_required 风险，**When** 点击风险项，**Then** 可进入 Approval Center 或 Policy Center 的对应上下文。

---

### 用户故事 2 - 审批人处理 Approval（优先级：P0）

作为安全/IAM 审批人，我希望在 Approval Center 看到申请原因、影响动作、SLA、证据摘要、策略来源和 Grant 状态，以便批准、拒绝、要求补充材料或升级。

**优先级说明**：002 已完成 Approval/Grant 契约，本期必须让它成为可操作页面，而不是只存在于后端测试。

**独立测试**：在 Approval Center 切换 pending、needs_more_info、approved、rejected、expired、revoked、escalated 状态，验证主动作、次动作、SLA 和审计 ID 可见。

**验收场景**：

1. **Given** Approval 为 pending，**When** 审批人进入详情，**Then** 看到 requester、reason、affected_actions、policy_version、sla_due_at、audit_id。
2. **Given** Approval 已 approved，**When** 页面展示，**Then** 能看到绑定的 Capability Grant 与 expires_at。
3. **Given** 审批超过 SLA，**When** 页面展示，**Then** 主动作变为升级或提醒，不显示为正常待办。

---

### 用户故事 3 - 运营者查看 Evidence Explorer（优先级：P0）

作为 AgentOps 运营者，我希望在 Evidence Explorer 查看脱敏摘要、payload hash、raw access 状态、redaction_failed 和权限失败，以便在不泄露原文的前提下定位问题。

**优先级说明**：Evidence 是可信治理证明的核心；前端若泄露原文或隐藏脱敏失败，会破坏 002 红线。

**独立测试**：构造 summary_only、pending_approval、approved_limited、expired、redaction_failed、permission_denied 六类状态，验证页面不展示 raw_payload，且 redaction_failed 有告警动作。

**验收场景**：

1. **Given** 用户无 raw grant，**When** 查看 Evidence，**Then** 只展示 redacted_summary、payload_hash、raw_access_state、audit_id。
2. **Given** redaction_failed，**When** 页面展示，**Then** 只展示 hash、告警和补救动作，不显示不可信摘要。
3. **Given** permission_denied，**When** 页面展示，**Then** 显示 denied_scope 和申请权限入口。

---

### 用户故事 4 - 安全负责人排查 Policy 与 Risk（优先级：P0）

作为安全负责人，我希望在 Policy Center 和 Risk Triage 看到策略优先级、decision、fallback_action、Grant TTL、degrade_action 和风险队列，以便识别 block、approval_required、warn、conditional_allow 与 allow 的差异。

**优先级说明**：Policy Check 是 AgentOps 强治理入口；前端必须保持“不知道不能显示为 allow”的红线。

**独立测试**：构造 block、approval_required、warn、conditional_allow、allow、degraded、unknown、permission_denied，验证颜色、文案、动作和筛选结果。

**验收场景**：

1. **Given** Policy Service degraded，**When** 进入 Policy Center，**Then** 高风险动作显示 require_online/block 降级动作。
2. **Given** active Grant 存在但上游 deny 覆盖，**When** 页面展示，**Then** 显示 deny/block 优先，不显示 conditional_allow。
3. **Given** 风险队列有 evidence_failed 和 approval_overdue，**When** 进入 Risk Triage，**Then** 可从风险项跳转到 Evidence 或 Approval 页面。

---

### 用户故事 5 - AI-SDLC 负责人查看运行接入状态（优先级：P1）

作为 AI-SDLC 负责人，我希望在 Console 中看到 Ai_AutoSDLC Runs、adapter 状态、治理激活证明状态和连接器健康，以便判断当前 AgentOps 是否已真正接入 SDLC 治理。

**优先级说明**：用户已明确关心 `materialized / verified_loaded` 区别；Console 必须把 CLI 预演和治理激活证明区别清楚。

**独立测试**：展示 materialized、verified_loaded、degraded、unsupported 四类 adapter 状态，验证 dry-run 不被标记为 verified_loaded。

**验收场景**：

1. **Given** adapter 只有 materialized/unverified，**When** Ai_AutoSDLC Runs 页面展示，**Then** 标注“CLI 预演可运行，但不构成 verified_loaded 证明”。
2. **Given** adapter 为 verified_loaded，**When** 页面展示，**Then** 显示 machine-verifiable evidence、captured_at 和 proof source。
3. **Given** 连接器 degraded，**When** Connector Status 页面展示，**Then** 显示影响范围和下一步处理动作。

## 3. 边界情况

- Console 数据缺失时不得显示 healthy，必须显示 unknown/empty 和 request_id。
- Policy Check、Approval、Evidence Query 的 SLO 缺失时不得用绿色健康态兜底。
- Evidence 页面任何路径不得包含 `raw_payload` 字段展示。
- permission_denied 必须展示 denied_scope、audit_id 或 request_id。
- redaction_failed 不得展示 redacted_summary 正文，只展示 hash、告警和补救动作。
- Approval requester 不得在 UI 上看到“自批通过”的默认路径。
- Grant expired/revoked/scope mismatch 不得在 UI 中显示为 active。
- adapter dry-run 成功不得显示为 `verified_loaded`。
- 企业组件库不可全量 `Vue.use`；只能通过本项目白名单 provider 注册。
- 移动视口下主导航、表格、详情抽屉和操作按钮不得互相遮挡。

## 4. 功能需求

- **FR-001**：系统必须提供 Vue 2 Console 应用入口，默认路径为 `apps/agentops-console/`。
- **FR-002**：系统必须把前端技术栈冻结为 Vue 2，并在 `.ai-sdlc/profiles/tech-stack.yml` 记录。
- **FR-003**：系统必须把组件库冻结为 SDLC 企业 Vue2 组件库，来源为 `/Users/sinclairpan/project/前端组件库1`。
- **FR-004**：系统必须实现企业组件库白名单 Provider，不得默认全量 `Vue.use(@sxf/er-components)`。
- **FR-005**：系统必须提供 Console Shell，包含顶部状态、侧边导航、主内容区和响应式移动导航。
- **FR-006**：系统必须提供 Overview 页面，展示治理摘要、SLO、风险、审批、证据和连接器概览。
- **FR-007**：系统必须提供 Runs 页面，展示 run_id、agent、skill、L5 Gate、policy_state、evidence_state、risk_level。
- **FR-008**：系统必须提供 Evidence Explorer 页面，展示 EvidenceVaultSummary，不展示 raw_payload。
- **FR-009**：系统必须提供 Approval Center 页面，覆盖 pending、needs_more_info、approved、rejected、expired、revoked、escalated、permission_denied。
- **FR-010**：系统必须提供 Policy Center 页面，覆盖 block、approval_required、warn、conditional_allow、allow、degraded、unknown、permission_denied。
- **FR-011**：系统必须提供 Quality Center 页面，展示质量信号、contract test、browser gate、evidence completeness、quality_drop 和 owner_hint。
- **FR-012**：系统必须提供 Risk Triage 页面，覆盖 policy_block、approval_overdue、evidence_failed、quality_drop、degraded、unknown。
- **FR-013**：系统必须提供 Connector Status 页面，展示 Agent Store、AI-SDLC、Evidence Store、Policy Service、IAM/Security 的健康状态。
- **FR-014**：系统必须提供 Ai_AutoSDLC Runs 页面，明确 materialized、verified_loaded、degraded、unsupported 与 dry-run 的区别。
- **FR-015**：系统必须提供 mock data adapter，字段对齐 001/002 view model 和 contract summary。
- **FR-016**：系统必须提供页面级 empty/loading/error/degraded/permission_denied 状态。
- **FR-017**：系统必须提供导航与筛选交互，至少支持页面切换、风险筛选、审批状态筛选、证据状态筛选、质量状态筛选。
- **FR-018**：系统必须提供浏览器验证脚本或命令，覆盖桌面和移动视口截图。
- **FR-019**：系统必须提供前端 contract 文档，冻结页面、状态、字段、组件白名单和验收命令。

## 5. 关键实体

- **ConsoleRoute**：前端页面路由与导航项，绑定 page_id、label、icon、required_scope。
- **ConsoleSummary**：总览摘要，聚合 runs、evidence、policy、approval、risk、connector、sdlc adapter。
- **RunListItem**：运行列表项，承接 run_id、agent、skill、L5 Gate、policy_state、evidence_state、risk_level。
- **EvidencePanelState**：Evidence Explorer 展示状态，承接 EvidenceVaultSummary 与 raw_access_state。
- **ApprovalWorkItem**：审批工作项，承接 ApprovalRequest、SLA、affected_actions 与 Grant 摘要。
- **PolicyDecisionCard**：策略裁决展示，承接 decision、fallback_action、policy_version、grant_id、audit_id。
- **RiskQueueItem**：风险队列项，绑定 severity、source、owner_hint、primary_action、deep_link。
- **QualitySignal**：质量中心信号，绑定 signal_id、category、status、score、owner_hint、evidence_ref、primary_action。
- **ConnectorHealth**：连接器健康，承接 status、last_seen_at、degrade_action、request_id。
- **SdlcAdapterProof**：AI-SDLC adapter 证明状态，区分 dry-run、materialized、verified_loaded、degraded、unsupported。
- **EnterpriseVue2ProviderWhitelist**：企业组件库白名单包装策略，记录允许组件、禁止能力和替换边界。

## 6. 契约测试矩阵

| test_id | 契约 | 正例 | 反例/错误码 | 状态/兼容性 |
|---|---|---|---|---|
| AO3-CT-001 | Console Shell | 首页可打开，导航可切换 | 页面空白、导航不可达失败 | 桌面/移动视口 |
| AO3-CT-002 | Enterprise Vue2 Provider | 白名单组件可用 | 全量 `Vue.use` 或未知组件默认开放失败 | 对齐 016 provider baseline |
| AO3-CT-003 | Evidence UI Safety | summary_only 不展示 raw_payload | redaction_failed 展示正文失败 | 对齐 AO2-CT-004 |
| AO3-CT-004 | Policy/Risk UI | unknown/degraded 不显示 healthy/allow | active grant 绕过 deny 的 UI 表达失败 | 对齐 AO2-CT-001/006 |
| AO3-CT-005 | Approval UI | pending/escalated/approved/revoked 状态可见 | expired/revoked 显示 active 失败 | 对齐 AO2-CT-002/003 |
| AO3-CT-006 | Quality UI | quality_drop、contract gaps、browser gate 状态可见 | 质量状态缺失却显示 healthy 失败 | 对齐 001/002 view model 与 browser gate |
| AO3-CT-007 | SDLC Adapter UI | dry-run 与 verified_loaded 区分清楚 | materialized/unverified 标记为 verified_loaded 失败 | 对齐 AGENTS.md adapter truth |

## 7. 成功标准

- **SC-001**：`apps/agentops-console` 可启动并展示 AgentOps Console MVP。
- **SC-002**：Vue 2 与 SDLC 企业 Vue2 组件库约束写入项目级 `tech-stack.yml` 与 003 contract。
- **SC-003**：Console 至少覆盖 Overview、Runs、Evidence Explorer、Approval Center、Policy Center、Quality Center、Risk Triage、Connector Status、Ai_AutoSDLC Runs 九个页面。
- **SC-004**：Evidence、Policy、Approval、Adapter 的关键安全红线有前端可见状态和验证断言。
- **SC-005**：桌面与移动浏览器截图无空白、无关键文本重叠、主工作流可交互。
- **SC-006**：两个常驻对抗 agent 对正式文档、实现和验证结果均无 P0/P1 阻断意见。
