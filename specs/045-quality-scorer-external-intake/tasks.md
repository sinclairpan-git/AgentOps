---
related_plan: "specs/044-quality-scorer-execution-evidence/plan.md"
related_doc:
  - "specs/041-quality-scorer-versioning/spec.md"
  - "specs/042-quality-center-workbench/spec.md"
  - "specs/044-quality-scorer-execution-evidence/spec.md"
---
# 任务分解：Quality Scorer External Intake

**编号**：`045-quality-scorer-external-intake` | **日期**：2026-05-11
**来源**：plan.md + spec.md

---

## 分批策略

```text
Batch 1: 045 formal scope and contract registry
Batch 2: repository/core/API external intake
Batch 3: Quality Center aggregation and close verification
```

---

## Batch 1：045 formal scope and contract registry

### Task 1.1 冻结 045 formal docs

- **任务编号**：T11
- **优先级**：P0
- **依赖**：无
- **文件**：specs/045-quality-scorer-external-intake/*
- **可并行**：否
- **状态**：完成
- **验收标准**：
  1. 045 canonical formal docs 已直接位于 `specs/045-quality-scorer-external-intake/`
  2. scope 明确为 external scorer result intake，不包含 AgentOps 执行 scorer
- **验证**：文档对账 + `uv run ai-sdlc verify constraints`

### Task 1.2 注册 external intake contract

- **任务编号**：T12
- **优先级**：P0
- **依赖**：T11
- **文件**：src/agentops/core/runtime_contracts.py, tests/contract/test_ao45_ct_quality_scorer_external_intake.py
- **可并行**：否
- **状态**：完成
- **验收标准**：
  1. `quality_scorer_external_intake.v1` 存在 required fields、enum fields、error codes 和 AO45 contract tests
  2. contract 声明 no-auto-action 与 summary-only intake 边界
- **验证**：`uv run pytest tests/contract/test_ao45_ct_quality_scorer_external_intake.py -q`

## Batch 2：repository/core/API external intake

### Task 2.1 新增 intake receipt 与 idempotency 存储

- **任务编号**：T21
- **优先级**：P0
- **依赖**：T12
- **文件**：src/agentops/storage/repository.py
- **可并行**：否
- **状态**：完成
- **验收标准**：
  1. repository 可存储 external intake receipt
  2. 重复 `idempotency_key` 不重复创建 execution evidence
- **验证**：AO45 idempotency contract test

### Task 2.2 实现 external scorer execution intake

- **任务编号**：T22
- **优先级**：P0
- **依赖**：T21
- **文件**：src/agentops/core/operations.py, src/agentops/api/operations.py
- **可并行**：否
- **状态**：完成
- **验收标准**：
  1. signed/verified result 生成 accepted receipt 与 `quality_scorer_execution.v1`
  2. unsigned、缺签名、未知 EvalCase、raw/secret marker 输入被拒绝
  3. 输出不含 raw evidence、prompt、diff、terminal、URL、secret
- **验证**：AO45 accepted/rejection contract tests

## Batch 3：Quality Center aggregation and close verification

### Task 3.1 复用 Quality Center execution evidence 聚合

- **任务编号**：T31
- **优先级**：P1
- **依赖**：T22
- **文件**：tests/contract/test_ao45_ct_quality_scorer_external_intake.py
- **可并行**：否
- **状态**：完成
- **验收标准**：
  1. external intake 写入的 execution evidence 被 `get_quality_center_workbench()` 聚合
  2. no-auto-action guardrails 保持 false
- **验证**：AO45 workbench aggregation test + AO40/AO41/AO42/AO44/AO45 回归

---

## 完成定义

- AO45 定向测试通过。
- AO40/AO41/AO42/AO44/AO45 定向回归通过。
- `uv run ruff check`、`uv run ruff format --check` 通过。
- `uv run ai-sdlc verify constraints` 无 BLOCKER。
- `python -m ai_sdlc program truth sync --execute --yes` 已同步。
- `python -m ai_sdlc workitem close-check --wi specs/045-quality-scorer-external-intake --json` 仅允许提交前 git closure 阻塞。
