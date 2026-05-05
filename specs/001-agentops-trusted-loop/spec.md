# 功能规格：AgentOps 可信最小闭环

**功能编号**：`001-agentops-trusted-loop`  
**创建日期**：2026-05-05  
**状态**：对抗评审前草案  
**工作项分类**：`new_requirement`  
**继承 baseline_id**：`agent-platform-baseline-2026-05-v1.4.2`  
**项目 Owner**：AgentOps Owner  
**契约 Owner**：AgentOps 维护 Schema/API/Policy/Evidence Registry 平台；Agent Store 仍是 Agent/Package/Skill/Installation 域 Owner；Ai_AutoSDLC 是 Reporter L5 payload producer Owner。  
**基线来源**：

- `/Users/sinclairpan/project/AI-Native底座开发文档/Agent_Store_AgentOps_AiSDLC_应用底座顶层规划_PRD.md`
- `/Users/sinclairpan/project/AI-Native底座开发文档/AgentOps_项目_PRD.md`

## 1. 目标与边界

### 1.1 项目目标

本工作项建设 AgentOps 阶段 0/阶段 1 的可信最小闭环：以契约优先方式定义并实现 Agent 运行事实接入、证据合成、Ai_AutoSDLC L5 Eligibility Gate、Bootstrap Credential 验签、最小运行查询与 Agent Store 回显摘要。

阶段 1 完成后，平台必须能够证明：

1. enterprise_managed 模式下，一次 Ai_AutoSDLC 真实运行可上报签名事件。
2. AgentOps 能校验 EventEnvelope v1、签名、幂等键和 sequence_no，并写入事件事实。
3. AgentOps 能按 session/run 查询调用链、证据摘要、L5 Gate 结果和降级原因。
4. Agent Store 可消费 AgentOps 输出的质量/证据/风险/审批摘要契约，但 AgentOps 不写 Agent/Skill 注册事实。
5. standalone 模式不被误报为企业接入异常，也不得进入 AgentOps L5 判定。

### 1.2 本期范围

- EventEnvelope v1、L5 核心事件、状态枚举和错误码冻结。
- Schema Registry、API Contract Registry、状态枚举 Registry、错误码 Registry 的 Owner、版本、兼容策略冻结。
- Ingestion API 最小批量接入、schema 校验、签名校验接口、幂等和 outbox 重放语义。
- Raw Event、Domain Event、Evidence Summary、L5 Evaluation 的最小存储模型。
- BootstrapSession、ReporterCredential、IngestionToken、DeviceKey 的签发、验证、轮换/吊销接口契约。
- Bootstrap 签名规范：canonicalization、algorithm、key_id、timestamp skew、nonce/replay window、TTL、轮换和吊销传播。
- Ai_AutoSDLC L5 Eligibility Gate 的 deterministic evaluator。
- 最小查询 API：session/run/step、Evidence Summary、L5 Evaluation、Ingestion health。
- 最小管理员视图需求：Overview、Runs、Evidence Explorer、Risk Triage、Approval Center、Policy Center、Quality Center、Connector Status 的阶段 1 信息架构和状态语义。
- 阶段 0 体验基线：核心用户旅程、服务蓝图、统一 Shell、通知中心、待办中心、全局搜索、状态文案、响应式和 WCAG 2.2 AA 可访问性要求。
- AO-CT-001 到 AO-CT-006 的可执行 contract test。

### 1.3 本期不做

- 不做 Agent Store 首页、卡片推荐、上架向导、安装器主流程、包上传、包签名、自动升级。
- 不改造 Ai_AutoSDLC 本地 CLI 逻辑；只定义 Reporter/Outbox 接入契约并接收事件。
- 不自建统一身份系统；只消费统一认证/IAM 提供的 user、role、attribute、permission 结果。
- 阶段 1 不做完整 Policy Check 强 SLO、高风险运行时强阻断和完整 Capability Grant 生命周期，只提供契约、降级语义和 bootstrap 相关验签。
- 阶段 1 不覆盖全量 Codex/Cursor/Claude Code 过程观测；仅覆盖 Ai_AutoSDLC 标准路径和可导入证据。
- 不做完整质量评分引擎；只输出 Evidence Level、confidence、missing_evidence 和 summary-ready 字段。

## 2. 用户场景与测试

### 用户故事 1 - 平台接入方上报签名事件（优先级：P0）

