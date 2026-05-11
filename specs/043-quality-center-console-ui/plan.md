---
related_doc:
  - "specs/043-quality-center-console-ui/spec.md"
  - "specs/042-quality-center-workbench/spec.md"
  - "specs/040-quality-lifecycle-analytics/spec.md"
  - "specs/041-quality-scorer-versioning/spec.md"
---
# 实施计划：Quality Center Console UI

**编号**：`043-quality-center-console-ui` | **日期**：2026-05-11 | **规格**：specs/043-quality-center-console-ui/spec.md

## 概述

043 将 042 的 `quality_center_workbench.v1` 投影接入浏览器 Console。交付重点是可视化和安全校验：页面展示质量摘要、scorer rollout 人工审批队列、review queue 和趋势摘要，但不执行 scorer、不自动 rollout、不写 Store、不发布通知。

## 技术背景

**语言/版本**：Python 3.11+、Vue 2 + Vite、Node contract tests  
**主要依赖**：现有 `agentops` API snapshot、`apps/agentops-console` 组件  
**存储**：复用 Console snapshot 与本地 mock/fallback，不引入新持久化  
**测试**：pytest contract + `npm test` Console contract  
**约束**：summary-only、no raw evidence/diff/prompt/terminal、manual review only、legacy snapshot safe fallback

## 宪章检查

| 宪章门禁 | 计划响应 |
|----------|----------|
| AgentOps 不执行 Runtime/scorer | UI 只展示摘要，不触发 scorer execution 或 Runtime action |
| Evidence/脱敏基线 | API client 和 contract test 拒绝 raw URL、diff、prompt、secret、PR 原文 |
| Contract-first | 后端 snapshot 字段对齐 042 `quality_center_workbench.v1` |
| Store 边界 | 页面只显示人工建议，不写 Store、不下架、不发布通知 |
| Legacy 安全 | 缺少 `qualityCenterWorkbench` 时生成只读 fallback，不推导自动动作 |

## 项目结构

```text
src/agentops/api/console_snapshot.py
apps/agentops-console/src/data/agentOpsApiClient.js
apps/agentops-console/src/data/mockAgentOpsData.js
apps/agentops-console/src/views/QualityCenterView.js
apps/agentops-console/src/styles.css
apps/agentops-console/tests/console-contract.test.mjs
tests/contract/test_ao4_ct_console_api.py
specs/043-quality-center-console-ui/
```

## 阶段计划

### Phase 0：Formal baseline

**目标**：冻结 043 spec/plan/tasks/log 并同步 program truth。  
**验证方式**：`ai-sdlc adapter status`、`ai-sdlc run --dry-run`、`python -m ai_sdlc program truth sync --execute --yes`。

### Phase 1：Snapshot contract

**目标**：后端 Console snapshot 增加 `qualityCenterWorkbench`，保持 summary-only。  
**验证方式**：AO4 Console API contract。

### Phase 2：Frontend validation and UI

**目标**：API client 校验/legacy fallback，QualityCenterView 渲染 AO42 工作台字段。  
**验证方式**：Console npm contract。

### Phase 3：Close-out

**目标**：同步任务、执行日志、development summary 和 AI-SDLC 约束。  
**验证方式**：ruff、pytest、npm test、AI-SDLC verify。

## 关键路径验证策略

| 关键路径 | 主验证方式 | 次验证方式 |
|----------|------------|------------|
| Snapshot shape | AO4 contract | Console npm validateSnapshot |
| Legacy fallback | Console npm contract | Browser manual smoke if server runs |
| No auto action | Console npm negative tests | raw leak scan |
| AO42 compatibility | AO42 contract regression | ruff |

## 开放问题

| 问题 | 状态 | 阻塞阶段 |
|------|------|----------|
| 是否执行真实 scorer | 不进入 043，保持人工审批展示 | 不阻塞 |
| 是否 Store 写回或通知 | 不进入 043 | 不阻塞 |
