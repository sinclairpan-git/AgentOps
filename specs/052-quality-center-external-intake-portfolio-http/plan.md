# 实施计划：Quality Center External Intake Portfolio HTTP

**功能编号**：`052-quality-center-external-intake-portfolio-http`  
**日期**：2026-05-12  
**阶段**：execute

## 概要

AO52 将 051 的 Quality Center external intake portfolio 暴露为只读 HTTP endpoint。Route 只解析 query、校验权限、构造 safe agent_refs 并调用 051 builder；不新增业务状态机，不执行 scorer，不读取 raw material。

## 技术上下文

**语言/运行时**：Python 3.11  
**HTTP**：项目标准库 `BaseHTTPRequestHandler` server  
**测试**：pytest contract tests  
**存储**：复用 `InMemoryRepository` external intake receipts  
**约束**：summary-only、read-only、no-auto-action、production scope/audit、URI identity redaction

## 改动范围

```text
src/agentops/api/app.py
src/agentops/api/server.py
src/agentops/core/runtime_contracts.py
tests/contract/test_ao52_ct_quality_center_external_intake_portfolio_http.py
specs/052-quality-center-external-intake-portfolio-http/*
.ai-sdlc/work-items/052-quality-center-external-intake-portfolio-http/resume-pack.yaml
program-manifest.yaml
.ai-sdlc/project/config/project-state.yaml
```

## 阶段

### Phase 0 - Formal baseline

冻结 spec/plan/tasks/log/summary，明确 052 只做 HTTP read route，Console UI 后续另拆。

### Phase 1 - Contract and discovery

登记 `quality_center_external_intake_portfolio_http.v1`，在 `create_app()` 中声明 route。

### Phase 2 - HTTP handler

实现 `GET /v1/quality/center/external-intake/portfolio`，支持 repeated `scope` 和 `required_scope`，生产模式要求 `quality.scorer.intake.read`，写最小 audit。

### Phase 3 - Verification

新增 AO52 contract tests，回归 AO50/AO51，运行 ruff、constraints、truth sync 和 close-check。

## 风险与边界

| 风险 | 控制 |
|---|---|
| GET query 泄露 URI/raw marker | response 使用 051 safe labels；audit metadata 不记录 query 原文 |
| route 重算逻辑与 051 漂移 | route 只构造 agent_refs 并调用 `get_quality_center_external_intake_portfolio()` |
| required scope 自动触发动作 | tests 锁定 automatic action flags 全 false |