作为 Ai_AutoSDLC Reporter 维护者，我希望将一次企业托管 run 的事件批量上报到 AgentOps，以便 AgentOps 能保存运行事实并进入 L5 Gate。

**优先级说明**：没有可信事件接入，就没有 Evidence Store、L5 判定、质量回显和风险治理。

**独立测试**：提交一组 enterprise_managed、签名有效、schema 合法、sequence 连续的 EventEnvelope v1 批次，验证 Raw Event/Domain Event 写入且重复重放不重复落库。

**验收场景**：

场景 1: **Given** ReporterCredential 为 active 且事件包含有效 signature、idempotency_key、sequence_no，**When** 调用 Ingestion API，**Then** 系统写入事件并返回 accepted 结果。
场景 2: **Given** 相同 idempotency_key 的事件被 outbox 重放，**When** 再次调用 Ingestion API，**Then** 系统返回 deduplicated，不产生第二条核心事实。
场景 3: **Given** enterprise_managed 事件缺少 signature，**When** 调用 Ingestion API，**Then** 系统拒绝高置信写入并返回 `EVENT_SIGNATURE_REQUIRED`。

---

### 用户故事 2 - 管理员查看一次运行的证据链（优先级：P0）

作为 AgentOps 管理员，我希望按 session/run 查看 step、事件、证据等级和降级原因，以便判断一次运行是否可信、是否需要补证据或通知接入方。

**优先级说明**：阶段 1 的最小可用价值是“能看见一次运行事实，并解释为什么是 L5、pending 或 degraded”。

**独立测试**：导入一条完整 run 和一条缺 fresh verification 的 run，验证查询 API 与页面模型分别返回 L5 与 degraded/pending 解释。

**验收场景**：

场景 1: **Given** run 具备 stage_started、stage_completed、gate_result、violation_scan_completed、verification_result、artifact_generated，**When** 管理员打开 run 详情，**Then** 系统展示完整调用链、证据摘要和 L5 Gate 条件明细。
场景 2: **Given** run 缺少 fresh verification，**When** 系统计算 L5 Gate，**Then** evidence_level 不得为 L5，并在 missing_evidence 中展示缺失来源和补救动作。
场景 3: **Given** 当前用户无原文权限，**When** 查看 Evidence Explorer，**Then** 默认只展示脱敏摘要、hash、raw_access_state 和申请入口，不展示未脱敏原文。

---

### 用户故事 3 - Agent Store 完成手动激活 bootstrap（优先级：P0）

作为 Agent Store 安装/激活流程，我希望用 signed_installation_assertion 换取 ReporterCredential、IngestionToken 和 DeviceKey，以便 Reporter 上报具备 installation、device 和 user 绑定。

**优先级说明**：无 bootstrap 可信身份，签名事件不能进入 L5 Gate。

**独立测试**：使用有效、过期、artifact_hash 不匹配三类 installation assertion，验证 credential 签发、幂等重试和拒绝语义。

**验收场景**：

场景 1: **Given** signed_installation_assertion 有效且 device proof 通过，**When** 调用 Credential Issue API，**Then** 系统签发 active ReporterCredential、IngestionToken、DeviceKey。
场景 2: **Given** 同一 bootstrap_id 被重试，**When** 再次调用 Credential Issue API，**Then** 系统返回同一 credential 状态，不重复创建冲突凭证。
场景 3: **Given** assertion 已过期，**When** 调用 Credential Issue API，**Then** 系统返回 `BOOTSTRAP_EXPIRED`，不得签发 token。

---

### 用户故事 4 - 安全/IAM 看到策略裁决口径（优先级：P1）

作为安全/IAM 负责人，我希望 AgentOps 定义 PolicyDecision、fallback_action 和 Approval/Grant 关系，以便阶段 2 能进入强 Policy Check，同时阶段 1 对高风险未知状态有清晰降级。

**优先级说明**：阶段 1 不强制完整阻断，但必须避免“策略未知却显示安全”的误导。

**独立测试**：构造高风险动作缺 resource_scope、Policy Service 不可用、approval_required 三类决策，验证输出枚举和降级解释。

**验收场景**：

场景 1: **Given** 高风险动作缺 resource_scope，**When** 调用 PolicyDecision 契约测试，**Then** 系统返回 `POLICY_SCOPE_REQUIRED`。
场景 2: **Given** Policy Service 不可用且 action 为高风险，**When** 系统生成 run 摘要，**Then** policy_state_known 为 false，并展示 require_online/block 降级说明。

---

