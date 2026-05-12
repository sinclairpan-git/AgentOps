# 实施计划：Quality Center External Intake Portfolio

**功能编号**：`051-quality-center-external-intake-portfolio`  
**日期**：2026-05-12  
**阶段**：execute

## 概要

AO51 将 050 留下的跨 agent/version summary 非目标补齐为 Quality Center 顶层 portfolio。实现只复用现有 repository receipt lookup、per-agent health 和 workbench agent_refs，不新增 HTTP route、不引入外部存储、不改变 scorer execution。

## 技术上下文

**语言/运行时**：Python 3.11  
**测试**：pytest contract tests  
**存储**：复用 `InMemoryRepository` external intake receipts  
**约束**：summary-only、read-only、no-auto-action、URI identity redaction

## 改动范围

```text
src/agentops/core/runtime_contracts.py
src/agentops/core/operations.py
src/agentops/api/operations.py
tests/contract/test_ao51_ct_quality_center_external_intake_portfolio.py
specs/051-quality-center-external-intake-portfolio/*
.ai-sdlc/work-items/051-quality-center-external-intake-portfolio/resume-pack.yaml
```

## 阶段

### Phase 0 - Formal baseline

冻结 spec/plan/tasks/log/summary，明确 AO51 仅承接跨 scope portfolio，HTTP route 和 UI 后续另拆。

### Phase 1 - Contract and projection

登记 `quality_center_external_intake_portfolio.v1`，扩展 `quality_center_workbench.v1` required fields，新增 backend portfolio builder 并接入 workbench。

### Phase 2 - Contract tests

新增 AO51 tests，覆盖 multi-scope receiving/no_receipts/needs_review、required missing scopes、URI no-raw echo、no new execution。

### Phase 3 - Verification

运行 AO50/AO51 定向测试、ruff、format check、AI-SDLC constraints 和 close-check；更新 execution log 与 development summary。

## 风险与边界

| 风险 | 控制 |
|---|---|
| Portfolio 泄露 URI/raw marker | 全部输出走 `_safe_label`、hash identity 和 no-raw-leaks tests |
| 聚合误触发 scorer execution | 测试记录 execution count 前后不变 |
| 与 050 per-agent health 漂移 | Portfolio 复用 workbench agent_summaries 的 health，不重算业务状态 |
