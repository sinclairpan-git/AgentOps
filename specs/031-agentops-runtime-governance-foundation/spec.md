# 功能规格：AgentOps Runtime Governance Foundation

**功能编号**：`031-agentops-runtime-governance-foundation`  
**创建日期**：2026-05-09  
**状态**：待执行  
**工作项分类**：`new_requirement`  
**继承 baseline_id**：`agent-platform-baseline-2026-05-v1.4.2`  
**项目 Owner**：AgentOps Owner  
**契约 Owner**：AgentOps 维护 Policy / Grant / Approval / Evidence / Health / Eval 域契约；Agent Runtime 是 RuntimeRun / TraceSpan / Outbox 生产事实源；Agent Store 是 AgentManifest / Installation 事实源；Ai_AutoSDLC 是 SDLC evidence payload 事实源。  
**基线来源**：

- `/Users/sinclairpan/project/AI-Native底座开发文档/AgentOps_项目_PRD.md`
- `/Users/sinclairpan/project/AI-Native底座开发文档/Agent_Runtime_项目_PRD.md`
- `/Users/sinclairpan/project/AI-Native底座开发文档/Agent_Store_AgentOps_AiSDLC_应用底座顶层规划_PRD.md`

## 1. 目标与边界

### 1.1 项目目标

本工作项承接新 PRD 下 AgentOps 的第一组 P0 拆分需求，覆盖：

1. **AO-P0-01 Contract / Schema Registry 最小治理**：冻结 AgentOps 与 Runtime 对接的最小 P0 契约、状态、错误码、Owner 和 contract tests。
2. **AO-P0-02 Ingestion API v1**：接收 Runtime 上报的 `RuntimeRun`、`TraceSpan`、`EventEnvelope`、Guardrail result、Artifact refs，执行 schema、签名、幂等、sequence 和 source_trust 校验。
3. **AO-P0-03 Runtime Run Detail**：按 `session_id / run_id / step_id / span_id` 查询运行详情，展示运行状态、失败原因、PolicyDecision、Guardrail、Artifact 摘要。
4. **AO-P0-04 Trace Timeline**：展示 Runtime TraceSpan 链路，覆盖 `agent / workflow / model / tool / retrieval / handoff / approval / guardrail / artifact / system`。

阶段完成后，AgentOps 必须能证明一条最小 Runtime 治理链路：

```text
Runtime 上报 RuntimeRun + TraceSpan
  -> AgentOps Ingestion 校验并落事实
  -> 管理员查看 Run Detail / Trace Timeline
  -> 缺失、待上报、降级、阻断状态可解释
```

### 1.0 后续需求池归档

AgentOps P0 / P1 / P2 全量需求池已归档到 `agentops-p0-p2-backlog.md`。后续新增工作项必须优先从该归档选择需求包编号，避免每一阶段重新归纳。

### 1.2 本期范围

- Contract Registry 最小条目：`RuntimeRun`、`TraceSpan`、`EventEnvelope`、`PolicyDecision`、`CapabilityGrant`、`Approval`、`EvidenceSummary`、`HealthSummary`、`StateRegistry`。
- Schema Registry 最小校验：字段类型、必填字段、枚举、schema_version、event_type_version。
- Runtime Ingestion API v1：批量接收、幂等、签名状态、sequence_no、payload_hash、payload_ref、source_trust、DLQ/rejection reason。
- Run Detail 查询模型：session/run/attempt/status/terminal_reason、policy summary、guardrail summary、artifact refs、outbox state。
- Trace Timeline 查询模型：span tree、parent-child 关系、span_kind、status_code、duration、token/cost 摘要、input/output 引用。
- Console 数据契约：`apps/agentops-console` 可消费新的 run detail 与 trace timeline 字段，未接真实后端时仍能用 mock 数据表达状态。
- AO31-CT-001 到 AO31-CT-008 的可执行 contract test 定义。

### 1.3 本期不做

