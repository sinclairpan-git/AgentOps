---
related_doc:
  - "/Users/sinclairpan/project/AI-Native底座开发文档/AgentOps_项目_PRD.md"
  - "specs/040-quality-lifecycle-analytics/spec.md"
  - "specs/041-quality-scorer-versioning/spec.md"
---
# 任务分解：Quality Center Workbench

**编号**：`042-quality-center-workbench` | **日期**：2026-05-11  
**来源**：plan.md + spec.md

## 分批策略

```text
Batch 1: formal baseline + quality center workbench contract
Batch 2: close-out verification + PR review fixes if any
```

## Batch 1：formal baseline + quality center workbench contract

### Task 1.1 冻结 042 formal baseline

- **任务编号**：T11
- **状态**：已完成
- **优先级**：P0
- **依赖**：无
- **文件**：spec.md, plan.md, tasks.md, program-manifest.yaml
- **可并行**：否
- **验收标准**：
  1. 042 文档承接 PRD Quality Center 页面目标。
  2. program truth 映射 042 spec/plan/tasks/log。
- **验证**：`python -m ai_sdlc program truth sync --execute --yes`

### Task 1.2 登记 AO42 contract

- **任务编号**：T12
- **状态**：已完成
- **优先级**：P0
- **依赖**：T11
- **文件**：src/agentops/core/runtime_contracts.py, tests/contract/test_ao42_ct_quality_center_workbench.py
- **可并行**：否
- **验收标准**：
  1. registry 包含 `quality_center_workbench.v1`。
  2. required fields、enum fields 和 contract tests 与 spec 一致。
- **验证**：AO42-CT-001

### Task 1.3 实现 Quality Center projection

- **任务编号**：T13
- **状态**：已完成
- **优先级**：P1
- **依赖**：T12
- **文件**：src/agentops/core/operations.py, src/agentops/api/operations.py
- **可并行**：否
- **验收标准**：
  1. workbench 输出 quality summaries、scorer rollout panel、review queue、trend summary。
  2. 输出不包含 raw prompt/config/evidence/diff。
  3. 所有 action 保持人工处理，不自动 rollout/写 Store/下架/发布。
- **验证**：AO42-CT-002、AO42-CT-003

### Task 1.4 回归与归档

- **任务编号**：T14
- **状态**：已完成
- **优先级**：P0
- **依赖**：T13
- **文件**：tasks.md, task-execution-log.md, development-summary.md
- **可并行**：否
- **验收标准**：
  1. AO42、AO40、AO41 定向回归通过。
  2. ruff、AI-SDLC verify 和 close-check 通过。
  3. 执行日志与任务状态和本批提交一致。
- **验证**：见 task-execution-log.md
