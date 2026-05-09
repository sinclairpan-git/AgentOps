---
related_doc:
  - "specs/031-agentops-runtime-governance-foundation/agentops-p0-p2-backlog.md"
  - "specs/031-agentops-runtime-governance-foundation/spec.md"
  - "specs/032-evidence-health-summary-loop/spec.md"
  - "specs/033-policy-grant-approval-minimum-control/spec.md"
---
# 实施计划：Runtime Outbox and SDLC Trace Bridge

**编号**：`034-runtime-outbox-sdlc-trace-bridge` | **日期**：2026-05-09 | **规格**：specs/034-runtime-outbox-sdlc-trace-bridge/spec.md

## 概述

AO34 承接 P0 backlog 的 outbox 可靠接收和 Ai_AutoSDLC trace bridge。实现目标是让 Runtime / Reporter 的重复、乱序、拒绝和 DLQ 路径都有稳定 receipt 与诊断，同时让 Ai_AutoSDLC 的 stage/gate/verification/artifact/violation 摘要进入 AgentOps 既有 Runtime TraceSpan、Run Detail、Trace Timeline 和 EvidenceSummary 口径。

## 技术背景

**语言/版本**：Python 3.11+  
**主要依赖**：标准库、pytest、ruff、AI-SDLC CLI  
**存储**：`InMemoryRepository` 作为 P0 contract repository；不引入外部 DB  
**测试**：pytest contract tests + AO31/AO32/AO33 回归 + ruff + AI-SDLC constraints  
**目标平台**：macOS / Linux / Windows，保持 GitHub Compatibility Gate 口径  
**约束**：不读取 raw payload；不执行 Agent；不替代 Ai_AutoSDLC stage/gate 结果；不把 dry-run 或 receipt 成功提升为 `verified_loaded`

## 宪章检查

| 宪章门禁 | 计划响应 |
|----------|----------|
| Contract-first | 先冻结 AO34 spec/plan/tasks，再新增 AO34 contract tests。 |
| Source truth | 所有新工作项文档位于 `specs/034-runtime-outbox-sdlc-trace-bridge/` 并同步 program manifest。 |
| Runtime boundary | AgentOps 只接收和投影 Runtime / Ai_AutoSDLC 事实，不执行 Runtime 或 Agent。 |
| Evidence safety | 所有 receipt、diagnostic、TraceSpan 和 EvidenceSummary 只包含引用、hash、状态和错误码。 |
| Compatibility | AO31/AO32/AO33 contract tests 必须继续通过。 |

## 项目结构

### 文档结构

```text
specs/034-runtime-outbox-sdlc-trace-bridge/
├── spec.md
├── plan.md
├── tasks.md
└── task-execution-log.md
```

### 源码结构

```text
src/agentops/core/runtime_contracts.py      # runtime_outbox_receipt.v1 / sdlc_trace_event.v1 registry
src/agentops/core/runtime_ingestion.py      # outbox receipt, stale handling, diagnostics, SDLC mapping
src/agentops/storage/repository.py          # stale-aware writes and summary-only diagnostics
src/agentops/api/server.py                  # HTTP 202 for accepted/dedup/stale/dlq outbox results
tests/contract/test_ao34_ct_runtime_outbox_sdlc_trace_bridge.py
```

## 阶段计划

### Phase 0：Formal truth freeze

**目标**：将 AO34 范围、非目标、验收场景和分批任务从模板替换为真实业务规格。  
**产物**：spec.md / plan.md / tasks.md / task-execution-log.md / program-manifest.yaml  
**验证方式**：`ai-sdlc program truth sync --execute --yes`、`uv run ai-sdlc verify constraints`  
**回退方式**：仅回退 AO34 新工作项文档和 manifest 条目。

### Phase 1：Runtime outbox receipt and diagnostics

**目标**：补齐 receipt contract、dedup、stale ignored、signature/schema/idempotency diagnostic。  
**产物**：runtime contract registry、runtime ingestion、repository diagnostic、AO34 outbox tests。  
**验证方式**：`uv run pytest tests/contract/test_ao34_ct_runtime_outbox_sdlc_trace_bridge.py -q`  
**回退方式**：回退 AO34 新 contract 和 ingestion 分支，不影响 AO31 基础 ingestion。

### Phase 2：Ai_AutoSDLC trace bridge

**目标**：登记并接收 `sdlc_trace_event.v1`，仅在 canonical enterprise_managed envelope 下映射为 TraceSpan / Evidence 输入。  
**产物**：SDLC contract、event mapping、projection/evidence regression tests。  
**验证方式**：AO34 + AO31/AO32/AO33 定向回归。  
**回退方式**：移除 `sdlc_trace_event` event type 映射，保留既有 Runtime event types。

### Phase 3：Close-out and PR

**目标**：完成文档归档、manifest 同步、约束验证、commit、PR 和 review/checks 收口。  
**产物**：development-summary.md、task-execution-log.md、GitHub PR。  
**验证方式**：ruff、contract tests、AI-SDLC close-check、GitHub Compatibility Gate。  
**回退方式**：按 PR 回退单一 AO34 分支。

## 工作流计划

### 工作流 A：Outbox receive semantics

**范围**：batch receipt、item-level result、dedup、stale ignored、diagnostic persistence。  
**影响范围**：runtime ingestion、repository、HTTP status 判断。  
**验证方式**：AO34 outbox contract tests。  
**回退方式**：保留 AO31 runtime ingestion 旧路径。

### 工作流 B：SDLC trace bridge

**范围**：`sdlc_trace_event.v1` contract、enterprise_managed gate、TraceSpan mapping、EvidenceSummary consumption。  
**影响范围**：runtime contracts、runtime ingestion、AO32 evidence summary indirectly。  
**验证方式**：AO34 SDLC bridge tests + AO32 summary regression。  
**回退方式**：删除 `sdlc_trace_event` event type mapping。

## 关键路径验证策略

| 关键路径 | 主验证方式 | 次验证方式 |
|----------|------------|------------|
| Outbox dedup/replay | AO34 contract test | AO31 ingestion replay regression |
| Stale ignored | AO34 stale sequence test | Run Detail latest sequence regression |
| Signature/schema diagnostics | AO34 rejection diagnostic test | Runtime DLQ count and raw payload guard |
| SDLC bridge mapping | AO34 SDLC mapping test | AO32 EvidenceSummary missing dimension checks |
| No raw payload | AO34 anti-leak assertions | Existing AO12/AO31/AO33 anti-leak patterns |

## 开放问题

| 问题 | 状态 | 阻塞阶段 |
|------|------|----------|
| 是否需要持久化 outbox batch header 到长期存储 | P1 延后 | 不阻塞 P0 |
| 是否需要独立 SDLC EvidenceSummary contract | P0 不新增，先复用 TraceSpan/EvidenceSummary | 不阻塞 |

## 实施顺序建议

1. 冻结 AO34 formal docs，并同步 program manifest。
2. 新增 AO34 contract tests，覆盖 outbox receipt、diagnostics 和 SDLC bridge。
3. 实现 runtime contracts、repository stale/diagnostic、ingestion mapping。
4. 联跑 AO31/AO32/AO33 回归、ruff 和 AI-SDLC constraints。
5. 归档 execution log / development summary，提交并进入 PR 收口。
