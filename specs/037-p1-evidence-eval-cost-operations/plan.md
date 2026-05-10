---
related_doc:
  - "specs/031-agentops-runtime-governance-foundation/agentops-p0-p2-backlog.md"
  - "specs/032-evidence-health-summary-loop/spec.md"
  - "specs/034-runtime-outbox-sdlc-trace-bridge/spec.md"
---
# 实施计划：P1 Evidence Eval Cost Operations

**编号**：`037-p1-evidence-eval-cost-operations` | **日期**：2026-05-10 | **规格**：specs/037-p1-evidence-eval-cost-operations/spec.md

## 概述

AO37 承接 P1-B，把 P0 Evidence/Health/Outbox/Store 摘要推进为可运营的后端 contract surface。第一批实现聚焦 summary-only operation projections：Evidence raw access 申请、EvalCase、Runtime budget、DLQ ops、Exporter dry-run、Runtime SLO 和 Store governance。所有 projection 只提供人工处置依据，不执行 replay/export/disable/publish。

## 技术背景

**语言/版本**：Python 3.11+  
**主要依赖**：标准库 + 现有 `agentops` core/api/storage  
**存储**：复用 `InMemoryRepository`，新增轻量 operation records；不引入外部 DB  
**测试**：pytest contract tests + focused regression  
**目标平台**：本地/CI Python 后端  
**约束**：summary-only、no raw evidence、no external exporter write、no Runtime execution、backward compatible with P0 contracts

## 宪章检查

| 宪章门禁 | 计划响应 |
|----------|----------|
| AgentOps 不执行 Runtime | 只读 projection，不触发 Runtime 或 Agent 执行 |
| Evidence Vault 原文边界 | raw access operation 不返回原文，只返回 hash/ref/audit |
| Contract-first | 先登记 `runtime_contracts.py`，再实现 API/core 投影 |
| Store 不是事实源 | Store governance projection 只消费 AgentOps 摘要，不反推健康态 |
| AI-SDLC 单批提交 | 本批代码、测试、文档与执行日志合并为一次提交 |

## 项目结构

```text
src/agentops/core/operations.py                         # P1-B projection builders
src/agentops/api/operations.py                          # API wrappers
src/agentops/core/runtime_contracts.py                  # contract registry
src/agentops/storage/repository.py                      # operation records / DLQ reads
tests/contract/test_ao37_ct_p1_evidence_eval_cost_operations.py
specs/037-p1-evidence-eval-cost-operations/
```

## 阶段计划

### Phase 0：Formal baseline

**目标**：冻结 037 spec/plan/tasks/log，并同步 program truth。  
**产物**：037 formal docs、manifest truth snapshot。  
**验证方式**：`ai-sdlc adapter status`、`ai-sdlc run --dry-run`、`python -m ai_sdlc program truth sync --execute --yes`。  
**回退方式**：仅还原 037 docs/manifest，不触碰已合入 main 的 036。

### Phase 1：Contract registry + red tests

**目标**：新增 AO37 contract tests，先证明 registry 和投影缺口。  
**产物**：`test_ao37_ct_p1_evidence_eval_cost_operations.py`。  
**验证方式**：聚焦 pytest 预期红灯。  
**回退方式**：删除 AO37 新测试即可回到 baseline。

### Phase 2：P1-B projection implementation

**目标**：实现 Evidence/Eval/Budget/DLQ/Exporter/SLO/Store governance projection builders。  
**产物**：core/api/storage/runtime contracts 改动。  
**验证方式**：AO37 聚焦测试通过，AO32/AO34/AO35 回归通过。  
**回退方式**：回滚新增 `operations.py` 与 registry/storage 扩展。

### Phase 3：Close-out

**目标**：同步任务、执行日志、development summary 和 AI-SDLC close-check。  
**产物**：`development-summary.md`、更新 `tasks.md`、更新 `task-execution-log.md`。  
**验证方式**：ruff、pytest、AI-SDLC verify/close-check。  
**回退方式**：修复阻断后重跑同一门禁。

## 关键路径验证策略

| 关键路径 | 主验证方式 | 次验证方式 |
|----------|------------|------------|
| Contract registry | AO37-CT-001 | runtime contract unit tests |
| Evidence access raw boundary | AO37-CT-002 | JSON raw leak scan |
| EvalCase failure sample | AO37-CT-003 | AO32 evidence summary regression |
| Budget/SLO aggregation | AO37-CT-004/007 | AO31/AO32 runtime facts regression |
| DLQ/Exporter no write | AO37-CT-005/006 | AO34 outbox regression |
| Store governance display-only | AO37-CT-008 | AO32 Store summary regression |

## 开放问题

| 问题 | 状态 | 阻塞阶段 |
|------|------|----------|
| Console UI 是否进入 037 | 明确不进入，留给后续 UI work item | 不阻塞 |
| OTLP/OpenInference 是否真实发送 | 本批只做 dry-run projection，真实发送后续独立评估 | 不阻塞 |
| Eval scorer 是否执行模型评测 | 本批只登记 scorer_status 与 deterministic scorer plan | 不阻塞 |

## 实施顺序建议

1. 补 AO37 contract tests。
2. 登记 runtime contracts。
3. 扩展 repository 只读 records 和 P1-B operation records。
4. 实现 `core.operations` 与 `api.operations`。
5. 跑 AO37 + AO32/AO34/AO35 回归。
6. 更新任务/日志/summary，执行 close-check。
