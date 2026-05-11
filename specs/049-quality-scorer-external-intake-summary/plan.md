# 实施计划：Quality Scorer External Intake Summary

## 摘要

AO49 在 AO48 receipt index 后补只读 intake health summary。运维工具和 Quality Center 可以按完整 agent/version scope 查看最近 external scorer intake 的健康摘要；AgentOps 不暴露 key-only 汇总，不回放 payload，不新增 execution evidence。

## 技术上下文

**语言/运行时**：Python 3.11+  
**HTTP 边界**：`src/agentops/api/server.py` 标准库 handler  
**数据层**：复用 `InMemoryRepository.quality_scorer_external_receipt_records()`  
**约束**：完整 scope 查询；summary-only；只读；不记录 query payload；不执行 scorer

## 影响文件

```text
src/agentops/api/app.py
src/agentops/api/server.py
src/agentops/core/runtime_contracts.py
tests/contract/test_ao49_ct_quality_scorer_external_intake_summary.py
specs/049-quality-scorer-external-intake-summary/*
program-manifest.yaml
.ai-sdlc/project/config/project-state.yaml
.ai-sdlc/state/checkpoint.yml
```

## 实施阶段

### Phase 1：formal baseline

冻结 049 spec/plan/tasks/log/summary，明确只做 intake summary，不新增 scorer 执行、payload replay、自动 rollout 或 Console UI。

### Phase 2：route and contract

登记 `quality_scorer_external_intake_summary.v1`；实现 `GET /v1/quality/scorers/external-intake/summary`，复用 `quality.scorer.intake.read` scope 和 AO48 scoped receipt listing。

### Phase 3：verification

新增 AO49 contract tests，回归 AO45/AO46/AO47/AO48/AO49 与完整 pytest，运行 AI-SDLC truth/constraints/close-check。

## 风险与缓解

| 风险 | 缓解 |
|---|---|
| summary 泄露 raw query 或 URI identity | lookup 使用原始 query，response 通过 safe label redaction；audit 不记录 query string |
| summary 被误用为自动 rollout 信号 | 输出显式声明 no-auto-action guardrails |
| 无 receipt 时伪造健康态 | 明确返回 `health_state=no_receipts` |
| summary 意外新增 execution evidence | contract test 比较查询前后 execution record count |

## 非目标

- 不支持 key-only 或 partial-scope summary。
- 不返回 external_result 或 raw payload。
- 不执行 scorer，不 replay payload。
- 不新增 Console UI。