### 用户故事 5 - Agent Store 消费 AgentOps 摘要（优先级：P1）

作为 Agent Store 详情页，我希望消费 AgentOps 的证据、风险、审批和质量摘要，以便用户在商店中看到可信但不越权的运行健康信号。

**优先级说明**：质量和证据结果由 AgentOps 产生，必须能回显到 Agent Store，但 Store 不应拿到未脱敏原文。

**独立测试**：调用 summary API，验证返回 score_template_id、evidence_level、confidence、missing_evidence、risk_state、approval_state、valid_until 和脱敏字段。

**验收场景**：

场景 1: **Given** Agent Store 请求某 agent/version 的摘要，**When** schema_version 兼容，**Then** 系统返回可回显摘要和 deep link 字段。
场景 2: **Given** consumer schema 不兼容，**When** Agent Store 请求摘要，**Then** 系统返回 `SUMMARY_SCHEMA_UNSUPPORTED`，不得返回半结构化字段。

## 3. 边界情况

- `integration_mode=standalone` 的远端事件只能作为 imported evidence 或被解释性拒绝，不得进入 AgentOps L5。
- `integration_mode=custom_sink` 不得冒用 enterprise credential 或 AgentOps L5。
- governance 为 degraded/unsupported 时最高 L4，并必须展示降级原因。
- Outbox 未送达但本地签名缓存可验证时只能显示 `pending L5 verification`。
- 缺 signature、token 失效、device revoked、credential revoked 的事件不得进入 L5。
- successful run 不要求出现 gate_failed 或 violation_detected，但必须有 gate_result 和 violation_scan_completed。
- 脱敏失败时只保留 hash/摘要并告警，原文不得展示或导出。
- Agent Store 元数据缺失时 AgentOps 可记录 unknown，但不得执行强治理或下架建议。
- 旁路发现的未注册 Agent 只能进入 suspected/discovered/notified，不得误称已治理。

## 4. 功能需求

