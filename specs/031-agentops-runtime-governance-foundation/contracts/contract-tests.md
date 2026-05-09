# Contract Tests：AO31 Runtime Governance Foundation

**工作项**：`031-agentops-runtime-governance-foundation`  
**日期**：2026-05-09

## AO31-CT-001 Contract Registry

- **正例**：`RuntimeRun`、`TraceSpan`、`EventEnvelope`、`PolicyDecision`、`CapabilityGrant`、`Approval`、`EvidenceSummary`、`HealthSummary` 均包含 Domain Owner、Producer、Consumer、required fields、state refs、error codes、contract test id。
- **反例**：缺 Domain Owner 返回 `CONTRACT_OWNER_REQUIRED`；未知 Producer/Consumer 返回 `CONTRACT_PARTY_UNREGISTERED`。
- **幂等**：重复加载 registry 返回稳定 hash。
- **兼容**：新增 optional field 不改变 required field 校验。

## AO31-CT-002 Runtime Ingestion Batch

- **正例**：有效批次包含 RuntimeRun + TraceSpan，schema/signature/idempotency/sequence 校验通过，返回 accepted。
- **反例**：schema_version 不支持返回 `EVENT_SCHEMA_UNSUPPORTED`；签名无效返回 `EVENT_SIGNATURE_INVALID`。
- **幂等**：同 idempotency_key 重放返回 deduplicated，不重复写 run/span fact。
- **兼容**：event_type_version minor 新字段可安全忽略。

## AO31-CT-003 RuntimeRun Fact

- **正例**：完整 RuntimeRun 规范化为 `RuntimeRunFact`。
- **反例**：缺 `run_id` 或 `status` 返回 `RUNTIME_RUN_INVALID`；非法状态流转返回 `RUNTIME_RUN_STATE_INVALID`。
- **幂等**：同 run_id + attempt_no 重放不创建重复 attempt。
- **兼容**：未知 `execution_environment` 降级为 unknown，不影响必填字段校验。

## AO31-CT-004 TraceSpan Fact

- **正例**：model/tool/approval/guardrail/artifact span 规范化为 `TraceSpanFact`。
- **反例**：未登记 `span_kind` 返回 `TRACE_SPAN_KIND_UNSUPPORTED`；缺 span_id 返回 `TRACE_SPAN_INVALID`。
- **幂等**：同 trace_id + span_id 重放返回 deduplicated。
- **兼容**：缺 token_usage/cost_estimate 不失败。

## AO31-CT-005 Trace Parent Integrity

- **正例**：span parent-child 完整，timeline 状态为 complete。
- **反例**：parent_span_id 指向不存在 span 返回 `TRACE_PARENT_MISSING`，timeline 状态为 degraded。
- **幂等**：乱序批次可按 sequence_no/start_time 重建。
- **兼容**：后续补齐 parent 后可从 degraded 恢复 complete。

## AO31-CT-006 Run Detail Projection

- **正例**：blocked/approval_paused/trace_pending run 均返回 display_state、next_action、audit_id。
- **反例**：无权限返回 `RUN_DETAIL_SCOPE_DENIED`，且只返回 request_id、audit_id、denied_scope、request_access_url。
- **幂等**：同 run 输入返回稳定 projection hash。
- **兼容**：旧 run 无 TraceSpan 时展示 `trace_pending`，不返回空白成功态。

## AO31-CT-007 Trace Timeline Projection

- **正例**：span tree 展示 span_kind、duration、status、input_ref/output_ref、error_code 和降级原因。
- **反例**：请求 raw input/output 但无权限返回 `RAW_ACCESS_REQUIRED`，不泄露原文。
- **幂等**：同 trace 输入返回稳定排序。
- **兼容**：token/cost 字段缺失时 aggregate 显示 unknown，不失败。

## AO31-CT-008 State Registry

- **正例**：`running`、`approval_paused`、`succeeded`、`failed`、`cancelled`、`timeout`、`blocked`、`trace_pending`、`degraded` 均有白话解释和主动作。
- **反例**：同 machine_value 出现不同 display_name 返回 `STATE_DISPLAY_MISMATCH`。
- **幂等**：重复加载 State Registry 返回稳定 hash。
- **兼容**：新增状态必须先登记为 warning/degraded/unknown，不能直接默认 success。
