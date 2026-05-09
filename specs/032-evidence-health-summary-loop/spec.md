# 功能规格：AgentOps Evidence and Health Summary Loop

**功能编号**：`032-evidence-health-summary-loop`  
**创建日期**：2026-05-09  
**状态**：待执行  
**工作项分类**：`new_requirement`  
**继承 baseline_id**：`agent-platform-baseline-2026-05-v1.4.2`  
**项目 Owner**：AgentOps Owner  
**契约 Owner**：AgentOps 维护 `EvidenceSummary`、`HealthSummary` 和 Store 回显摘要；Agent Runtime 继续维护 RuntimeRun / TraceSpan 事实；Agent Store 只消费摘要和 deep link，不读取原文、不推导治理态。  
**需求来源**：`specs/031-agentops-runtime-governance-foundation/agentops-p0-p2-backlog.md` 中 AO-P0-05、AO-P0-06、AO-P0-11、AO-P0-13。

## 1. 目标与边界

### 1.1 项目目标

本工作项承接 AO31 之后的第二组 AgentOps P0 拆分需求：

1. **AO-P0-05 EvidenceSummary 合成**：基于 AO31 的 RuntimeRun / TraceSpan 事实，输出 `evidence_level`、`source_event_ids`、`freshness`、`valid_until`、`confidence`、`missing_dimensions`、`redaction_state`、`raw_access_state`、`degraded_reason`。
2. **AO-P0-06 HealthSummary 生成与 Store 回写**：按 agent/version/window 计算 `success_rate`、`failure_rate`、`evidence_completeness`、`policy_block_count`、`recommended_action`、`valid_until`。
3. **AO-P0-11 Agent Store 回显接口**：向 Store 提供 EvidenceSummary、HealthSummary、recommended_action、ops_detail_url；摘要过期后必须返回 expired。
4. **AO-P0-13 P0 端到端验收**：串起 Runtime 上报 -> Ops Run Detail/Timeline -> Evidence/Health Summary -> Store 回显。

阶段完成后，AgentOps 必须能证明一条最小摘要闭环：

```text
Runtime 上报 RuntimeRun + TraceSpan
  -> AgentOps 生成 Run Detail / Trace Timeline
  -> AgentOps 合成 EvidenceSummary / HealthSummary
  -> Agent Store 通过 display-only 摘要回显健康和证据状态
```

### 1.2 本期范围

- 新增 `EvidenceSummaryProjection`，从 AO31 runtime facts 派生证据等级、完整度、新鲜度、脱敏状态和降级原因。
- 新增 `HealthSummaryProjection`，按 agent/version 的最近窗口聚合成功率、失败率、证据完整度、策略阻断数和推荐动作。
- 新增 Store Runtime Governance Summary API：保留既有 `/v1/store-summary/{agent_id}`，当 repository 存在 runtime facts 时优先使用 AO32 摘要，兼容 AO22 的 SDLC audit event 摘要。
- 新增 `ops_detail_url`、`evidence_summary`、`health_summary` 和 `expired` 语义，供 Agent Store 只展示和跳转。
- 新增 AO32-CT-001 到 AO32-CT-006 可运行 contract tests。

### 1.3 本期不做

- 不实现复杂质量评分、ROI、采纳分析、prompt optimizer。
- 不实现完整 Approval Center、Policy 管理台、Grant 生命周期；这些属于 AO33/P1。
- 不新增 Runtime 执行、调度、包加载或 Tool/Model 调用。
- 不把 Agent Store 改造成治理事实源；Store 仍只消费 AgentOps 摘要，不反推 active/verified_loaded。
- 不实现生产级跨服务回写队列；P0 使用 API contract 和 repository projection 证明语义。

## 2. 用户场景与测试

### 用户故事 1 - 管理员查看运行证据摘要（P0）

作为 AgentOps 管理员，我希望每个 runtime run 都能生成证据摘要，以便不用打开原文也能判断证据是否完整、新鲜、可信、可回溯。

**独立测试**：导入成功 run 和 model/tool/guardrail/artifact span，调用 EvidenceSummary API，验证证据等级、source_event_ids、missing_dimensions、redaction_state 和 raw_access_state。

**验收场景**：

场景 1: 完整 runtime trace 生成高可信摘要  
- **Given** run 已成功且包含 model/tool/guardrail/artifact span，**When** 查询 EvidenceSummary，**Then** 返回 `evidence_level=L5`、`confidence=1.0`、`missing_dimensions=[]`。