- **FR-001**：系统必须提供 EventEnvelope v1 schema，覆盖 event_id、schema_version、event_type、event_type_version、timestamp、integration_mode、enterprise_state、user_id、identity_confidence、agent_id、agent_version、installation_id、device_id、session_id、run_id、trace_id、sequence_no、idempotency_key、signature、data_classification、redaction_policy、payload。
- **FR-001a**：EventEnvelope v1 必须覆盖调用链字段 span_id、parent_span_id；enterprise_managed 事件必须包含 user_id、identity_confidence、agent_id、agent_version、installation_id、device_id、signature、source_trust_level、ingestion_token、credential_status、device_key_status，缺失任一可信绑定或 active 状态不得进入 managed/L5；standalone 使用 local_subject、local_workspace_hash、local_report_uri，不得伪造企业身份；custom_sink 使用 sink_id、sink_capability_id、external_subject。
- **FR-002**：系统必须维护统一 Event Catalog，区分 raw event、domain event、derived fact，derived fact 必须保留来源 event_id 列表。
- **FR-002a**：L5 核心事件必须至少包含 stage_started、stage_completed、gate_result、verification_result、violation_scan_completed、artifact_generated、generation_snapshot、l5_eligibility_input；gate_failed 与 violation_detected 是失败/发现分支事件，成功 run 不要求出现。
- **FR-003**：系统必须实现 Ingestion API 批量接收，并校验 schema_version、event_type_version、signature、token、idempotency_key、sequence_no。
- **FR-004**：系统必须对 event_id 和 idempotency_key 执行幂等保护，支持 outbox 重放不重复写核心事实。
- **FR-005**：系统必须识别 integration_mode：standalone、enterprise_managed、custom_sink、unknown，并按模式执行 L5、imported evidence 或拒绝/降级。
- **FR-006**：系统必须提供 Raw Event 与 Domain Event 写入模型，禁止无结构日志直接进入核心事实表。
- **FR-007**：系统必须提供 L5 Eligibility Gate evaluator，按 reporter_enabled、governance_loaded、schema_valid、source_signed、identity_confidence、session_mapping、stage_events_complete、verification_fresh、artifact_linked、outbox_delivered、policy_state_known 逐项判定。
- **FR-008**：系统必须将 L5-capable 和实际 run-level L5 分开表示，不得仅因 Ai_AutoSDLC 是官方应用而标记所有 run 为 L5。
- **FR-009**：系统必须输出 evidence_level、source_trust、completeness、freshness、confidence、missing_evidence 和 downgrade_reason。
- **FR-010**：系统必须提供 Evidence Summary API，默认返回 data_classification、redaction_policy、access_policy、retention_policy、redacted_summary、payload_hash、raw_access_state 和 linked_event_ids。
- **FR-011**：系统必须为 Evidence Vault 原文访问保留审批、审计、限时访问状态字段；阶段 1 可先实现摘要和申请状态，不暴露原文。
- **FR-012**：系统必须提供 Credential Issue API，校验 signed_installation_assertion、artifact_hash、issuer、expires_at 和 device proof 后签发 ReporterCredential、IngestionToken、DeviceKey。
- **FR-012a**：Credential Issue API 必须定义 signed_installation_assertion 的 canonicalization、algorithm、key_id、issued_at/expires_at、timestamp skew、nonce、replay window、assertion TTL、device proof TTL、轮换与吊销传播语义。
- **FR-013**：系统必须支持 BootstrapSession、ReporterCredential、IngestionToken、DeviceKey 的 active、expired、revoked 等状态，并在事件校验中生效。
- **FR-014**：系统必须提供 Signature Test API，用于验证首个签名事件是否能被 AgentOps 接受。
- **FR-015**：系统必须提供 session/run/step 查询 API，返回调用链、事件状态、证据摘要、policy_state_known 和 L5 Gate 结果。
- **FR-016**：系统必须定义 PolicyDecision 契约，包含 block、approval_required、warn、conditional_allow、allow、fallback_action、policy_version 和 decision_reason。
- **FR-017**：阶段 1 中高风险策略未知时，系统必须展示 require_online/block 降级说明，不得展示为 allow。
- **FR-018**：系统必须提供 Agent Store Summary 契约，强制输出 score_template_id、evidence_level、confidence、missing_evidence、risk_state、approval_state、calculated_at、valid_until 和 deep link 字段，不返回未授权原文。
- **FR-019**：系统必须定义 AO-CT-001 到 AO-CT-006 contract tests，并保证每个测试包含正例、反例错误码、幂等/兼容性断言。
- **FR-020**：系统必须记录 Connector/Ingestion freshness、rate_limit、DLQ 和 replay watermark，用于 Connector Status 和证据降级。
- **FR-021**：系统必须为管理员页面模型提供空状态、错误状态、pending/degraded/failed 状态和下一步动作字段。
- **FR-022**：系统必须保留跨项目 deep link 字段：agent_id、version、session_id/run_id、installation_id、trace_id、audit_id、return_url。
- **FR-023**：系统必须在所有权限失败场景返回 denied_scope、audit_id 或 request_id，避免静默失败。
- **FR-024**：系统必须提供 schema minor version 向后兼容策略；不兼容时返回可解释错误码。
- **FR-025**：系统必须保留 standalone 回归契约，确保未配置 Agent Store/AgentOps 时 Ai_AutoSDLC 核心命令不被强制登录或远端依赖阻断。
- **FR-026**：系统必须输出阶段 0 核心用户旅程和服务蓝图，覆盖审批处理、证据失败处理、风险 triage、质量回显、Store 深链返回。
- **FR-027**：管理员页面模型必须定义统一 Shell、通知中心、待办中心、全局搜索入口与跨系统 return_url，不允许只做孤立后台页面。
- **FR-028**：所有状态枚举必须有展示名、白话解释、严重度、主动作、次动作、可见角色、通知规则、审计要求、Owner 和允许流转。
- **FR-029**：Risk Triage 必须按 今日最急、待我处理、影响范围、建议动作、关闭条件 组织，不得退化为纯指标看板。
- **FR-030**：Approval Center 必须冻结审批原因、审批人、SLA、补充材料、撤回、拒绝原因、过期/撤销影响、权限失败和 Store/通知/审计回显字段。
- **FR-031**：Policy Center 必须冻结裁决优先级、fallback_action、enforcement_mode、policy_version、resource_scope、Grant TTL、降级状态和权限失败字段。
- **FR-032**：Quality Center 必须冻结 score_template_id、证据等级、置信度、缺失证据、解释链、申诉路径和低置信不自动下架规则。

## 5. 非功能需求

