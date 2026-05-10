---
related_doc:
  - "specs/031-agentops-runtime-governance-foundation/agentops-p0-p2-backlog.md"
  - "specs/031-agentops-runtime-governance-foundation/spec.md"
  - "specs/032-evidence-health-summary-loop/spec.md"
  - "specs/033-policy-grant-approval-minimum-control/spec.md"
  - "specs/034-runtime-outbox-sdlc-trace-bridge/spec.md"
---
# 实施计划：P0 End-to-End Acceptance Gate

**编号**：`035-p0-end-to-end-acceptance-gate` | **日期**：2026-05-09 | **规格**：specs/035-p0-end-to-end-acceptance-gate/spec.md

## 概述

AO35 串联 P0 已交付能力，新增一个只读验收 projection。它不新增执行路径或持久化模型，而是在同一 `run_id` 上聚合 Runtime ingestion、Run Detail、Trace Timeline、EvidenceSummary、HealthSummary、PolicyDecision、CapabilityGrant、Guardrail 和 Agent Store echo，输出机器可判定的 `p0_acceptance_gate.v1`。

## 技术背景

**语言/版本**：Python 3.11+  
**主要依赖**：标准库、pytest、ruff、AI-SDLC CLI  
**存储**：复用 `InMemoryRepository` P0 contract repository；不引入外部 DB  
**测试**：AO35 contract tests + AO31/AO32/AO33/AO34 定向回归  
**约束**：只读 projection；不执行 Agent；不读取 raw payload；不把 dry-run、outbox receipt 或局部 summary 单独提升为 P0 pass

## 宪章检查

| 宪章门禁 | 计划响应 |
|----------|----------|
| Contract-first | 先登记 `p0_acceptance_gate.v1`，再以 AO35 contract tests 固化 pass/fail 口径。 |
| Source truth | 工作项文档位于 `specs/035-p0-end-to-end-acceptance-gate/` 并同步 manifest。 |
| Runtime boundary | Gate 只读聚合 Runtime / Ai_AutoSDLC / Agent Store 事实，不执行 Runtime。 |
| Evidence safety | Gate 只返回摘要、引用、状态、错误码和 audit_id，不返回 raw payload。 |
| Compatibility | AO31-AO34 回归必须继续通过。 |

## 项目结构

```text
src/agentops/api/acceptance.py                         # P0 acceptance projection
src/agentops/core/runtime_contracts.py                 # p0_acceptance_gate.v1 registry
tests/contract/test_ao35_ct_p0_acceptance_gate.py      # AO35 contract tests
specs/035-p0-end-to-end-acceptance-gate/
```

## 阶段计划

### Phase 0：Formal baseline

冻结 AO35 spec/plan/tasks/log/summary，并将 manifest 加入新工作项。

### Phase 1：Acceptance projection

新增 `build_p0_acceptance_gate()`，复用现有 API projection 和 repository facts，输出 required_checks 和 summary。

### Phase 2：Contract tests and regression

覆盖完整闭环 pass、缺 trace fail、无 raw leak，并联跑 AO31/AO32/AO33/AO34 定向回归、ruff 和 AI-SDLC constraints。

## 开放问题

| 问题 | 状态 | 阻塞阶段 |
|------|------|----------|
| 是否需要 HTTP route 暴露 acceptance gate | P1 延后，P0 先冻结 projection 和 contract | 不阻塞 |
| 是否需要持久化历史 gate result | P1 延后，P0 只读即时计算 | 不阻塞 |
