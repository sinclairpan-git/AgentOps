---
related_doc:
  - "/Users/sinclairpan/project/AI-Native底座开发文档/AgentOps_项目_PRD.md"
  - "specs/037-p1-evidence-eval-cost-operations/spec.md"
  - "specs/040-quality-lifecycle-analytics/spec.md"
---
# 任务分解：Quality Scorer Versioning

**编号**：`041-quality-scorer-versioning` | **日期**：2026-05-10  
**来源**：plan.md + spec.md

## 分批策略

```text
Batch 1: formal baseline + scorer versioning contracts
Batch 2: close-out verification + PR review fixes if any
```

## Batch 1：formal baseline + scorer versioning contracts

### Task 1.1 冻结 041 formal baseline

- **任务编号**：T11
- **状态**：已完成
- **优先级**：P0
- **依赖**：无
- **文件**：spec.md, plan.md, tasks.md, program-manifest.yaml
- **可并行**：否
- **验收标准**：
  1. 041 文档承接 PRD 16.6 P1 基础 scorer 与版本对比。
  2. program truth 映射 041 spec/plan/tasks/log。
- **验证**：`python -m ai_sdlc program truth sync --execute --yes`

### Task 1.2 登记 AO41 contracts

- **任务编号**：T12
- **状态**：已完成
- **优先级**：P0
- **依赖**：T11
- **文件**：src/agentops/core/runtime_contracts.py, tests/contract/test_ao41_ct_quality_scorer_versioning.py
- **可并行**：否
- **验收标准**：
  1. registry 包含 `quality_scorer_version.v1`、`quality_scorer_comparison.v1`。
  2. required fields、enum fields 和 contract tests 与 spec 一致。
- **验证**：AO41-CT-001

### Task 1.3 实现 scorer version projection

- **任务编号**：T13
- **状态**：已完成
- **优先级**：P1
- **依赖**：T12
- **文件**：src/agentops/core/operations.py, src/agentops/api/operations.py
- **可并行**：否
- **验收标准**：
  1. scorer version 输出模板、证据需求、输入边界和 rollout 状态。
  2. 输出不包含 raw prompt/config/evidence。
- **验证**：AO41-CT-002

### Task 1.4 实现 scorer comparison projection

- **任务编号**：T14
- **状态**：已完成
- **优先级**：P1
- **依赖**：T13
- **文件**：src/agentops/core/operations.py, src/agentops/api/operations.py
- **可并行**：否
- **验收标准**：
  1. comparison 只消费当前 agent/version EvalCase 摘要。
  2. 输出 baseline/candidate、alignment_delta、safety_impact、recommendation 和 manual approval 状态。
  3. 样本不足或非法门槛不进入 ready/rollout。
- **验证**：AO41-CT-003、AO41-CT-004

### Task 1.5 回归与归档

- **任务编号**：T15
- **状态**：已完成
- **优先级**：P0
- **依赖**：T14
- **文件**：tasks.md, task-execution-log.md, development-summary.md
- **可并行**：否
- **验收标准**：
  1. AO41、AO37、AO40 定向回归通过。
  2. ruff、AI-SDLC verify 和 close-check 通过。
  3. 执行日志与任务状态和本批提交一致。
- **验证**：见 task-execution-log.md
