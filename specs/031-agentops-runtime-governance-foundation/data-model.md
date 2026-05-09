# 数据模型：AgentOps Runtime Governance Foundation

**工作项**：`031-agentops-runtime-governance-foundation`  
**日期**：2026-05-09  
**阶段**：design / data-model

## 1. 模型总览

```text
ContractRegistryEntry
  -> SchemaDefinition
  -> StateRegistryEntry
  -> ErrorCodeDefinition

RuntimeIngestionBatch
  -> EventEnvelopeFact
  -> RuntimeRunFact
  -> TraceSpanFact
  -> IngestionReceipt

RuntimeRunFact + TraceSpanFact
  -> RunDetailProjection
  -> TraceTimelineProjection
```

AgentOps 只保存 Runtime 上报后的治理事实，不生成 RuntimeRun，不执行 Tool/Model。

## 2. Registry 模型

### 2.1 ContractRegistryEntry

| 字段 | 类型 | 必填 | 说明 |
|---|---|---|---|
| contract_id | string | 是 | 如 `runtime_run.v1`、`trace_span.v1` |
| domain_owner | enum | 是 | AgentOps / Agent Runtime / Agent Store / Ai_AutoSDLC / Contract Registry |
| producer | string | 是 | 事实生产方 |
| consumers | string[] | 是 | 消费方 |
| schema_ref | string | 是 | SchemaDefinition id |
| required_fields | string[] | 是 | P0 必填字段 |
| state_registry_refs | string[] | 否 | 关联状态 |
| error_codes | string[] | 是 | 关联错误码 |
| contract_tests | string[] | 是 | AO31-CT-* |
| compatibility_policy | enum | 是 | additive_minor / breaking_major / no_breaking_in_p0 |
| deprecated_at | datetime/null | 否 | 废弃时间 |

### 2.2 SchemaDefinition

| 字段 | 类型 | 必填 | 说明 |
|---|---|---|---|
| schema_id | string | 是 | schema 标识 |
| schema_version | string | 是 | 语义版本 |
| required_fields | map | 是 | 字段名到类型 |
| optional_fields | map | 否 | 可选字段 |
| enums | map | 否 | 枚举集合 |
| source_prd_refs | string[] | 是 | PRD 段落引用 |

### 2.3 StateRegistryEntry

| 字段 | 类型 | 必填 | 说明 |
|---|---|---|---|
| machine_value | string | 是 | 机器状态 |
| display_name | string | 是 | 展示名 |
| plain_language_explanation | string | 是 | 白话解释 |
| severity | enum | 是 | info / success / warning / critical |
| primary_action | string | 是 | 主动作 |
| secondary_action | string/null | 否 | 次动作 |
| terminal_state | boolean | 是 | 是否终态 |
| allowed_next_states | string[] | 否 | 合法流转 |
| audit_required | boolean | 是 | 是否审计 |
| owner | string | 是 | 状态 owner |

### 2.4 ErrorCodeDefinition

| 字段 | 类型 | 必填 | 说明 |
|---|---|---|---|
| error_code | string | 是 | 错误码 |
| http_status | integer | 是 | HTTP 状态 |
| retryable | boolean | 是 | 是否可重试 |
| user_message | string | 是 | 面向用户解释 |
| developer_message | string | 是 | 面向接入方解释 |
| audit_required | boolean | 是 | 是否审计 |

## 3. Runtime 接入模型

### 3.1 RuntimeIngestionBatch

| 字段 | 类型 | 必填 | 说明 |
|---|---|---|---|
| batch_id | string | 是 | 批次 ID |
| runtime_id | string | 是 | Runtime ID |
| runtime_version | string | 是 | Runtime 版本 |
| schema_version | string | 是 | 接入 schema |
| sent_at | datetime | 是 | Runtime 发送时间 |
| events | EventEnvelopeFact[] | 是 | 事件列表 |
| signature | string/null | 是 | 批次签名或事件级签名 |

### 3.2 EventEnvelopeFact

| 字段 | 类型 | 必填 | 说明 |
|---|---|---|---|
| event_id | string | 是 | 全局唯一事件 ID |
| schema_version | string | 是 | 信封 schema |
| event_type | enum | 是 | runtime_run / trace_span / guardrail_result / artifact_ref / policy_decision |
| event_type_version | string | 是 | 事件类型版本 |
| timestamp | datetime | 是 | 事件时间 |
| sequence_no | integer | 是 | Runtime 局部顺序 |
| idempotency_key | string | 是 | 幂等键 |
| source_trust | enum | 是 | verified / signed / unsigned / suspected |
| signature_state | enum | 是 | valid / missing / invalid / expired / not_required |
| data_classification | enum | 是 | public / internal / confidential / restricted |
| redaction_policy | string | 是 | 脱敏策略 |
| payload_hash | string | 是 | payload hash |
| payload_ref | string/null | 否 | 原文引用 |
| payload | object | 是 | 结构化摘要 payload |

### 3.3 RuntimeRunFact

