---
related_doc:
  - "specs/031-agentops-runtime-governance-foundation/agentops-p0-p2-backlog.md"
  - "specs/032-evidence-health-summary-loop/spec.md"
  - "specs/036-p1-approval-policy-grant-operations/spec.md"
  - "specs/037-p1-evidence-eval-cost-operations/spec.md"
---
# 任务分解：P2 Replay Simulation Optimizer

**编号**：`038-p2-replay-simulation-optimizer` | **日期**：2026-05-10  
**来源**：plan.md + spec.md

## 分批策略

```text
Batch 1: formal baseline + P2-A planning/projection contracts
Batch 2: close-out verification + PR review fixes if any
```

## Batch 1：formal baseline + P2-A planning/projection contracts

### Task 1.1 冻结 038 formal baseline

- **任务编号**：T11
- **优先级**：P0
- **依赖**：无
- **文件**：spec.md, plan.md, tasks.md, program-manifest.yaml
- **可并行**：否
- **验收标准**：
  1. 038 文档承接 P2-A AO-P2-01/02/07/10。
  2. program truth 映射 038 spec/plan/tasks/log。
- **验证**：`python -m ai_sdlc program truth sync --execute --yes`

### Task 1.2 登记 AO38 P2-A contracts

- **任务编号**：T12
- **优先级**：P0
- **依赖**：T11
- **文件**：src/agentops/core/runtime_contracts.py, tests/contract/test_ao38_ct_p2_replay_simulation_optimizer.py
- **可并行**：否
- **验收标准**：
  1. registry 包含 `safe_replay_plan.v1`、`experiment_plan.v1`、`optimizer_recommendation.v1`、`policy_simulation_projection.v1`。
  2. required fields、enum fields 和 contract tests 与 spec 一致。
- **验证**：AO38-CT-001

### Task 1.3 实现 SafeReplay 与 Experiment plan

- **任务编号**：T13
- **优先级**：P1
- **依赖**：T12
- **文件**：src/agentops/core/operations.py, src/agentops/api/operations.py, src/agentops/storage/repository.py
- **可并行**：否
- **验收标准**：
  1. terminal run 可生成 safe replay plan，running run 被拒绝。
  2. experiment variants 只保留 safe ref/hash/risk，不保留 raw config/payload。
- **验证**：AO38-CT-002、AO38-CT-003

### Task 1.4 实现 Optimizer 与 Policy simulation projection

- **任务编号**：T14
- **优先级**：P1
- **依赖**：T13
- **文件**：src/agentops/core/operations.py, src/agentops/api/operations.py
- **可并行**：否
- **验收标准**：
  1. optimizer 只从 EvalCase 摘要输出人工可审建议。
  2. policy simulation 只做 dry-run 影响投影，不发布 policy。
- **验证**：AO38-CT-004、AO38-CT-005

### Task 1.5 回归与归档

- **任务编号**：T15
- **优先级**：P0
- **依赖**：T14
- **文件**：tasks.md, task-execution-log.md, development-summary.md
- **可并行**：否
- **验收标准**：
  1. AO38、AO32、AO34、AO35、AO37 定向回归通过。
  2. ruff、AI-SDLC verify 和 close-check 通过。
  3. 执行日志与任务状态和本批提交一致。
- **验证**：见 task-execution-log.md
