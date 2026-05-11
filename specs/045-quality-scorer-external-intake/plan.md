---
related_plan: "specs/044-quality-scorer-execution-evidence/plan.md"
related_doc:
  - "specs/041-quality-scorer-versioning/spec.md"
  - "specs/042-quality-center-workbench/spec.md"
  - "specs/044-quality-scorer-execution-evidence/spec.md"
---
# 实施计划：Quality Scorer External Intake

**编号**：`045-quality-scorer-external-intake` | **日期**：2026-05-11 | **规格**：specs/045-quality-scorer-external-intake/spec.md

## 概述

在 044 的 `quality_scorer_execution.v1` 基础上新增外部 scorer result intake。AgentOps 接收外部受管 scorer 上报的 summary-only execution result，完成 trust、signature、idempotency 与 sample boundary 校验后，写入既有 scorer execution evidence 并进入 Quality Center Workbench。实现不调用外部 scorer、不读取 raw evidence、不触发 rollout/Store/通知。

## 技术背景

**语言/版本**：Python 3.11  
**主要依赖**：现有 `agentops.core.operations`、`agentops.storage.repository`、runtime contract registry  
**存储**：In-memory repository 增加 intake receipt 与 idempotency index  
**测试**：pytest contract tests  
**目标平台**：AgentOps backend contract/API surface  
**约束**：summary-only、no raw access、no external execution by AgentOps、no automatic lifecycle action

## 宪章检查

| 宪章门禁 | 计划响应 |
|----------|----------|
| AI-SDLC 入口 | 已执行 `ai-sdlc adapter status` 与 `ai-sdlc run --dry-run` |
| Canonical docs | 045 formal docs 直接位于 `specs/045-quality-scorer-external-intake/` |
| Summary-only 边界 | 只接收 summary result；raw/prompt/diff/terminal 禁止进入输出 |
| AgentOps 边界 | AgentOps 不执行 scorer，不调度 Runtime，不写 Store，不发通知 |
| 可验证证据 | AO45 contract tests 覆盖 accepted/dedup/rejection/aggregation |

## 项目结构

### 文档结构

```text
specs/045-quality-scorer-external-intake/
├── spec.md
├── plan.md
├── tasks.md
└── task-execution-log.md
```

### 源码结构

```text
src/agentops/core/runtime_contracts.py        # 注册 quality_scorer_external_intake.v1
src/agentops/core/operations.py               # intake builder 与安全校验
src/agentops/api/operations.py                # API wrapper
src/agentops/storage/repository.py            # intake receipt/idempotency 存储
tests/contract/test_ao45_ct_quality_scorer_external_intake.py
```

## 阶段计划

### Phase 0：研究与决策冻结

**目标**：冻结 045 scope，明确只做 external result intake。  
**产物**：spec.md / plan.md / tasks.md / task-execution-log.md。  
**验证方式**：文档对齐 041/042/044 未进入本批项。  
**回退方式**：移除 045 docs 与 manifest mapping。

### Phase 1：Contract 与 repository

**目标**：注册 intake contract，并提供 receipt/idempotency 存储。  
**产物**：`quality_scorer_external_intake.v1`、repository methods。  
**验证方式**：AO45-CT-001、AO45-CT-003。  
**回退方式**：删除新增 contract entry 与 repository fields/methods。

### Phase 2：Core/API intake

**目标**：实现 signed/verified external result intake，输出 receipt 与 execution evidence。  
**产物**：`ingest_quality_scorer_external_execution` core/API wrapper。  
**验证方式**：AO45 accepted/rejected contract tests。  
**回退方式**：移除 wrapper 与 tests。

### Phase 3：Quality Center 回归

**目标**：证明 external intake 写入的 execution evidence 被现有 Workbench 聚合。  
**产物**：AO45 Quality Center aggregation test。  
**验证方式**：AO40/AO41/AO42/AO44/AO45 定向回归。  
**回退方式**：回滚 045 feature branch。

## 工作流计划

### 工作流 A：可信 external result accepted

**范围**：signed/verified source、已存在 EvalCase、summary-only result。  
**影响范围**：Core/API/repository/contract tests。  
**验证方式**：receipt accepted，execution evidence persisted，Quality Center 可见。  
**回退方式**：删除 receipt 与 execution record。

### 工作流 B：不可信或越界 result rejected

**范围**：unsigned source、缺签名、未知 EvalCase、raw marker。  
**影响范围**：Core validation。  
**验证方式**：抛出 `AgentOpsError`，不写 execution record。  
**回退方式**：无持久副作用。

## 关键路径验证策略

| 关键路径 | 主验证方式 | 次验证方式 |
|----------|------------|------------|
| Contract registry | AO45-CT-001 | runtime registry focused tests |
| Accepted intake | AO45-CT-002 | AO44 scorer execution regression |
| Idempotency | AO45-CT-003 | repository record count assertion |
| Rejection boundary | AO45-CT-004/005 | no raw leak assertion |
| Workbench aggregation | AO45-CT-006 | AO42/AO44 regression |

## 开放问题

| 问题 | 状态 | 阻塞阶段 |
|------|------|----------|
| 是否需要真实网络 endpoint | 非目标；当前只提供 core/API contract surface | 不阻塞 |
| 是否自动 rollout approved scorer | 非目标；必须人工审批 | 不阻塞 |

## 实施顺序建议

1. 更新 045 docs 和 contract registry。
2. 增加 repository intake receipt/idempotency。
3. 实现 core/API external intake wrapper。
4. 新增 AO45 contract tests 并跑定向回归。
5. 执行 truth sync、constraints、close-check。
