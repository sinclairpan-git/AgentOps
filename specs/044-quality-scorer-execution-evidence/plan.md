---
related_plan: "specs/042-quality-center-workbench/plan.md"
related_doc:
  - "specs/041-quality-scorer-versioning/spec.md"
  - "specs/042-quality-center-workbench/spec.md"
  - "specs/043-quality-center-console-ui/spec.md"
---
# 实施计划：Quality Scorer Execution Evidence

**编号**：`044-quality-scorer-execution-evidence` | **日期**：2026-05-11 | **规格**：specs/044-quality-scorer-execution-evidence/spec.md

## 概述

新增 `quality_scorer_execution.v1` summary contract，记录 scorer 对 EvalCase summary 的确定性执行证据，并把最新 execution evidence 聚合到 Quality Center Workbench。实现必须延续 041-043 的边界：summary-only、人工审批、无外部写入、无自动 rollout。

## 技术背景

**语言/版本**：Python 3.11，现有 AgentOps core/API/repository。
**主要依赖**：stdlib、pytest、ruff、AI-SDLC CLI。
**存储**：`InMemoryRepository` 新增 scorer execution records。
**测试**：AO44 contract tests + AO40/AO41/AO42 focused regression。
**目标平台**：本地 contract/API 层，Console 可通过后续快照/UI 消费聚合字段。
**约束**：不得读取 raw evidence；不得新增真实外部 scorer execution；不得触发 rollout、Store 写回、通知发送或 lifecycle 自动动作。

## 宪章检查

| 宪章门禁 | 计划响应 |
|----------|----------|
| Governance-first | 先运行 adapter status、dry-run，并用 workitem init 物化 canonical docs。 |
| Machine-verifiable evidence | 新增 contract tests，验证 contract registry、execution payload、Quality Center 聚合与 no raw/no auto guardrails。 |
| Human approval boundary | 所有 execution outcome 只产生 manual recommendation，自动 rollout/store/notification/lifecycle action 均为 false。 |
| Summary-only evidence | 输入只使用 EvalCase summary、scorer version 和 scorer comparison；输出通过 redaction，禁止 raw/prompt/diff/terminal/url/secret marker。 |

## 项目结构

### 文档结构

```text
specs/044-quality-scorer-execution-evidence/
├── spec.md
├── plan.md
├── tasks.md
├── task-execution-log.md
└── development-summary.md
```

### 源码结构

```text
src/agentops/core/runtime_contracts.py
src/agentops/core/operations.py
src/agentops/api/operations.py
src/agentops/storage/repository.py
tests/contract/test_ao44_ct_quality_scorer_execution_evidence.py
```

## 阶段计划

### Phase 0：正式规格冻结

**目标**：明确 AO44 范围、非目标、验收标准和 contract surface。
**产物**：spec.md / plan.md / tasks.md / task-execution-log.md。
**验证方式**：文档对账、program truth sync。
**回退方式**：删除 044 docs 和 manifest mapping，回到 043 close 状态。

### Phase 1：Contract 与后端 summary evidence

**目标**：注册 `quality_scorer_execution.v1`，实现 builder/API/repository，提供 deterministic summary-only evidence。
**产物**：runtime contract、operations builder、API wrapper、repository methods、AO44 tests。
**验证方式**：`uv run pytest tests/contract/test_ao44_ct_quality_scorer_execution_evidence.py -q`。
**回退方式**：移除新增 contract/API/repository methods 和 AO44 tests。

### Phase 2：Quality Center 聚合与回归

**目标**：Quality Center agent summary 与 rollout panel 聚合最新 scorer execution evidence。
**产物**：Workbench 字段、review queue 人工复核项、focused regression。
**验证方式**：AO40/AO41/AO42/AO44 focused tests、ruff、constraints、close-check。
**回退方式**：回退 Quality Center 聚合字段，保留原 042/043 行为。

## 工作流计划

### 工作流 A：Scorer Execution Summary

**范围**：新增 builder/API/repository 存取。
**影响范围**：Core operations、API operations、contract registry。
**验证方式**：AO44-CT-001 至 AO44-CT-004。
**回退方式**：删除新增 execution path。

### 工作流 B：Quality Center Aggregation

**范围**：Workbench 聚合 latest execution evidence 和 manual review signal。
**影响范围**：`build_quality_center_workbench`、review queue、rollout panel。
**验证方式**：AO44-CT-005 + AO42 focused regression。
**回退方式**：保留 repository records，不展示到 workbench。

## 关键路径验证策略

| 关键路径 | 主验证方式 | 次验证方式 |
|----------|------------|------------|
| Contract registry | AO44-CT-001 | `get_contract` required fields |
| Summary-only execution | AO44-CT-002/003/004 | forbidden key/value traversal |
| Quality Center 聚合 | AO44-CT-005 | AO42 regression |
| Governance | `uv run ai-sdlc verify constraints` | workitem close-check |

## 开放问题

| 问题 | 状态 | 阻塞阶段 |
|------|------|----------|
| 是否执行真实 scorer runtime | 明确不进入 044 | 否 |
| 是否自动 rollout 或写 Store | 明确不进入 044 | 否 |

## 实施顺序建议

1. 冻结 docs 并同步 truth。
2. 注册 contract 与 repository records。
3. 实现 scorer execution builder/API。
4. 聚合到 Quality Center Workbench。
5. 运行 focused tests、ruff、constraints、close-check。
