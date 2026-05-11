---
related_doc:
  - "/Users/sinclairpan/project/AI-Native底座开发文档/AgentOps_项目_PRD.md"
  - "specs/037-p1-evidence-eval-cost-operations/spec.md"
  - "specs/040-quality-lifecycle-analytics/spec.md"
---
# 实施计划：Quality Scorer Versioning

**编号**：`041-quality-scorer-versioning` | **日期**：2026-05-10 | **规格**：specs/041-quality-scorer-versioning/spec.md

## 概述

AO41 承接 PRD Eval Flywheel 的 P1 缺口，把 037 的 EvalCase 与 040 的质量评分投影连接到基础 scorer 管理：scorer version 基线、baseline/candidate 对比、人工审批建议。第一批只做 backend contracts/API，不执行真实 scorer、不自动 rollout、不读取原文。

## 技术背景

**语言/版本**：Python 3.11+  
**主要依赖**：标准库 + 现有 `agentops` core/api/storage  
**存储**：复用 `InMemoryRepository` runtime facts / eval cases；scorer 输入为调用方提供的摘要模板参数  
**测试**：pytest contract tests + focused regression  
**约束**：no raw evidence/diff/prompt、no automatic rollout、no Store write、backward compatible with AO37/AO40

## 宪章检查

| 宪章门禁 | 计划响应 |
|----------|----------|
| AgentOps 不执行 Runtime | scorer comparison 只读 EvalCase summary，不触发 Runtime |
| Evidence/脱敏基线 | 输出只保留 id/hash/ref/summary，不返回 raw evidence、prompt、diff |
| Contract-first | 先登记 `runtime_contracts.py`，再实现 API/core 投影 |
| Store 边界 | comparison 只给人工 rollout 建议，不写 Store、不切模板 |
| AI-SDLC 单批提交 | 本批代码、测试、文档与执行日志合并为一次提交 |

## 项目结构

```text
src/agentops/core/operations.py                         # AO41 projection builders
src/agentops/api/operations.py                          # API wrappers
src/agentops/core/runtime_contracts.py                  # contract registry
tests/contract/test_ao41_ct_quality_scorer_versioning.py
specs/041-quality-scorer-versioning/
```

## 阶段计划

### Phase 0：Formal baseline

**目标**：冻结 041 spec/plan/tasks/log，并同步 program truth。  
**验证方式**：`ai-sdlc adapter status`、`ai-sdlc run --dry-run`、`python -m ai_sdlc program truth sync --execute --yes`。

### Phase 1：Contract registry + red tests

**目标**：新增 AO41 contract tests，证明 scorer version 与 scorer comparison 缺口。  
**验证方式**：AO41 聚焦 pytest。

### Phase 2：Scorer version/comparison projections

**目标**：实现 quality scorer version 和 quality scorer comparison builders。  
**验证方式**：AO41 聚焦测试通过，AO37/AO40 回归通过。

### Phase 3：Close-out

**目标**：同步任务、执行日志、development summary 和 AI-SDLC close-check。  
**验证方式**：ruff、pytest、AI-SDLC verify/close-check。

## 关键路径验证策略

| 关键路径 | 主验证方式 | 次验证方式 |
|----------|------------|------------|
| Contract registry | AO41-CT-001 | runtime contract validation |
| Scorer version boundary | AO41-CT-002 | raw leak scan |
| Comparison summary-only | AO41-CT-003 | EvalCase filtered by agent/version |
| Insufficient evidence guardrail | AO41-CT-004 | invalid threshold regression |
| AO37/AO40 compatibility | focused regression | AI-SDLC constraints |

## 开放问题

| 问题 | 状态 | 阻塞阶段 |
|------|------|----------|
| 是否执行真实 scorer | 本批只做 deterministic summary projection，不执行 scorer | 不阻塞 |
| 是否自动 rollout candidate | 明确不进入，保持人工审批 | 不阻塞 |
| 是否更新 Console UI | 本批不做 UI | 不阻塞 |
