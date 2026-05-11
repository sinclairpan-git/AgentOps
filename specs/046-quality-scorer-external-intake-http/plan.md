# 实施计划：Quality Scorer External Intake HTTP

## 摘要

AO46 把 AO45 已验证的 external scorer summary intake 从 Python API 扩展到本地标准库 HTTP handler。实现重点是 route envelope、生产 scope、最小 audit 和 contract registry；业务校验继续由 AO45 core intake 承担，避免第二套 scorer 入口逻辑漂移。

## 技术上下文

**语言/运行时**：Python 3.11+  
**HTTP 边界**：`src/agentops/api/server.py` 标准库 `ThreadingHTTPServer` handler  
**数据层**：`InMemoryRepository`，复用 AO45 external intake receipt 和 scorer execution records  
**约束**：summary-only；不执行 scorer；不访问 raw；不自动 rollout/Store write/notification；audit 不记录 body

## 影响文件

```text
src/agentops/api/app.py                              # route discovery
src/agentops/api/auth.py                             # production scope
src/agentops/api/server.py                           # HTTP route
src/agentops/core/runtime_contracts.py               # AO46 contract registry
tests/contract/test_ao46_ct_quality_scorer_external_intake_http.py
specs/046-quality-scorer-external-intake-http/*
program-manifest.yaml
.ai-sdlc/project/config/project-state.yaml
.ai-sdlc/state/checkpoint.yml
```

## 实施阶段

### Phase 1：formal baseline

冻结 046 spec/plan/tasks/log/summary，明确该批只补 HTTP/webhook 边界，不扩大到真实外部 scorer execution hosting。

### Phase 2：route and contract

登记 `quality_scorer_external_intake_http.v1`；新增 route discovery；扩展生产 scope；实现 `POST /v1/quality/scorers/external-intake`，解析 body/header 后调用 AO45 core intake。

### Phase 3：contract tests and verification

新增 AO46 HTTP contract tests，回归 AO45，运行 ruff/pytest/AI-SDLC gates，更新 truth snapshot 与 close evidence。

## 风险与缓解

| 风险 | 缓解 |
|---|---|
| HTTP route 重新实现 intake 校验导致与 AO45 漂移 | route 只做 envelope 解析，所有核心校验调用 AO45 |
| audit 意外记录 raw body | audit API 只传 action/outcome/resource/error/scope，contract test 读取 JSONL 验证 forbidden markers 不存在 |
| 生产 scope 过宽 | 新增 `quality.scorer.intake.write`，只授予 admin/operator/ingestor |
| HTTP status 与 error registry 不一致 | AO46 tests 锁定 400/401/403/409/202 映射 |

## 非目标

- 不新增真实 webhook secret verification algorithm。
- 不新增外部 scorer runner、queue、scheduler 或 callback。
- 不新增 Console UI 页面。
- 不自动触发 rollout、Store write、通知或 lifecycle action。