- 不实现完整 EvidenceSummary 合成、HealthSummary 计算和 Store 回写；这些进入后续 AO-P0-05 / AO-P0-06。
- 不实现 Approval Center 完整 pause/resume、补充材料和 SLA；本期只展示审批 span 与 policy decision 事实。
- 不实现完整质量评分、EvalCase scorer、safe replay、simulation、ROI。
- 不做 Runtime 执行、Agent 包加载、Tool/Model 调用或 Outbox 生产；这些属于 Agent Runtime。
- 不做统一门户入口、全局首页或账号体系。
- 不把 OpenTelemetry/OpenInference 作为内部 P0 唯一模型；P1 再做 exporter。

## 2. 用户场景与测试

### 用户故事 1 - 平台 Owner 冻结跨项目契约（P0）

作为 AgentOps Owner，我希望看到每个 Runtime 接入契约的 Domain Owner、Producer、Consumer、必填字段、错误码和 contract test，以便 Runtime、Store、Ops 不再各自发明字段。

**独立测试**：读取 registry 输出，验证 P0 契约均有 owner、schema_version、required fields、state mapping、错误码和至少一个 contract test。

**验收场景**：

场景 1: Contract Registry 缺少 Owner 时拒绝通过
- **Given** Contract Registry 中缺少 `TraceSpan` 的 Owner，**When** 运行 AO31 contract registry gate，**Then** 返回 `CONTRACT_OWNER_REQUIRED`。

场景 2: 未登记枚举不能进入契约
- **Given** `PolicyDecision.decision` 出现未登记枚举，**When** 校验 schema，**Then** 返回 `CONTRACT_ENUM_UNREGISTERED`。

场景 3: 状态展示冲突必须显式失败
- **Given** Runtime 和 Ops 对同一状态使用不同展示名，**When** 校验 State Registry，**Then** 返回 `STATE_DISPLAY_MISMATCH`。

### 用户故事 2 - Runtime 上报运行事实（P0）

作为 Agent Runtime，我希望用批量 Ingestion API 上报 RuntimeRun、TraceSpan、Guardrail result 和 Artifact refs，以便 AgentOps 保存可治理事实并能安全去重重放。

**独立测试**：提交有效批次、重复批次、乱序批次、签名失败批次和 schema 拒绝批次，验证 accepted/deduplicated/rejected/dlq 语义。

**验收场景**：

场景 1: 有效 Runtime 批次可写入运行事实
- **Given** 有效 Runtime 事件批次包含 `sequence_no`、`idempotency_key`、`signature`、`payload_hash`，**When** 调用 Ingestion API，**Then** 返回 accepted 并创建 run/span 事实。

场景 2: Outbox 重放不会重复写事实
- **Given** 同一 `idempotency_key` 的事件被 Outbox 重放，**When** 再次调用 Ingestion API，**Then** 返回 deduplicated，不创建第二份运行事实。

场景 3: 缺失父 span 时 timeline 降级
- **Given** `TraceSpan.parent_span_id` 指向不存在 span，**When** 批次结束校验 timeline，**Then** 返回 `TRACE_PARENT_MISSING`，并将 timeline 标为 degraded。

### 用户故事 3 - 管理员查看 Runtime Run Detail（P0）

作为 AgentOps 管理员，我希望按 run 查看执行状态、失败原因、PolicyDecision、Guardrail、Artifact 和 Outbox 状态，以便快速判断当前问题是运行失败、策略阻断、审批等待还是上报延迟。

**独立测试**：导入 succeeded、failed、blocked、approval_paused、trace_pending 五类 run，验证 Run Detail 返回白话状态、下一步动作、关联 span 和审计线索。

**验收场景**：

场景 1: 策略阻断 run 展示可解释原因
- **Given** run 状态为 `blocked` 且有 PolicyDecision，**When** 打开 Run Detail，**Then** 展示 reason_code、fallback_action、policy_set_version 和 audit_id。

场景 2: 审批暂停 run 展示审批进度入口
- **Given** run 状态为 `approval_paused`，**When** 打开 Run Detail，**Then** 展示 approval_id、pause_token 摘要、SLA 和查看审批进度入口。

