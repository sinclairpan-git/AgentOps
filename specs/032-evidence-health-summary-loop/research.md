# 技术研究：AgentOps Evidence and Health Summary Loop

**工作项**：`032-evidence-health-summary-loop`  
**日期**：2026-05-09

## 1. 背景结论

AO31 已提供 runtime facts、Run Detail 和 Trace Timeline。032 不再重新设计 Runtime 执行层，而是在 AgentOps 内做可验证的治理摘要：

- EvidenceSummary 证明单次 run 的证据是否完整、可信、新鲜、可脱敏展示。
- HealthSummary 证明某个 agent/version 在最近窗口内是否适合继续被 Store 推荐使用。
- Store 只能消费 display-only summary 和 deep link，不能读取 raw evidence，也不能把展示状态提升为治理事实。

## 2. 方案比较

| 方案 | 优点 | 风险 | 决策 |
|---|---|---|---|
| 在 `/v1/store-summary/{agent_id}` 内直接增强 runtime 摘要 | 兼容 AO22，Store 不需要换入口；P0 易验收 | route 内需区分 legacy audit events 与 runtime facts | 采用 |
| 新增 `/v1/runtime/summaries/{run_id}` 再由 Store 二次调用 | 边界清楚 | P0 多入口、多联调，容易偏离 Store contract | 暂不采用 |
| HealthSummary 引入复杂质量分 | 更接近长期 AgentOps 平台 | P0 证据不足，容易过拟合 | 暂不采用，P2 再做 |
| 摘要持久化落库 | 生产更稳 | 当前 repository 仍是 P0 in-memory，持久化不是本期主目标 | 暂不采用，先做纯投影 |

## 3. EvidenceSummary 规则

P0 采用可解释规则：

- 有 RuntimeRun + TraceSpan，且至少包含 model/tool/guardrail/artifact 中的关键 span，终态为 succeeded 时为 `L5`。
- 有 RuntimeRun 但缺 TraceSpan 时为 `L3`，`degraded_reason=trace_pending`。
- 有 RuntimeRun + 部分 TraceSpan 但缺关键维度时为 `L4`，`missing_dimensions` 列出缺失项。
- failed/blocked run 可有完整证据，但 confidence 会下降，HealthSummary 负责表达风险。

## 4. HealthSummary 规则

P0 按最近 20 条同 agent/version runtime run 聚合：

- `success_rate = succeeded / sample_size`
- `failure_rate = failed|timeout / sample_size`
- `policy_block_count = blocked 数量`
- `evidence_completeness = evidence 完整度均值`
- `recommended_action`：
  - sample_size=0：`watching`
  - 过期：`expired`
  - policy_block_count > 0 或 failure_rate >= 0.5：`disable_recommended`
  - failure_rate > 0 或 evidence_completeness < 0.8：`use_with_caution`
  - 其他：`usable`

## 5. Store 消费边界

Store summary 必须继续声明：

- `agentops_fact_owner=AgentOps`
- `registry_fact_owner=Agent Store`
- `agent_store_consumer_boundary.mode=display_only`
- 禁止动作包含 `infer_active`、`infer_verified_loaded`、`read_raw_evidence`

AO32 只在响应中新增 `evidence_summary`、`health_summary`、`recommended_action`、`ops_detail_url`，不改变 Store 的事实源边界。

## 6. 风险与控制

| 风险 | 控制 |
|---|---|
| Store summary legacy AO22 contract 被破坏 | runtime facts 不存在时回落 AO22 逻辑，并跑 AO22 回归 |
| 缺 trace 被误判健康 | EvidenceSummary 明确 `trace_pending`，HealthSummary 以完整度参与 recommended_action |
| raw payload 泄露到 Store | AO32-CT-002/006 序列化扫描 raw/secrets |
| 过期摘要继续显示 usable | AO32-CT-005 强制 expired 覆盖 |
