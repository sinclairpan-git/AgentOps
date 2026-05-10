---
related_doc:
  - "specs/031-agentops-runtime-governance-foundation/agentops-p0-p2-backlog.md"
  - "specs/032-evidence-health-summary-loop/spec.md"
  - "specs/034-runtime-outbox-sdlc-trace-bridge/spec.md"
---
# 任务分解：P1 Evidence Eval Cost Operations

**编号**：`037-p1-evidence-eval-cost-operations` | **日期**：2026-05-10  
**来源**：plan.md + spec.md

## 分批策略

```text
Batch 1: formal baseline + P1-B contract projections
Batch 2: close-out verification + PR review fixes if any
```

## Batch 1：formal baseline + P1-B contract projections

### Task 1.1 冻结 037 formal baseline

- **任务编号**：T11
- **优先级**：P0
- **依赖**：无
- **文件**：spec.md, plan.md, tasks.md, program-manifest.yaml
- **可并行**：否
- **验收标准**：
  1. 037 文档反映 P1-B AgentOps 真实业务范围。
  2. program truth 映射 037 spec/plan/tasks/log。
- **验证**：`python -m ai_sdlc program truth sync --execute --yes`

### Task 1.2 登记 AO37 P1-B contracts

- **任务编号**：T12
- **优先级**：P0
- **依赖**：T11
- **文件**：src/agentops/core/runtime_contracts.py, tests/contract/test_ao37_ct_p1_evidence_eval_cost_operations.py
- **可并行**：否
- **验收标准**：
  1. registry 包含 `evidence_access_operation.v1`、`eval_case.v1`、`runtime_budget_summary.v1`、`dlq_operations_projection.v1`、`exporter_operation.v1`、`runtime_slo_summary.v1`、`store_governance_projection.v1`。
  2. required fields、enum fields 和 contract tests 与 spec 一致。
- **验证**：AO37-CT-001

### Task 1.3 实现 Evidence access 与 EvalCase operation projection

- **任务编号**：T13
- **优先级**：P1
- **依赖**：T12
- **文件**：src/agentops/core/operations.py, src/agentops/api/operations.py, src/agentops/storage/repository.py
- **可并行**：否
- **验收标准**：
  1. raw evidence access operation 不返回原文。
  2. failed/blocked/degraded run 可沉淀 EvalCase，succeeded run 被拒绝。
- **验证**：AO37-CT-002、AO37-CT-003

### Task 1.4 实现 Budget / DLQ / Exporter / Runtime SLO / Store governance projection

- **任务编号**：T14
- **优先级**：P1
- **依赖**：T13
- **文件**：src/agentops/core/operations.py, src/agentops/api/operations.py, src/agentops/storage/repository.py
- **可并行**：否
- **验收标准**：
  1. budget summary 汇总 token、cost 和 latency。
  2. DLQ projection 返回 candidates 和 error stats，不返回 raw payload。
  3. exporter operation 为 dry-run/no-write。
  4. Runtime SLO 与 Store governance projection display-only。
- **验证**：AO37-CT-004 到 AO37-CT-008

### Task 1.5 回归与归档

- **任务编号**：T15
- **优先级**：P0
- **依赖**：T14
- **文件**：tasks.md, task-execution-log.md, development-summary.md
- **可并行**：否
- **验收标准**：
  1. AO37、AO32、AO34、AO35 定向回归通过。
  2. ruff、AI-SDLC verify 和 close-check 通过。
  3. 执行日志与任务勾选和本批提交一致。
- **验证**：见 task-execution-log.md