场景 3: 缺少 TraceSpan 时展示待上报
- **Given** run 只有 RuntimeRun 但缺 TraceSpan，**When** 打开 Run Detail，**Then** 展示 `trace_pending` 而不是空白或成功。

### 用户故事 4 - 管理员查看 Trace Timeline（P0）

作为 AgentOps 管理员，我希望看到 span 链路、span kind、状态、耗时、输入输出引用和错误码，以便定位 Tool/Model/Guardrail/Artifact 哪一步出了问题。

**独立测试**：导入包含 model、tool、approval、guardrail、artifact 五类 span 的 trace，验证 timeline 顺序、父子关系、降级状态和脱敏摘要。

**验收场景**：

场景 1: Timeline 按链路关系展示 span
- **Given** trace 包含 model/tool/guardrail/artifact span，**When** 查询 timeline，**Then** 按 start_time 和 parent-child 关系展示。

场景 2: 无原文权限时只展示脱敏引用
- **Given** span 含 `input_ref/output_ref`，**When** 用户无原文权限，**Then** 只展示 hash/摘要和 Evidence Vault 申请状态。

场景 3: token 和 cost 只做摘要展示
- **Given** span 上报了 token_usage 和 cost_estimate，**When** 打开 timeline，**Then** 展示 run 级汇总但不进入完整成本预算治理。

## 3. 边界情况

- `EventEnvelope.schema_version` 不支持时必须拒绝或降级，不得半结构落库。
- `RuntimeRun` 缺 `runtime_id`、`run_id`、`agent_id` 或 `status` 时必须拒绝。
- `TraceSpan` 缺 `trace_id`、`span_id`、`span_kind`、`start_time` 或 `status_code` 时必须拒绝。
- `span_kind` 未登记时标记 `TRACE_SPAN_KIND_UNSUPPORTED`，不得映射为普通 system span。
- 签名缺失的受管 Runtime 事件不得进入高可信事实；可进入 suspected/imported 线索必须降级。
- 重放事件必须以 `idempotency_key` 和 `sequence_no` 去重；乱序不得造成 timeline 伪成功。
- 原文、prompt、diff、model input/output 默认只用 `payload_hash`、`payload_ref` 或脱敏摘要。
- Policy Service 不可用时，高风险动作必须展示 `policy_unavailable` 和 fallback_action，不得展示 allow。
- Store 或 Runtime 深链缺权限时必须返回 request_id/audit_id/denied_scope，不暴露未授权原文。

## 4. 功能需求

