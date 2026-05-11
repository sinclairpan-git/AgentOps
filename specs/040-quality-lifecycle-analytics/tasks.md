---
related_doc:
  - "/Users/sinclairpan/project/AI-Native底座开发文档/AgentOps_项目_PRD.md"
  - "specs/032-evidence-health-summary-loop/spec.md"
  - "specs/037-p1-evidence-eval-cost-operations/spec.md"
  - "specs/039-p2-ecosystem-governance/spec.md"
---
# 任务分解：Quality Lifecycle Analytics

**编号**：`040-quality-lifecycle-analytics` | **日期**：2026-05-10  
**来源**：plan.md + spec.md

## 分批策略

```text
Batch 1: formal baseline + quality lifecycle analytics contracts
Batch 2: close-out verification + PR review fixes if any
```

## Batch 1：formal baseline + quality lifecycle analytics contracts

### Task 1.1 冻结 040 formal baseline

- **任务编号**：T11
- **状态**：已完成
- **优先级**：P0
- **依赖**：无
- **文件**：spec.md, plan.md, tasks.md, program-manifest.yaml
- **可并行**：否
- **验收标准**：
  1. 040 文档承接 PRD 阶段 4/5 质量评分、采纳分析、生命周期建议、月报。
  2. program truth 映射 040 spec/plan/tasks/log。
- **验证**：`python -m ai_sdlc program truth sync --execute --yes`

### Task 1.2 登记 AO40 contracts

- **任务编号**：T12
- **状态**：已完成
- **优先级**：P0
- **依赖**：T11
- **文件**：src/agentops/core/runtime_contracts.py, tests/contract/test_ao40_ct_quality_lifecycle_analytics.py
- **可并行**：否
- **验收标准**：
  1. registry 包含 `quality_score_projection.v1`、`adoption_roi_projection.v1`、`lifecycle_recommendation.v1`、`monthly_quality_report.v1`。
  2. required fields、enum fields 和 contract tests 与 spec 一致。
- **验证**：AO40-CT-001

### Task 1.3 实现 quality score 与 adoption ROI projection

- **任务编号**：T13
- **状态**：已完成
- **优先级**：P1
- **依赖**：T12
- **文件**：src/agentops/core/operations.py, src/agentops/api/operations.py
- **可并行**：否
- **验收标准**：
  1. quality score 输出 score/template/evidence/confidence/missing/explanation。
  2. adoption ROI 只消费摘要指标，输出 retention、rework、CI/review 摘要。
- **验证**：AO40-CT-002、AO40-CT-003

### Task 1.4 实现 lifecycle recommendation 与 monthly report

- **任务编号**：T14
- **状态**：已完成
- **优先级**：P1
- **依赖**：T13
- **文件**：src/agentops/core/operations.py, src/agentops/api/operations.py
- **可并行**：否
- **验收标准**：
  1. lifecycle recommendation 组合 quality/risk/store governance，只返回人工建议。
  2. monthly report 聚合多个 Agent/version summary，不自动发布。
- **验证**：AO40-CT-004、AO40-CT-005

### Task 1.5 回归与归档

- **任务编号**：T15
- **状态**：已完成
- **优先级**：P0
- **依赖**：T14
- **文件**：tasks.md, task-execution-log.md, development-summary.md
- **可并行**：否
- **验收标准**：
  1. AO40、AO32、AO37、AO39 定向回归通过。
  2. ruff、AI-SDLC verify 和 close-check 通过。
  3. 执行日志与任务状态和本批提交一致。
- **验证**：见 task-execution-log.md
