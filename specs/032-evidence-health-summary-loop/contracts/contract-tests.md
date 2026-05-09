# 契约测试：AgentOps Evidence and Health Summary Loop

**工作项**：`032-evidence-health-summary-loop`  
**日期**：2026-05-09

## AO32-CT-001 EvidenceSummary 合成

- **正例**：完整 succeeded RuntimeRun + model/tool/guardrail/artifact TraceSpan 生成 `evidence_level=L5`、`confidence=1.0`、`missing_dimensions=[]`。
- **反例**：只有 RuntimeRun、无 TraceSpan 时生成 `evidence_level=L3`、`missing_dimensions` 包含 `trace_span`、`degraded_reason=trace_pending`。
- **覆盖**：AO-P0-05，FR-001 到 FR-003。

## AO32-CT-002 Raw Access Boundary

- **正例**：默认 EvidenceSummary 只返回 hash/ref/summary 字段，`raw_access_state=summary_only`。
- **反例**：请求 raw evidence 且无权限时返回 `RAW_ACCESS_REQUIRED`，包含 audit_id、request_access_url、denied_scope。
- **覆盖**：AO-P0-05，FR-010。

## AO32-CT-003 HealthSummary 聚合

- **正例**：同 agent/version 多个 runtime runs 聚合出 success_rate、failure_rate、policy_block_count、evidence_completeness 和 `recommended_action`。
- **反例**：无样本时 sample_size=0 不除零，返回 `watching` 或 `expired`。
- **覆盖**：AO-P0-06，FR-004 到 FR-006。

## AO32-CT-004 Store Runtime Summary

- **正例**：`GET /v1/store-summary/{agent_id}` 在 runtime facts 存在时返回 evidence_summary、health_summary、recommended_action、ops_detail_url。
- **反例**：请求 agent_id/version 与 run fact 不匹配时返回 `STORE_SUMMARY_RUN_MISMATCH`。
- **覆盖**：AO-P0-11，FR-007、FR-008。

## AO32-CT-005 Expiry Semantics

- **正例**：新鲜摘要按 HealthSummary recommended_action 回显。
- **反例**：valid_until 已过期时 Store summary 返回 `recommended_action=expired`、`summary_state=expired`。
- **覆盖**：AO-P0-11，FR-009。

## AO32-CT-006 P0 End-to-End Acceptance

- **正例**：Runtime ingestion 写入 run/span 后，Run Detail、Trace Timeline、EvidenceSummary、Store Summary 均引用同一 run_id/agent_id/version。
- **反例**：Store summary 序列化结果不包含 raw payload、prompt、token secret、credential secret、device key。
- **覆盖**：AO-P0-13，FR-011、FR-012。

## 回归要求

- AO22 Store Summary HTTP Contract 必须继续通过。
- AO31 Runtime Governance Foundation contract tests 必须继续通过。
- 新增字段必须 additive，不得删除 AO22/031 已声明字段。