- **FR-001**：系统必须提供 Contract Registry 最小实现，覆盖 P0 契约的 Domain Owner、Producer、Consumer、required fields、state mapping、错误码、deprecation policy 和 contract test id。
- **FR-002**：系统必须提供 Schema Registry 最小实现，覆盖 `RuntimeRun`、`TraceSpan`、`EventEnvelope`、`PolicyDecision`、`CapabilityGrant`、`Approval`、`EvidenceSummary`、`HealthSummary`。
- **FR-003**：系统必须维护 State Registry，至少包含 `running`、`approval_paused`、`succeeded`、`failed`、`cancelled`、`timeout`、`blocked`、`trace_pending`、`degraded`、`schema_rejected`、`signature_failed`。
- **FR-004**：系统必须维护错误码 Registry，覆盖 `CONTRACT_OWNER_REQUIRED`、`CONTRACT_ENUM_UNREGISTERED`、`EVENT_SCHEMA_UNSUPPORTED`、`EVENT_SIGNATURE_INVALID`、`EVENT_IDEMPOTENCY_CONFLICT`、`TRACE_PARENT_MISSING`、`TRACE_SPAN_KIND_UNSUPPORTED`。
- **FR-005**：Ingestion API v1 必须支持批量提交 Runtime 事件，并返回逐条 accepted、deduplicated、rejected、dlq 状态。
- **FR-006**：Ingestion API v1 必须校验 `schema_version`、`event_type_version`、`idempotency_key`、`sequence_no`、`signature_state`、`payload_hash`、`source_trust`。
- **FR-007**：系统必须将 RuntimeRun 规范化为 run fact，字段至少包含 runtime_id、runtime_version、execution_environment、session_id、run_id、attempt_no、agent_id、version、trigger_source、isolation_profile、policy_bundle_version、status、terminal_reason。
- **FR-008**：系统必须将 TraceSpan 规范化为 span fact，字段至少包含 trace_id、span_id、parent_span_id、span_kind、operation_name、status_code、start_time、end_time、attempt_no、input_ref、output_ref、token_usage、cost_estimate、grant_id、guardrail_result_refs、error_code、retryable。
- **FR-009**：系统必须支持 span parent-child 校验，父 span 缺失时 timeline 标为 degraded，并保留缺失引用。
- **FR-010**：系统必须支持 Outbox 重放幂等，重复事件不得造成重复 run/span fact。
- **FR-011**：系统必须提供 Run Detail API / view model，返回 run 状态、下一步动作、policy summary、approval summary、guardrail summary、artifact refs、outbox state、audit_id。
- **FR-012**：系统必须提供 Trace Timeline API / view model，返回 span tree、排序、duration、状态、脱敏 input/output 摘要、错误码和降级原因。
- **FR-013**：Run Detail 必须把 `blocked`、`approval_paused`、`trace_pending`、`policy_unavailable`、`signature_failed` 映射为用户可理解状态与主动作。
- **FR-014**：Trace Timeline 必须支持 model/tool/approval/guardrail/artifact 五类最小 span；其他 P0 枚举可展示但不要求深度详情。
- **FR-015**：Console mock 数据必须覆盖 succeeded、blocked、approval_paused、trace_pending、degraded 五类运行。
- **FR-016**：权限不足时 Run Detail / Trace Timeline 只返回脱敏摘要、request_id、audit_id、denied_scope 和 request_access_url。
- **FR-017**：系统必须将 AO31 契约测试加入 contract test 文档，后续执行阶段必须转化为可运行测试文件。
- **FR-018**：本工作项不得改变 Ai_AutoSDLC standalone 语义；standalone 事件只能作为 imported/degraded 线索。

## 5. 非功能需求

- **NFR-001 可追踪性**：所有新增字段必须能追溯到顶层 PRD 第 14 章或 AgentOps PRD 第 16 章。
- **NFR-002 可验证性**：AO31 contract tests 必须覆盖正例、反例、幂等、兼容和降级。
- **NFR-003 安全**：未签名、签名失败或凭证吊销事件不得进入高可信事实。
- **NFR-004 隐私**：prompt、模型输入输出、diff、terminal 原文不进入默认 Run Detail / Timeline。
- **NFR-005 兼容性**：不得破坏 001-030 既有 contract tests；新增 schema 必须 additive。
- **NFR-006 性能目标**：P0 查询模型面向控制台使用，Run Detail / Timeline 查询目标 P95 <= 2s。

## 6. 关键实体

- **ContractRegistryEntry**：跨项目契约条目，绑定 owner、producer、consumer、required_fields、error_codes、contract_tests。
- **StateRegistryEntry**：状态白话映射，包含 machine_value、display_name、plain_language_explanation、severity、primary_action、allowed_next_states。
- **RuntimeRunFact**：Runtime 上报并经 AgentOps 校验后的运行事实。
- **TraceSpanFact**：Runtime 上报并经 AgentOps 校验后的链路步骤事实。
- **EventEnvelopeFact**：标准事件信封事实，承载 schema、source_trust、signature、idempotency 和 payload 引用。
- **RunDetailProjection**：面向 API/Console 的运行详情投影，不包含未授权原文。
- **TraceTimelineProjection**：面向 API/Console 的 trace tree 投影，包含降级和脱敏信息。
- **IngestionReceipt**：批量接入回执，逐条表达 accepted、deduplicated、rejected、dlq。

## 7. 契约测试矩阵

