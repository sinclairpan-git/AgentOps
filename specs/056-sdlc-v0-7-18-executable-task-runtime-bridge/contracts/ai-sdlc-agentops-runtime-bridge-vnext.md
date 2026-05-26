# Ai_AutoSDLC -> AgentOps Runtime Bridge vNext Contract

**版本**：`ai-sdlc-agentops-runtime-bridge.vnext`  
**冻结日期**：2026-05-25  
**Producer**：Ai_AutoSDLC Reporter / Outbox  
**Consumer**：AgentOps Runtime Ingestion / Trace / Evidence / Console  
**适用版本**：Ai_AutoSDLC v0.7.18+、AgentOps AO56+

## 1. 责任边界

| 项目 | 责任 | 不负责 |
|---|---|---|
| Ai_AutoSDLC | 生成 executable task、task guard、stage/gate/verification/artifact/violation、outbox batch 和签名摘要事件 | 不判定 AgentOps actual L5，不执行 AgentOps policy，不保存 Store 发布事实 |
| AgentOps | 接收 batch、返回 receipt、写 Trace/Evidence、判定 readiness/L5、展示 Console 只读摘要 | 不执行 SDLC，不触发 Console replay，不伪造 Agent Store installation |
| Agent Store | 分发、安装、激活命令、安装状态和健康摘要回显 | 不作为 SDLC Outbox 运行事实必经中转，不展示完整 Trace |

## 2. 接入路径

### 2.1 Store-mediated activation

用于官方应用安装、设备绑定和 Store 回显。事件可携带 `installation_id`、`device_id`、`signed_installation_assertion_id`。

### 2.2 Ops-direct producer activation

用于 CI、受管 repo、内部平台服务或无 Store 中转的 Reporter。事件携带 `producer_id`、`runtime_id`、`credential_id`、`key_id`、`source_trust`。不得伪造 Agent Store installation。

两条路径最终都直接上报 AgentOps：

```text
Ai_AutoSDLC Reporter / Outbox
  -> POST /v1/runtime/events
  -> runtime_outbox_receipt.v1
  -> Trace / Evidence / Console / Store summary
```

## 3. Batch Envelope

AgentOps sink 使用 `runtime.ingestion.v1`：

```json
{
  "schema_version": "runtime.ingestion.v1",
  "batch_id": "batch_sdlc_001",
  "outbox_id": "outbox_sdlc_001",
  "producer": "Ai_AutoSDLC",
  "replay_reason": "initial_delivery",
  "events": []
}
```

要求：

- `batch_id` 必填且稳定。
- `outbox_id` 必填；同一 outbox replay 使用相同 `outbox_id`。
- `replay_reason` 使用 `initial_delivery`、`network_replay`、`credential_rotation_replay`、`manual_backend_replay` 之一。
- `events[]` 必须按 `sequence_no` 可排序；AgentOps 会按 sequence 处理并拒绝或忽略 stale event。

## 4. Event Envelope

进入 AgentOps 的 enterprise events 使用 canonical `event_envelope.v1`。

必填字段：

| 字段 | 说明 |
|---|---|
| event_id | 全局事件 ID |
| schema_version | `event_envelope.v1` |
| event_type | `sdlc_trace_event` |
| event_type_version | `sdlc_trace_event.v1` |
| timestamp | ISO 8601 |
| integration_mode | `enterprise_managed` |
| enterprise_state | `active` / `degraded` |
| session_id | SDLC session |
| run_id | SDLC run |
| trace_id | Trace ID |
| sequence_no | 单 outbox 局部顺序 |
| idempotency_key | 幂等键 |
| source_trust | `signed_producer` / `verified_runtime` / `degraded` |
| signature_state | `valid` |
| signature | producer signature |
| data_classification | `metadata` / `summary` |
| redaction_policy | 脱敏策略 |
| payload_hash | payload hash |
| payload_ref | summary-only ref |
| payload | SDLC payload |

身份字段二选一：

| 模式 | 必填 |
|---|---|
| Store-mediated | `installation_id`、`device_id`、`credential_id`、`key_id` |
| Ops-direct | `producer_id`、`runtime_id`、`credential_id`、`key_id` |

## 5. SDLC Payload

`payload.sdlc_event_type` 允许：

