---
related_doc:
  - "/Users/sinclairpan/project/AI-Native底座开发文档/AgentOps_项目_PRD.md"
  - "specs/032-evidence-health-summary-loop/spec.md"
  - "specs/037-p1-evidence-eval-cost-operations/spec.md"
  - "specs/039-p2-ecosystem-governance/spec.md"
---
# 实施计划：Quality Lifecycle Analytics

**编号**：`040-quality-lifecycle-analytics` | **日期**：2026-05-10 | **规格**：specs/040-quality-lifecycle-analytics/spec.md

## 概述

AO40 承接 PRD 阶段 4/5，把 AgentOps 的质量与采纳能力从 Console 早期展示推进为后端 summary-only contracts：质量评分、采纳 ROI、生命周期建议和月报摘要。第一批只做 backend projections/API，不自动修改 Store、不执行下架、不读取 raw evidence。

## 技术背景

**语言/版本**：Python 3.11+  
**主要依赖**：标准库 + 现有 `agentops` core/api/storage  
**存储**：复用 `InMemoryRepository` runtime facts / eval cases / summaries；adoption 输入为调用方提供的摘要指标  
**测试**：pytest contract tests + focused regression  
**约束**：no raw evidence/diff/prompt、no automatic lifecycle action、no Store write、backward compatible with P0/P1/P2 contracts

## 宪章检查

| 宪章门禁 | 计划响应 |
|----------|----------|
| AgentOps 不执行 Runtime | 质量和采纳只消费 summary facts，不触发 Runtime |
| Evidence/脱敏基线 | 输出只保留 hash/ref/summary，不返回 raw evidence、prompt、diff |
| Contract-first | 先登记 `runtime_contracts.py`，再实现 API/core 投影 |
| Store 边界 | lifecycle recommendation 不写回 Store、不自动 disable |
| AI-SDLC 单批提交 | 本批代码、测试、文档与执行日志合并为一次提交 |

## 项目结构

```text
src/agentops/core/operations.py                         # AO40 projection builders
src/agentops/api/operations.py                          # API wrappers
src/agentops/core/runtime_contracts.py                  # contract registry
tests/contract/test_ao40_ct_quality_lifecycle_analytics.py
specs/040-quality-lifecycle-analytics/
```

## 阶段计划

### Phase 0：Formal baseline

**目标**：冻结 040 spec/plan/tasks/log，并同步 program truth。  
**验证方式**：`ai-sdlc adapter status`、`ai-sdlc run --dry-run`、`python -m ai_sdlc program truth sync --execute --yes`。

### Phase 1：Contract registry + red tests

**目标**：新增 AO40 contract tests，证明 quality/adoption/lifecycle/monthly report 缺口。  
**验证方式**：AO40 聚焦 pytest。

### Phase 2：Quality lifecycle projections

**目标**：实现 quality score、adoption ROI、lifecycle recommendation、monthly report builders。  
**验证方式**：AO40 聚焦测试通过，AO32/AO37/AO39 回归通过。

### Phase 3：Close-out

**目标**：同步任务、执行日志、development summary 和 AI-SDLC close-check。  
**验证方式**：ruff、pytest、AI-SDLC verify/close-check。

## 关键路径验证策略

| 关键路径 | 主验证方式 | 次验证方式 |
|----------|------------|------------|
| Contract registry | AO40-CT-001 | runtime contract validation |
| Quality score evidence boundary | AO40-CT-002 | raw leak scan |
| Adoption ROI summary-only | AO40-CT-003 | unsafe field redaction |
| Lifecycle no-action guardrail | AO40-CT-004 | AO39 risk regression |
| Monthly report no publish | AO40-CT-005 | AO37/AO39 summary regression |

## 开放问题

| 问题 | 状态 | 阻塞阶段 |
|------|------|----------|
| 是否实现完整 scorer engine | 本批只做 deterministic projection，不做 scorer execution | 不阻塞 |
| 是否做 Console 页面 | 本批不做 UI | 不阻塞 |
| 是否自动写回 Store | 明确不进入，保持人工建议 | 不阻塞 |
