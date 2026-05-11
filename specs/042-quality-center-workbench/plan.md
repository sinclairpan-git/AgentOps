---
related_doc:
  - "/Users/sinclairpan/project/AI-Native底座开发文档/AgentOps_项目_PRD.md"
  - "specs/040-quality-lifecycle-analytics/spec.md"
  - "specs/041-quality-scorer-versioning/spec.md"
---
# 实施计划：Quality Center Workbench

**编号**：`042-quality-center-workbench` | **日期**：2026-05-11 | **规格**：specs/042-quality-center-workbench/spec.md

## 概述

AO42 承接 PRD Quality Center 页面目标，把 AO40 质量生命周期与 AO41 scorer versioning 汇总为一个 backend workbench contract。第一批只做后端投影/API，不做浏览器 UI、不执行真实 scorer、不自动 rollout、不写 Store。

## 技术背景

**语言/版本**：Python 3.11+  
**主要依赖**：标准库 + 现有 `agentops` core/api/storage  
**存储**：复用 `InMemoryRepository` runtime facts / eval cases；agent_refs 由调用方提供摘要配置  
**测试**：pytest contract tests + focused regression  
**约束**：no raw evidence/diff/prompt、no automatic rollout/lifecycle action、no Store write、backward compatible with AO40/AO41

## 宪章检查

| 宪章门禁 | 计划响应 |
|----------|----------|
| AgentOps 不执行 Runtime | workbench 只读 summary facts，不触发 Runtime |
| Evidence/脱敏基线 | 输出只保留 summary/id/state，不返回 raw evidence、prompt、diff |
| Contract-first | 先登记 `runtime_contracts.py`，再实现 API/core 投影 |
| Store 边界 | workbench 只给人工建议，不写 Store、不下架 |
| AI-SDLC 单批提交 | 本批代码、测试、文档与执行日志合并为一次提交 |

## 项目结构

```text
src/agentops/core/operations.py                         # AO42 workbench builder
src/agentops/api/operations.py                          # API wrapper
src/agentops/core/runtime_contracts.py                  # contract registry
tests/contract/test_ao42_ct_quality_center_workbench.py
specs/042-quality-center-workbench/
```

## 阶段计划

### Phase 0：Formal baseline

**目标**：冻结 042 spec/plan/tasks/log，并同步 program truth。  
**验证方式**：`ai-sdlc adapter status`、`ai-sdlc run --dry-run`、`python -m ai_sdlc program truth sync --execute --yes`。

### Phase 1：Contract registry + red tests

**目标**：新增 AO42 contract tests，证明 Quality Center workbench 缺口。  
**验证方式**：AO42 聚焦 pytest。

### Phase 2：Quality Center projection

**目标**：实现 quality center workbench builder，组合 quality score、lifecycle、scorer comparison 和 monthly trend summary。  
**验证方式**：AO42 聚焦测试通过，AO40/AO41 回归通过。

### Phase 3：Close-out

**目标**：同步任务、执行日志、development summary 和 AI-SDLC close-check。  
**验证方式**：ruff、pytest、AI-SDLC verify/close-check。

## 关键路径验证策略

| 关键路径 | 主验证方式 | 次验证方式 |
|----------|------------|------------|
| Contract registry | AO42-CT-001 | runtime contract validation |
| Quality summary aggregation | AO42-CT-002 | AO40 regression |
| Scorer rollout queue | AO42-CT-003 | AO41 regression |
| Malformed input / no raw leak | AO42-CT-004 | raw leak scan |
| AI-SDLC close-out | close-check | constraints |

## 开放问题

| 问题 | 状态 | 阻塞阶段 |
|------|------|----------|
| 是否做浏览器 UI | 本批只做 backend workbench contract | 不阻塞 |
| 是否执行真实 scorer | 本批不做 scorer execution | 不阻塞 |
| 是否自动 rollout 或 Store 写回 | 明确不进入，保持人工审批 | 不阻塞 |
