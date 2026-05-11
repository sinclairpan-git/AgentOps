---
related_plan: "specs/042-quality-center-workbench/plan.md"
related_doc:
  - "specs/041-quality-scorer-versioning/spec.md"
  - "specs/042-quality-center-workbench/spec.md"
  - "specs/043-quality-center-console-ui/spec.md"
---
# 任务分解：Quality Scorer Execution Evidence

**编号**：`044-quality-scorer-execution-evidence` | **日期**：2026-05-11
**来源**：plan.md + spec.md

---

## 分批策略

```text
Batch 1: formal baseline and contract registration
Batch 2: scorer execution summary builder/API/repository
Batch 3: Quality Center aggregation and focused verification
```

---

## Batch 1：formal baseline and contract registration

### Task 1.1 冻结 044 formal baseline

- **任务编号**：T11
- **优先级**：P0
- **依赖**：无
- **文件**：spec.md, plan.md, tasks.md, task-execution-log.md
- **可并行**：否
- **状态**：完成
- **验收标准**：
  1. 044 canonical formal docs 已直接位于 `specs/044-quality-scorer-execution-evidence/`
  2. 范围明确为 summary-only scorer execution evidence，不包含自动 rollout/Store 写回/通知发送
- **验证**：文档对账 + program truth sync

### Task 1.2 注册 quality_scorer_execution contract

- **任务编号**：T12
- **优先级**：P0
- **依赖**：T11
- **文件**：src/agentops/core/runtime_contracts.py
- **可并行**：否
- **状态**：完成
- **验收标准**：
  1. `quality_scorer_execution.v1` 存在 required fields、enum fields、error code 和 AO44 tests
  2. compatibility policy 与 Quality Center P1 contract 保持一致
- **验证**：AO44-CT-001

## Batch 2：scorer execution summary builder/API/repository

### Task 2.1 新增 scorer execution repository records

- **任务编号**：T21
- **优先级**：P0
- **依赖**：T12
- **文件**：src/agentops/storage/repository.py
- **可并行**：否
- **状态**：完成
- **验收标准**：
  1. repository 可存储 scorer execution summary
  2. repository 可按 agent/version/scorer 查询最新 execution records
- **验证**：AO44-CT-002/005

### Task 2.2 实现 summary-only scorer execution builder/API

- **任务编号**：T22
- **优先级**：P0
- **依赖**：T21
- **文件**：src/agentops/core/operations.py, src/agentops/api/operations.py
- **可并行**：否
- **状态**：完成
- **验收标准**：
  1. builder 只读取 EvalCase summary 与 scorer summary fields
  2. 稀疏样本进入 `insufficient_evidence`
  3. failed/blocked 状态进入人工复核
  4. 输出不包含 forbidden raw/prompt/diff/terminal/url/secret markers
- **验证**：AO44-CT-002/003/004

## Batch 3：Quality Center aggregation and focused verification

### Task 3.1 聚合 scorer execution evidence 到 Quality Center

- **任务编号**：T31
- **优先级**：P1
- **依赖**：T22
- **文件**：src/agentops/core/operations.py
- **可并行**：否
- **状态**：完成
- **验收标准**：
  1. agent summary 包含最新 scorer execution evidence
  2. rollout panel 包含 execution counts 与 manual review queue
  3. review queue 对需要人工复核的 execution evidence 追加 scorer_execution item
- **验证**：AO44-CT-005 + AO42 regression

### Task 3.2 完成 focused verification 与 close-check

- **任务编号**：T32
- **优先级**：P0
- **依赖**：T31
- **文件**：tests/contract/test_ao44_ct_quality_scorer_execution_evidence.py, specs/044-quality-scorer-execution-evidence/*
- **可并行**：否
- **状态**：完成
- **验收标准**：
  1. AO40/AO41/AO42/AO44 focused tests 通过
  2. ruff check/format 通过
  3. constraints 与 workitem close-check 通过
- **验证**：见 task-execution-log.md
