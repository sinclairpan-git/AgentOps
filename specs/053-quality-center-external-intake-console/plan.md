# 实施计划：Quality Center External Intake Console

**功能编号**：`053-quality-center-external-intake-console`  
**日期**：2026-05-12  
**阶段**：execute

## 概要

AO53 将 050-052 的 external intake summary 接入 Console Quality Center 页面。实现只扩展 snapshot/view-model 和前端展示，不新增执行路径或写操作。

## 技术上下文

**后端**：`src/agentops/api/console_snapshot.py`  
**前端**：Vue 2 Options API，`apps/agentops-console/src/views/QualityCenterView.js`  
**测试**：pytest contract tests、`npm test`、Browser smoke  
**约束**：summary-only、read-only、legacy fallback、no-auto-action、中文 UI

## 改动范围

```text
src/agentops/api/console_snapshot.py
tests/contract/test_ao4_ct_console_api.py
apps/agentops-console/src/data/agentOpsApiClient.js
apps/agentops-console/src/views/QualityCenterView.js
apps/agentops-console/tests/console-contract.test.mjs
specs/053-quality-center-external-intake-console/*
.ai-sdlc/work-items/053-quality-center-external-intake-console/resume-pack.yaml
program-manifest.yaml
```

## 阶段

### Phase 0 - Formal baseline

冻结 spec/plan/tasks/log/summary，明确只做 Console 展示，不调用 scorer、不写 Store。

### Phase 1 - Snapshot and API validation

扩展 Console snapshot external intake defaults；API client 增加 validation 和 legacy fallback。

### Phase 2 - UI rendering

Quality Center 页面增加 external intake metrics、portfolio detail、latest receipts、required missing scopes 和 per-agent intake column。

### Phase 3 - Verification

运行 pytest、npm test、ruff、Browser smoke、truth sync 和 close-check。

## 风险与边界

| 风险 | 控制 |
|---|---|
| 旧快照缺字段导致页面崩溃 | API client legacy fallback 补 safe empty external intake fields |
| UI 误导为自动修复/发布 | 文案和 tests 锁定 no-auto-action flags |
| raw/URL 泄露 | snapshot safe text + API validation forbidden material tests |