- **NFR-001 可观测性**：Ingestion API 必须统计 accepted、rejected、deduplicated、schema_failed、signature_failed、replay_lag。
- **NFR-002 性能目标**：阶段 1 Ingestion API P95 <= 800ms；Evidence Summary 查询 P95 <= 2s。
- **NFR-003 安全**：事件签名、token、device key、credential 状态必须参与高置信写入；未签名事件不得进入 L5。
- **NFR-004 隐私与脱敏**：prompt、diff、日志、模型输入输出默认 hash/摘要，原文访问必须经 Evidence Vault 流程。
- **NFR-005 可访问性**：管理员页面模型必须支持键盘可达、焦点可见、权限失败页不暴露未授权原文。
- **NFR-005a 可访问性基线**：阶段 0/1 页面模型必须以 WCAG 2.2 AA 为目标，定义响应式断点、焦点顺序、错误摘要、表格键盘导航和权限失败页可读性。
- **NFR-006 可演进性**：所有 schema、错误码、状态枚举必须有 owner 和版本，不允许各生产者自定义同义事件。

## 6. 关键实体

- **Session**：用户意图或工作项上下文，关联 user、project、repo、workitem、source_type。
- **Run**：Agent 对 Session 的一次执行尝试，关联 agent_id、version、status、evidence_level、enforcement_mode。
- **Step**：Run 内可解释动作，支持 parent_step_id、step_type、status。
- **Event**：EventEnvelope v1 的规范化事件事实，包含 trace/span、sequence、idempotency 和 signature 状态。
- **Evidence**：证据摘要与等级，包含 level、trust、confidence、data_classification、redaction_policy、access_policy、retention_policy、raw_access_state。
- **L5Evaluation**：L5 Gate 逐项判定结果，包含 failed_conditions、missing_evidence、downgrade_reason。
- **BootstrapSession**：安装激活会话，绑定 installation_id、device_id、user_id、artifact_hash、status、expires_at。
- **ReporterCredential**：Reporter 上报凭证，绑定 installation、device、scope、status、revoked_at。
- **IngestionToken**：短期上报 token，绑定 credential_id、ttl、last_used_at、status。
- **DeviceKey**：设备公钥状态，支持 active、rotating、lost、revoked。
- **PolicyDecision**：运行时策略裁决事实，包含 decision、fallback_action、policy_version、reason。
- **Approval**：审批事实，包含 requester、approver、decision、expires_at、SLA、audit_id。
- **QualitySummary**：阶段 1 摘要字段，包含 score_template_id、evidence_level、confidence、missing_evidence。

## 7. 契约测试矩阵

| test_id | 契约 | 正例 | 反例/错误码 | 幂等与兼容性 |
|---|---|---|---|---|
| AO-CT-001 | Reporter Event Envelope | 签名 enterprise_managed 事件写入 Raw Event，L5 核心 payload 最小字段通过 schema | 缺 signature 返回 `EVENT_SIGNATURE_REQUIRED`；L5 核心 payload 缺必填字段返回 `EVENT_PAYLOAD_INVALID` | idempotency_key 重放不重复写 |
| AO-CT-002 | Credential Issue API | active bootstrap 签发 credential/token/device key | 过期 bootstrap 返回 `BOOTSTRAP_EXPIRED` | 同 bootstrap 重试返回同 credential 状态 |
| AO-CT-003 | Evidence Summary | 输出脱敏摘要和 raw_access_state | 无权限返回 `RAW_ACCESS_DENIED` | 旧 schema 摘要可降级展示 |
| AO-CT-004 | PolicyDecision | 高风险动作返回 block/approval_required | 缺 resource_scope 返回 `POLICY_SCOPE_REQUIRED` | policy_version 兼容旧决策查询 |
| AO-CT-005 | Agent Store Summary | Store 可消费质量/风险/审批摘要 | consumer schema 不兼容返回 `SUMMARY_SCHEMA_UNSUPPORTED` | schema minor version 向后兼容 |
| AO-CT-006 | Integration Mode Ingestion | enterprise_managed 进入 L5 Gate；custom_sink 作为 imported evidence | unknown mode 返回 `INTEGRATION_MODE_UNSUPPORTED` | integration_mode 幂等兼容 |

## 7.1 顶层追踪矩阵

| 顶层基线 | 本工作项落点 | Owner |
|---|---|---|
| AgentOps 是运行事实与质量面 | Ingestion、Event、Evidence、L5Evaluation、Store Summary | AgentOps |
| Agent Store 是入口与分发面 | 只消费 Agent/Version/Skill/Installation 元数据，只回显 summary | Agent Store + AgentOps |
| Ai_AutoSDLC 是标准证据生产面 | Reporter/Outbox/EventEnvelope/L5 core payload | Ai_AutoSDLC + AgentOps |
| 统一 Event Catalog | `contracts/event-envelope-v1.schema.yaml`、`contract-tests.md` | AgentOps Schema Registry |
| Evidence/Data Classification | Evidence Summary、raw_access_state、retention/access policy | AgentOps + 安全/IAM |
| Runtime Policy/Approval | PolicyDecision、fallback_action、阶段 1 降级口径 | AgentOps Policy Service |
| 统一状态语义 | 管理员页面模型、Store Summary、错误码/状态 registry | AgentOps + 统一体验 Owner |