| 字段 | 类型 | 必填 | 说明 |
|---|---|---|---|
| runtime_id | string | 是 | Runtime ID |
| runtime_version | string | 是 | Runtime 版本 |
| execution_environment | enum | 是 | local / managed / ci / unknown |
| session_id | string | 是 | 会话 |
| run_id | string | 是 | 运行 |
| parent_run_id | string/null | 否 | 父运行 |
| attempt_no | integer | 是 | 尝试次数 |
| agent_id | string | 是 | Agent ID |
| version | string | 是 | Agent 版本 |
| trigger_source | enum | 是 | user / schedule / ci / store / runtime |
| isolation_profile | string | 是 | 隔离策略 |
| policy_bundle_version | string | 否 | 策略版本 |
| status | enum | 是 | created / running / approval_paused / succeeded / failed / timeout / cancelled / blocked |
| terminal_reason | string/null | 否 | 终态原因 |
| created_at | datetime | 是 | 创建时间 |
| updated_at | datetime | 是 | 更新时间 |

### 3.4 TraceSpanFact

| 字段 | 类型 | 必填 | 说明 |
|---|---|---|---|
| trace_id | string | 是 | trace ID |
| span_id | string | 是 | span ID |
| parent_span_id | string/null | 否 | 父 span |
| run_id | string | 是 | 所属 run |
| span_kind | enum | 是 | agent / workflow / model / tool / retrieval / handoff / approval / guardrail / artifact / system |
| operation_name | string | 是 | 操作名 |
| status_code | enum | 是 | ok / error / unset / blocked / waiting |
| start_time | datetime | 是 | 开始 |
| end_time | datetime/null | 否 | 结束 |
| attempt_no | integer | 是 | 尝试次数 |
| input_ref | string/null | 否 | 输入引用 |
| output_ref | string/null | 否 | 输出引用 |
| token_usage | object/null | 否 | token 摘要 |
| cost_estimate | object/null | 否 | 成本摘要 |
| grant_id | string/null | 否 | 授权 ID |
| guardrail_result_refs | string[] | 否 | Guardrail 结果引用 |
| error_code | string/null | 否 | 错误码 |
| retryable | boolean | 是 | 是否可重试 |

### 3.5 IngestionReceipt

| 字段 | 类型 | 必填 | 说明 |
|---|---|---|---|
| batch_id | string | 是 | 批次 ID |
| accepted_count | integer | 是 | 接收数 |
| deduplicated_count | integer | 是 | 去重数 |
| rejected_count | integer | 是 | 拒绝数 |
| dlq_count | integer | 是 | DLQ 数 |
| item_results | object[] | 是 | event_id -> status/error |
| audit_id | string | 是 | 审计 ID |

## 4. Projection 模型

### 4.1 RunDetailProjection

| 字段 | 类型 | 必填 | 说明 |
|---|---|---|---|
| run | RuntimeRunFact | 是 | 运行事实 |
| display_state | StateRegistryEntry | 是 | 用户可见状态 |
| next_action | string | 是 | 下一步 |
| policy_summary | object/null | 否 | PolicyDecision 摘要 |
| approval_summary | object/null | 否 | Approval 摘要 |
| guardrail_summary | object[] | 否 | Guardrail 摘要 |
| artifact_refs | object[] | 否 | Artifact 引用 |
| outbox_state | enum | 是 | delivered / pending / backlog / failed / unknown |
| trace_state | enum | 是 | complete / pending / degraded / missing |
| audit_id | string | 是 | 审计 ID |

### 4.2 TraceTimelineProjection

| 字段 | 类型 | 必填 | 说明 |
|---|---|---|---|
| trace_id | string | 是 | trace ID |
| run_id | string | 是 | run ID |
| spans | object[] | 是 | span tree/list |
| degraded | boolean | 是 | 是否降级 |
| degraded_reason | string/null | 否 | 降级原因 |
| redaction_state | enum | 是 | redacted / summary_only / raw_access_required |
| aggregate | object | 是 | duration、token、cost 摘要 |

## 5. 状态机

### 5.1 RuntimeRun 状态

```text
created -> running
running -> approval_paused
approval_paused -> running
running -> succeeded
running -> failed
running -> timeout
running -> cancelled
running -> blocked
```

非法流转必须记录 audit_id 并返回 `RUNTIME_RUN_STATE_INVALID`。

### 5.2 Trace 状态

```text
missing -> pending -> complete
pending -> degraded
complete -> degraded
degraded -> complete  (仅当补齐缺失 parent/span 并重新校验)
```

## 6. 权限与脱敏

- 默认 projection 不返回 raw payload。
- `input_ref` / `output_ref` 只展示 hash、摘要和 raw_access_state。
- 无权限访问 Run Detail 返回 `RUN_DETAIL_SCOPE_DENIED`，但可包含 request_id、audit_id、denied_scope。
- 无权限访问原文返回 `RAW_ACCESS_REQUIRED`，不得回显未脱敏内容。