场景 2: 缺少 trace 时摘要降级  
- **Given** run 只有 RuntimeRun 事实但没有 TraceSpan，**When** 查询 EvidenceSummary，**Then** 返回 `evidence_level=L3`、`missing_dimensions` 包含 `trace_span`，并给出 `degraded_reason=trace_pending`。

场景 3: 请求原文时必须走 Evidence Vault  
- **Given** 用户只拥有摘要权限，**When** 请求 raw evidence，**Then** 返回 `RAW_ACCESS_REQUIRED`，并包含 audit_id、request_access_url 和 denied_scope。

### 用户故事 2 - Store 消费健康摘要（P0）

作为 Agent Store，我希望通过一个 display-only 接口读取 AgentOps 生成的 EvidenceSummary 和 HealthSummary，以便在详情页提示 Agent 版本是否可用、是否需谨慎使用或建议禁用。

**独立测试**：为同一 agent/version 导入多个 succeeded/failed/blocked run，调用 `/v1/store-summary/{agent_id}`，验证 summary 中包含 health_summary、recommended_action、ops_detail_url 且不包含原文。

**验收场景**：

场景 1: 健康版本返回 usable  
- **Given** 最近窗口内 run 均成功且证据完整，**When** Store 查询 summary，**Then** 返回 `recommended_action=usable`、`success_rate=1.0`。

场景 2: 阻断或失败过多返回谨慎/禁用建议  
- **Given** 最近窗口内存在策略阻断或失败 run，**When** Store 查询 summary，**Then** 返回 `use_with_caution` 或 `disable_recommended`，并带 policy_block_count/failure_rate。

场景 3: 摘要过期必须返回 expired  
- **Given** Store 请求时摘要 `valid_until` 已过期，**When** 查询 summary，**Then** 返回 `recommended_action=expired` 且不声称当前健康。

### 用户故事 3 - P0 端到端验收（P0）

作为平台 Owner，我希望用一个 contract test 串起 Runtime 上报、Ops 投影、证据/健康摘要、Store 回显，以便确认 P0 治理闭环不是几个孤立接口。

**独立测试**：测试内通过 Runtime Ingestion 写入 run/span，再调用 Run Detail、Trace Timeline、EvidenceSummary、Store Summary，验证同一 run_id/agent_id/version 的链路一致。

**验收场景**：

场景 1: 同一 run_id 贯穿全部投影  
- **Given** Runtime 上报 `run_1`，**When** 查询四个投影，**Then** 所有响应均引用 `run_1`，且 Store deep link 指向 AgentOps run detail。

场景 2: Store 不能读取 raw payload  
- **Given** span input/output 只有 hash/ref，**When** Store 查询 summary，**Then** 响应不包含 prompt、raw payload、token secret 或 device key。

## 3. 边界情况

- run 不存在时返回 `RUNTIME_RUN_NOT_FOUND` 或 `RUN_NOT_FOUND`，不得返回空健康。
- agent_id/version 与 run fact 不匹配时返回 `STORE_SUMMARY_RUN_MISMATCH`。
- TraceSpan 缺失时 EvidenceSummary 降级，不伪装为 L5。
- HealthSummary sample_size 为 0 时必须返回 `recommended_action=expired` 或 `watching`，不得除零。
- valid_until 已过期时 Store 回显必须覆盖为 `expired`。
- 原文访问默认禁止，raw evidence 只能通过 Evidence Vault 申请。
- Store summary 只能展示 AgentOps fact owner、display-only boundary 和 deep links，不得暴露 Runtime 原文。

## 4. 功能需求

- **FR-001**：系统必须提供 `build_runtime_evidence_summary`，基于 runtime run + trace spans 生成 `evidence_summary.v1`。
- **FR-002**：EvidenceSummary 必须包含 run_id、trace_id、evidence_level、source_event_ids、freshness、valid_until、confidence、missing_dimensions、redaction_state、raw_access_state、degraded_reason。
- **FR-003**：EvidenceSummary 完整度必须至少检查 RuntimeRun、TraceSpan、model/tool/guardrail/artifact span、terminal status 和 source_event_ids。
- **FR-004**：系统必须提供 `build_runtime_health_summary`，按 agent_id/version 聚合最近窗口 runtime runs。
- **FR-005**：HealthSummary 必须包含 health_template_id、calculation_window、sample_size、success_rate、failure_rate、evidence_completeness、policy_block_count、confidence、valid_until、recommended_action、appeal_state。
- **FR-006**：recommended_action 必须映射为 `usable / watching / use_with_caution / disable_recommended / expired` 之一。
- **FR-007**：Store summary 在存在 runtime facts 时必须返回 AO32 的 evidence_summary 和 health_summary，并保留 AO22 display-only consumer boundary。
- **FR-008**：Store summary 必须提供 `ops_detail_url`，指向 AgentOps Run Detail，不得指向 Runtime 执行入口。
- **FR-009**：Store summary 在摘要过期时必须返回 `recommended_action=expired`，不得展示 usable。
- **FR-010**：请求 raw evidence 时必须返回 `RAW_ACCESS_REQUIRED` 和 request_access_url，不得返回原文。
- **FR-011**：AO32 必须提供端到端 contract test，覆盖 Runtime ingestion -> Run Detail -> Trace Timeline -> EvidenceSummary -> Store Summary。
- **FR-012**：本工作项必须保持 AO22、AO31 既有 contract tests 兼容。