## 7.2 阶段 0 体验验收基线

| 体验对象 | 必须冻结的内容 |
|---|---|
| 核心用户旅程 | 审批处理、证据失败处理、风险 triage、质量回显、Ai_AutoSDLC run 降级 |
| 服务蓝图 | 前台页面、后台系统、状态变化、通知触点、失败兜底、责任 Owner |
| 统一 Shell | Agent Store 与 AgentOps 一级入口、面包屑、return_url、角色默认首页 |
| 通知中心 | 审批变化、DLQ、证据降级、credential revoked、Store 回显失败 |
| 待办中心 | 待审批、待补证据、待通知 Owner、待关闭风险、待复核豁免 |
| 全局搜索 | 普通用户只见可见摘要；管理员按权限搜索 run/evidence/risk/approval |
| 状态文案 | 不直接暴露机器枚举；每个状态都有白话解释、影响范围和下一步 |
| 可访问性 | WCAG 2.2 AA、键盘可达、焦点可见、权限失败不泄露敏感事实 |
| Approval/Policy/Quality | 页面 IA、空状态、错误状态、降级状态、权限失败、主动作、关闭条件和跨 Store 回显 |

## 8. 成功标准

- **SC-001**：EventEnvelope v1、L5 核心事件、Bootstrap Credential、PolicyDecision、Evidence Summary、Agent Store Summary 至少各有 1 个可执行 contract test。
- **SC-002**：有效签名事件 schema/signature 校验通过率在测试集中达到 100%；缺签名 enterprise_managed 事件 100% 不进入 L5。
- **SC-003**：重复 outbox 重放在测试集中重复写入率为 0。
- **SC-004**：完整 Ai_AutoSDLC run 可生成 session/run/step、Evidence Summary 和 L5Evaluation；缺 fresh verification 的 run 不得显示 L5。
- **SC-005**：standalone / custom_sink / enterprise_managed 三种 integration_mode 均有正反例测试，standalone 不被误判为企业异常。
- **SC-006**：Agent Store Summary 返回字段 100% 包含 evidence_level、confidence、missing_evidence、calculated_at、valid_until、deep links。
- **SC-007**：管理员页面模型覆盖 pending、degraded、failed、permission_denied、empty 五类状态，并为每类状态提供下一步动作。
- **SC-008**：`ai-sdlc gate refine` 与 `ai-sdlc gate design` 通过；若 design 进入代码实现前仍有未决项，必须记录到 decisions.yml 或本 spec 的开放问题。

## 9. AI 决策与假设

| 编号 | 决策 | 理由 | 风险控制 |
|---|---|---|---|
| AD-001 | 阶段 1 以 Ai_AutoSDLC enterprise_managed 标准路径为唯一强闭环 | 顶层 PRD 明确阶段 1 不承诺全量多路径治理 | custom_sink/standalone 只做导入或降级语义 |
| AD-002 | 阶段 1 不实现完整质量评分，只实现 summary-ready 字段 | 质量评分属于阶段 5，提前实现会扩大范围 | 保留 score_template_id、confidence、missing_evidence 契约 |
| AD-003 | Policy Check 强 SLO 推迟到阶段 2 | AgentOps PRD 明确阶段 1 只验收 bootstrap、Ingestion、证据链关键链路 | 高风险未知默认 require_online/block 降级说明 |

## 10. 开放问题

| 问题 | 当前处理 | 阻塞阶段 |
|---|---|---|
| 统一 IAM 的真实 API 形态尚未提供 | 阶段 1 以接口适配层和 contract test mock 表达 | 阶段 2 强 Policy Check 前 |
| Agent Store registry API 的最终字段可能调整 | 阶段 1 使用 summary/metadata consumer contract，保持 owner 边界 | 阶段 1 回显联调前 |
| 是否使用 Postgres 作为正式存储尚未由项目确认 | 设计按 SQL 关系模型表达，开发期可用 SQLite 适配 | 代码实现前 |
