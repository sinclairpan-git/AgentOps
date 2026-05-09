# 数据模型：AgentOps Evidence and Health Summary Loop

**工作项**：`032-evidence-health-summary-loop`  
**日期**：2026-05-09

## RuntimeEvidenceSummary

| 字段 | 类型 | 必填 | 说明 |
|---|---|---|---|
| schema_version | string | 是 | 固定 `evidence_summary.v1` |
| run_id | string | 是 | Runtime run id |
| trace_id | string | 是 | Trace id，缺 trace 时为空字符串 |
| evidence_level | enum | 是 | `L3 / L4 / L5` |
| source_event_ids | list[string] | 是 | RuntimeRun / TraceSpan 的 event_id |
| freshness | enum | 是 | `fresh / stale / expired` |
| calculated_at | string | 是 | ISO timestamp |
| valid_until | string | 是 | ISO timestamp |
| confidence | number | 是 | 0.0 到 1.0 |
| completeness | number | 是 | 0.0 到 1.0 |
| missing_dimensions | list[string] | 是 | 缺失维度 |
| redaction_state | enum | 是 | `summary_only / redacted / raw` |
| raw_access_state | enum | 是 | `summary_only / pending_approval / approved_limited / denied` |
| degraded_reason | string/null | 是 | `trace_pending`、`missing_span_dimensions` 等 |
| request_access_url | string | 是 | Evidence Vault 申请入口 |

## RuntimeHealthSummary

| 字段 | 类型 | 必填 | 说明 |
|---|---|---|---|
| schema_version | string | 是 | 固定 `health_summary.v1` |
| agent_id | string | 是 | Agent id |
| version | string | 是 | Agent version |
| health_template_id | string | 是 | P0 固定模板 |
| calculation_window | object | 是 | limit、run_ids |
| sample_size | int | 是 | 样本数量 |
| success_rate | number | 是 | 成功率 |
| failure_rate | number | 是 | 失败率 |
| evidence_completeness | number | 是 | 证据完整度均值 |
| policy_block_count | int | 是 | 策略阻断数量 |
| confidence | number | 是 | 健康结论置信度 |
| calculated_at | string | 是 | ISO timestamp |
| valid_until | string | 是 | ISO timestamp |
| recommended_action | enum | 是 | `usable / watching / use_with_caution / disable_recommended / expired` |
| appeal_state | enum | 是 | P0 固定 `none` |

## StoreRuntimeGovernanceSummary

AO32 不替换 AO22 echo contract，而是在 AO22 响应上追加 runtime governance 摘要：

| 字段 | 类型 | 必填 | 说明 |
|---|---|---|---|
| evidence_summary | RuntimeEvidenceSummary | runtime facts 存在时是 | 单 run 证据摘要 |
| health_summary | RuntimeHealthSummary | runtime facts 存在时是 | agent/version 健康摘要 |
| recommended_action | string | 是 | Store 可展示的最终动作 |
| ops_detail_url | string | 是 | AgentOps run detail deep link |
| summary_state | enum | 是 | `fresh / degraded / expired` |

## 状态与错误码

| 名称 | 类型 | 说明 |
|---|---|---|
| `RAW_ACCESS_REQUIRED` | error | 原文访问必须走 Evidence Vault |
| `EVIDENCE_SUMMARY_EXPIRED` | error/state | 摘要过期 |
| `HEALTH_SUMMARY_EXPIRED` | error/state | 健康摘要过期 |
| `STORE_SUMMARY_RUN_MISMATCH` | error | 请求 agent/version 与 run fact 不一致 |
| `RUNTIME_RUN_NOT_FOUND` | error | run fact 不存在 |

## 兼容性

- `get_agent_store_summary_for_run` 先查 runtime run fact；存在则走 AO32。
- runtime run fact 不存在时保留 AO22 audit event 路径。
- `build_agent_store_echo_summary` 的 display-only boundary 不被删除或弱化。