| sdlc_event_type | TraceSpan 映射 | 必填重点 |
|---|---|---|
| executable_task | system span | `workitem`、`executable_task_id`、`task_title`、`task_guard_state` |
| code_guard | guardrail span | `guard_result`、`changed_paths`、`allowed_paths`、`blocking_reason` |
| stage | workflow span | `stage_name`、`status` |
| gate | guardrail span | `gate_id`、`status` |
| verification | tool/workflow span | `verification_id`、`status`、`artifact_ref` |
| artifact | artifact span | `artifact_ref`、`payload_hash` |
| violation | guardrail span | `violation_code`、`status` |

共同必填字段：

```text
sdlc_event_id
run_id
trace_id
span_id
parent_span_id
attempt_no
sdlc_event_type
stage_name
status
started_at
ended_at
artifact_ref
evidence_ref
violation_code
workitem
executable_task_id
task_guard_state
adapter_diagnostic_state
```

`adapter_diagnostic_state` 只允许作为诊断字段。`verified_loaded` 不得单独推出 run ready、Reporter active、Outbox delivered 或 actual L5。

## 6. Receipt

AgentOps 返回 `runtime_outbox_receipt.v1`：

```json
{
  "schema_version": "runtime_outbox_receipt.v1",
  "batch_id": "batch_sdlc_001",
  "outbox_id": "outbox_sdlc_001",
  "producer": "Ai_AutoSDLC",
  "replay_reason": "initial_delivery",
  "outbox_state": "delivered",
  "accepted_count": 4,
  "deduplicated_count": 0,
  "stale_count": 0,
  "rejected_count": 0,
  "dlq_count": 0,
  "item_results": [],
  "audit_id": "audit_runtime_ingestion_batch_sdlc_001"
}
```

`outbox_state` 允许：

| 状态 | 含义 |
|---|---|
| delivered | 全部接收或可接受处理 |
| replayed | 重放被幂等去重 |
| delivered_with_diagnostics | 存在 stale/rejected/dlq 但有可用事实 |
| rejected | 批次或全部事件被拒绝 |

## 7. Readiness Rules

AgentOps actual L5 / readiness 不得由单一字段推出。最低条件：

1. `executable_task_id` present。
2. `task_guard_state=allowed`。
3. signed event chain valid。
4. receipt `outbox_state in {delivered, delivered_with_diagnostics}`，且 rejected/DLQ 不影响必需事实。
5. stage/gate/verification/artifact/violation scan facts complete。
6. policy / guardrail state known。
7. EvidenceSummary freshness valid。

任何以下情况必须阻断 actual L5：

- missing executable task。
- task guard blocked。
- event signature invalid。
- required SDLC event rejected。
- raw payload exposure.
- adapter diagnostic alone used as proof.

## 8. Console Mapping

`sdlcRunWorkbench` 目标结构：

| Section | 字段 |
|---|---|
| taskGuard | run_id、workitem、executable_task_id、task_guard_state、blocking_reason、candidate_fixes |
| outboxReceipts | outbox_id、outbox_state、accepted/deduplicated/stale/rejected/dlq、audit_id |
| evidenceReadiness | evidence_level、readiness_state、missing_dimensions、freshness、next_action |
| adapterDiagnostics | adapter_diagnostic_state、host_target、detected_host、canonical_path、diagnostic_note |
| guardrails | no raw payload、no Console replay、adapter diagnostic is not main gate |

## 9. Error Codes

| code | 含义 | retryable |
|---|---|---|
| `CODE_CHANGE_TASK_REQUIRED` | 缺 executable task | false |
| `TASK_GUARD_BLOCKED` | task guard 阻断 | false |
| `SDLC_TRACE_EVENT_INVALID` | SDLC payload 或 integration mode 不合法 | false |
| `EVENT_SIGNATURE_INVALID` | 签名无效 | false |
| `EVENT_SCHEMA_UNSUPPORTED` | schema 不支持 | false |
| `TRACE_PARENT_MISSING` | 父 span 缺失 | true |
| `ADAPTER_DIAGNOSTIC_OVERREACH` | adapter diagnostic 被误用为主 proof | false |

## 10. 双边验收

- Ai_AutoSDLC 能生成 sample batch。
- AgentOps 能接收 sample batch 并返回 receipt。
- AgentOps Console 能展示 task guard、receipt、readiness 和 adapter diagnostics。
- `verified_loaded` 单独存在时不能推出 actual L5。
- Store summary 只回显摘要和下一步动作，不展示完整 Trace 或 raw payload。
