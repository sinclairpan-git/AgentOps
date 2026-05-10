---
related_doc:
  - "specs/031-agentops-runtime-governance-foundation/agentops-p0-p2-backlog.md"
  - "specs/032-evidence-health-summary-loop/spec.md"
  - "specs/034-runtime-outbox-sdlc-trace-bridge/spec.md"
  - "specs/037-p1-evidence-eval-cost-operations/spec.md"
  - "specs/038-p2-replay-simulation-optimizer/spec.md"
---
# 任务分解：P2 Ecosystem Governance

**编号**：`039-p2-ecosystem-governance` | **日期**：2026-05-10  
**来源**：plan.md + spec.md

## 分批策略

```text
Batch 1: formal baseline + P2-B ecosystem governance contracts
Batch 2: close-out verification + PR review fixes if any
```

## Batch 1：formal baseline + P2-B ecosystem governance contracts

### Task 1.1 冻结 039 formal baseline

- **任务编号**：T11
- **优先级**：P0
- **依赖**：无
- **文件**：spec.md, plan.md, tasks.md, program-manifest.yaml
- **可并行**：否
- **验收标准**：
  1. 039 文档承接 P2-B AO-P2-03/06/08/09。
  2. program truth 映射 039 spec/plan/tasks/log。
- **验证**：`python -m ai_sdlc program truth sync --execute --yes`

### Task 1.2 登记 AO39 P2-B contracts

- **任务编号**：T12
- **优先级**：P0
- **依赖**：T11
- **文件**：src/agentops/core/runtime_contracts.py, tests/contract/test_ao39_ct_p2_ecosystem_governance.py
- **可并行**：否
- **验收标准**：
  1. registry 包含 `mcp_a2a_governance_projection.v1`、`exporter_ecosystem_projection.v1`、`multi_agent_handoff_evaluation.v1`、`complex_risk_profile.v1`。
  2. required fields、enum fields 和 contract tests 与 spec 一致。
- **验证**：AO39-CT-001

### Task 1.3 实现 MCP/A2A 与 exporter ecosystem projection

- **任务编号**：T13
- **优先级**：P1
- **依赖**：T12
- **文件**：src/agentops/core/operations.py, src/agentops/api/operations.py
- **可并行**：否
- **验收标准**：
  1. MCP/A2A projection 固定 runtime gateway required，direct connection denied。
  2. 多 exporter projection 固定 dry-run/no-write，配置只保留 ref/hash。
- **验证**：AO39-CT-002、AO39-CT-003

### Task 1.4 实现 handoff evaluation 与 complex risk profile

- **任务编号**：T14
- **优先级**：P1
- **依赖**：T13
- **文件**：src/agentops/core/operations.py, src/agentops/api/operations.py
- **可并行**：否
- **验收标准**：
  1. handoff evaluation 从 TraceSpan summary 统计 handoff 质量。
  2. complex risk profile 聚合 health、DLQ、handoff 风险，不自动处置。
- **验证**：AO39-CT-004、AO39-CT-005

### Task 1.5 回归与归档

- **任务编号**：T15
- **优先级**：P0
- **依赖**：T14
- **文件**：tasks.md, task-execution-log.md, development-summary.md
- **可并行**：否
- **验收标准**：
  1. AO39、AO32、AO34、AO37、AO38 定向回归通过。
  2. ruff、AI-SDLC verify 和 close-check 通过。
  3. 执行日志与任务状态和本批提交一致。
- **验证**：见 task-execution-log.md
