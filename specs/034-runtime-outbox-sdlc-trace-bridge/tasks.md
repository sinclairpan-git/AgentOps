---
related_doc:
  - "specs/031-agentops-runtime-governance-foundation/agentops-p0-p2-backlog.md"
  - "specs/031-agentops-runtime-governance-foundation/spec.md"
  - "specs/032-evidence-health-summary-loop/spec.md"
  - "specs/033-policy-grant-approval-minimum-control/spec.md"
---
# 任务分解：Runtime Outbox and SDLC Trace Bridge

**编号**：`034-runtime-outbox-sdlc-trace-bridge` | **日期**：2026-05-09
**来源**：plan.md + spec.md

---

## 分批策略

```text
Batch 1: AO34 formal baseline + Runtime outbox receipt
Batch 2: rejection diagnostics + stale sequence semantics
Batch 3: Ai_AutoSDLC trace bridge
Batch 4: verification, archive, PR close-out
```

---

## Batch 1：AO34 formal baseline + Runtime outbox receipt

### Task 1.1 冻结 AO34 formal docs

- **任务编号**：T11
- **优先级**：P0
- **依赖**：031 backlog、031/032/033 runtime specs
- **文件**：spec.md, plan.md, tasks.md, task-execution-log.md, program-manifest.yaml
- **可并行**：否
- **验收标准**：
  1. spec/plan/tasks 明确承接 AO-P0-10 和 AO-P0-14
  2. 明确 AgentOps 不执行 Runtime、不读取 raw payload、不把 receipt 成功提升为治理激活
  3. program manifest source inventory 完整映射
- **验证**：`ai-sdlc program truth sync --execute --yes`、`uv run ai-sdlc verify constraints`

### Task 1.2 登记并返回 RuntimeOutboxReceipt

- **任务编号**：T12
- **优先级**：P0
- **依赖**：T11
- **文件**：src/agentops/core/runtime_contracts.py, src/agentops/core/runtime_ingestion.py, tests/contract/test_ao34_ct_runtime_outbox_sdlc_trace_bridge.py
- **可并行**：否
- **验收标准**：
  1. Contract Registry 登记 `runtime_outbox_receipt.v1`
  2. receipt 返回 outbox_id、producer、accepted/deduplicated/stale/rejected/dlq 计数
  3. 完全相同 outbox replay 返回 `deduplicated`
- **验证**：`uv run pytest tests/contract/test_ao34_ct_runtime_outbox_sdlc_trace_bridge.py -q`

## Batch 2：rejection diagnostics + stale sequence semantics

### Task 2.1 实现 stale ignored 语义

- **任务编号**：T21
- **优先级**：P0
- **依赖**：T12
- **文件**：src/agentops/storage/repository.py, src/agentops/core/runtime_ingestion.py
- **可并行**：否
- **验收标准**：
  1. 较旧 run/attempt sequence 不覆盖较新 run fact
  2. 较旧 trace span 和 guardrail result 不覆盖较新事实
  3. item result 返回 `stale_ignored`，后续同一事件重放变为 `deduplicated`
- **验证**：AO34 stale tests + AO31 latest sequence regression

### Task 2.2 持久化拒绝诊断但隔离 raw payload

- **任务编号**：T22
- **优先级**：P0
- **依赖**：T12
- **文件**：src/agentops/storage/repository.py, src/agentops/core/runtime_ingestion.py
- **可并行**：否
- **验收标准**：
  1. signature/schema/idempotency rejections 写入 summary-only diagnostic
  2. diagnostic 不包含 payload/raw_payload/input/output 原文
  3. DLQ 仍保留 retryable 语义
- **验证**：AO34 diagnostic tests

## Batch 3：Ai_AutoSDLC trace bridge

### Task 3.1 登记并校验 SdlcTraceEvent

- **任务编号**：T31
- **优先级**：P0
- **依赖**：T21-T22
- **文件**：src/agentops/core/runtime_contracts.py, src/agentops/core/runtime_ingestion.py
- **可并行**：否
- **验收标准**：
  1. Contract Registry 登记 `sdlc_trace_event.v1`
  2. 支持 stage/gate/verification/artifact/violation 五种 event type
  3. 只接受 canonical `event_envelope.v1` + `integration_mode=enterprise_managed`
- **验证**：AO34 SDLC contract tests

### Task 3.2 映射为 TraceSpan / Evidence 输入

- **任务编号**：T32
- **优先级**：P0
- **依赖**：T31
- **文件**：src/agentops/core/runtime_ingestion.py, src/agentops/api/view_models.py, src/agentops/core/runtime_summary.py
- **可并行**：否
- **验收标准**：
  1. SDLC stage/gate/verification/artifact/violation 写入 summary-only TraceSpan
  2. artifact/verification/violation 使用 ref/hash/error_code，不返回 raw payload
  3. EvidenceSummary 可消费映射 span 并保持降级口径
- **验证**：AO34 bridge tests + AO32 EvidenceSummary regression

## Batch 4：verification, archive, PR close-out

### Task 4.1 验证、归档、提交和 PR

- **任务编号**：T41
- **优先级**：P0
- **依赖**：T11-T32
- **文件**：task-execution-log.md, development-summary.md, program-manifest.yaml
- **可并行**：否
- **验收标准**：
  1. AO34 + AO31/AO32/AO33 定向回归通过
  2. ruff、format check、AI-SDLC constraints、workitem close-check 通过
  3. PR 创建后触发 @codex review 和 5 分钟 heartbeat
- **验证**：收口命令集合