| test_id | 契约 | 正例 | 反例/错误码 | 幂等与兼容性 |
|---|---|---|---|---|
| AO31-CT-001 | Contract Registry | P0 契约均有 Owner、Producer、Consumer、required fields、contract test id | 缺 Owner 返回 `CONTRACT_OWNER_REQUIRED` | additive 字段不破坏旧 consumer |
| AO31-CT-002 | Runtime Ingestion Batch | 有效 RuntimeRun + TraceSpan 批次 accepted | schema 不支持返回 `EVENT_SCHEMA_UNSUPPORTED` | 同 idempotency_key 重放 deduplicated |
| AO31-CT-003 | RuntimeRun Fact | 完整 RuntimeRun 规范化为 run fact | 缺 run_id/status 返回 `RUNTIME_RUN_INVALID` | attempt_no 支持同 run 多次尝试 |
| AO31-CT-004 | TraceSpan Fact | model/tool/approval/guardrail/artifact span 规范化 | 未登记 span_kind 返回 `TRACE_SPAN_KIND_UNSUPPORTED` | minor version 新字段安全忽略 |
| AO31-CT-005 | Trace Parent Integrity | span tree 父子关系完整，timeline 正常 | parent_span_id 缺失返回 `TRACE_PARENT_MISSING` 并 degraded | 乱序批次可按 sequence/start_time 重建 |
| AO31-CT-006 | Run Detail Projection | blocked/approval_paused/trace_pending 有状态、原因和下一步 | 无权限返回 `RUN_DETAIL_SCOPE_DENIED` | 旧 run 无 TraceSpan 时展示 trace_pending |
| AO31-CT-007 | Trace Timeline Projection | span tree 展示脱敏 input/output refs | 原文权限不足返回脱敏摘要和 `RAW_ACCESS_REQUIRED` | token/cost 新字段缺失时不失败 |
| AO31-CT-008 | State Registry | machine state 映射为统一白话文案和主动作 | 状态展示名冲突返回 `STATE_DISPLAY_MISMATCH` | 新状态必须先登记为 degraded/unknown |

## 8. 成功标准

- **SC-001**：`spec.md`、`research.md`、`data-model.md`、`plan.md`、`tasks.md`、`contracts/contract-tests.md` 均完成并互相可追踪。
- **SC-002**：AO31-CT-001 到 AO31-CT-008 覆盖 AO-P0-01 到 AO-P0-04。
- **SC-003**：Contract / Schema / State / Error Registry 最小字段均有 Owner 和 P0/P1 边界。
- **SC-004**：Runtime Ingestion、Run Detail、Trace Timeline 的字段均能映射到 AgentOps PRD 第 16 章与顶层 PRD 第 14 章。
- **SC-005**：`ai-sdlc gate refine`、`ai-sdlc gate design`、`ai-sdlc gate decompose` 通过，或失败项被归档为明确阻塞。
- **SC-006**：`ai-sdlc run --dry-run` 通过，证明阶段路由和基础门禁仍正常。

## 9. AI 决策与假设

| 编号 | 决策 | 理由 | 风险控制 |
|---|---|---|---|
| AD-031-001 | 将 AO-P0-01 到 AO-P0-04 合并为一个工作项 | 四项存在强依赖：无契约无法安全接入，无接入无法展示 Run/Trace | 后续 AO-P0-05/06 单独拆 Evidence/Health，避免范围膨胀 |
| AD-031-002 | P0 内部模型不直接采用 OTel/OpenInference 作为唯一 schema | 顶层 PRD 明确 P1 才做 exporter，P0 要保持内部事实源稳定 | 保留 trace/span 字段兼容 exporter 所需关键维度 |
| AD-031-003 | 本工作项以契约和投影为优先，不实现完整质量评分 | AgentOps PRD 第 16 章明确 P0 不做完整评分引擎 | HealthSummary 后续单独工作项承接 |
| AD-031-004 | Console 可以先用 mock 数据承接新状态 | 保持前后端并行开发，不阻塞 contract-first 验证 | 所有 mock 字段必须来自 contract，不允许自造语义 |