## 5. 非功能需求

- **NFR-001 可追踪性**：每个 AO32 test id 必须映射到 AO-P0-05/06/11/13。
- **NFR-002 安全与隐私**：summary 不包含 prompt、raw payload、credential token、device key、secret。
- **NFR-003 兼容性**：不得破坏既有 `/v1/store-summary/{agent_id}` 消费者；runtime facts 为空时沿用 AO22 逻辑。
- **NFR-004 可验证性**：Evidence/Health 逻辑必须通过 contract tests，而不是仅在 Console mock 中存在。
- **NFR-005 边界清晰**：AgentOps 不执行 Runtime、不加载 Agent Store 包、不生成 RuntimeRun。

## 6. 关键实体

- **RuntimeEvidenceSummary**：从 Run Detail / Trace Timeline 派生的证据摘要。
- **RuntimeHealthSummary**：按 agent/version/window 聚合的健康摘要。
- **StoreRuntimeGovernanceSummary**：Agent Store 可消费的 display-only 摘要，包含 EvidenceSummary、HealthSummary、recommended_action、ops_detail_url。
- **SummaryValidity**：valid_until、expired、freshness 和 recommended_action 的统一语义。

## 7. 契约测试矩阵

| test_id | 契约 | 正例 | 反例/错误码 | 覆盖需求 |
|---|---|---|---|---|
| AO32-CT-001 | EvidenceSummary | 完整 succeeded run 生成 L5 | 缺 trace 降级 L3/trace_pending | AO-P0-05 |
| AO32-CT-002 | Raw Access Boundary | summary_only 返回安全字段 | raw 请求返回 RAW_ACCESS_REQUIRED | AO-P0-05/12 |
| AO32-CT-003 | HealthSummary | 多 run 聚合 success/failure/block | sample_size=0 不除零 | AO-P0-06 |
| AO32-CT-004 | Store Runtime Summary | Store 回显 evidence/health/action/link | run target mismatch 拒绝 | AO-P0-11 |
| AO32-CT-005 | Expiry Semantics | 新鲜摘要可用 | 过期摘要返回 expired | AO-P0-11 |
| AO32-CT-006 | P0 E2E | ingestion 到 Store summary 链路一致 | Store 不泄露 raw/secrets | AO-P0-13 |

## 8. 成功标准

- **SC-001**：`spec.md`、`research.md`、`data-model.md`、`plan.md`、`tasks.md`、`contracts/contract-tests.md` 完成且互相可追踪。
- **SC-002**：AO32-CT-001 到 AO32-CT-006 均转化为可运行 contract tests。
- **SC-003**：Runtime facts 存在时 `/v1/store-summary/{agent_id}` 返回 evidence_summary、health_summary、recommended_action、ops_detail_url。
- **SC-004**：缺 trace、raw access、过期摘要和 run mismatch 均有可解释错误或降级状态。
- **SC-005**：AO22/AO31 contract tests 继续通过。
- **SC-006**：`ai-sdlc verify constraints` 与 `ai-sdlc run --dry-run` 通过。

## 9. AI 决策与假设

| 编号 | 决策 | 理由 | 风险控制 |
|---|---|---|---|
| AD-032-001 | 032 优先做 Evidence/Health/Store 回显，不提前做 Policy/Grant/Approval 控制 | Backlog 明确 032 承接 AO-P0-05/06/11/13，AO33 再做最小策略授权审批 | contract tests 限定为 summary loop，不引入执行控制 |
| AD-032-002 | Store summary 在 runtime facts 存在时优先走 AO32，legacy SDLC audit event 继续兼容 | AO22 已有 Store contract，不能破坏旧消费者 | 保留 `get_agent_store_summary_for_run` 的 fallback 逻辑 |
| AD-032-003 | P0 HealthSummary 先用可解释阈值，不引入复杂评分引擎 | P0 目标是可验证治理闭环，不是质量平台 | P2 再做完整质量评分引擎 |
