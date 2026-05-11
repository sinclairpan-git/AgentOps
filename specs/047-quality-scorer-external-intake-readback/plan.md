# 实施计划：Quality Scorer External Intake Readback

## 摘要

AO47 在 AO46 HTTP intake 之后补只读 receipt readback。外部 scorer 可以在 retry/replay 场景按完整 agent/version/idempotency key 查询接收结果；AgentOps 不重复写 execution evidence，不回放 payload，不扩大自动动作边界。

## 技术上下文

**语言/运行时**：Python 3.11+  
**HTTP 边界**：`src/agentops/api/server.py` 标准库 handler  
**数据层**：`InMemoryRepository.quality_scorer_external_receipt_by_idempotency()`  
**约束**：完整 scope 查询；summary-only；只读；不记录 request body；不执行 scorer

## 影响文件

```text
src/agentops/api/app.py
src/agentops/api/auth.py
src/agentops/api/server.py
src/agentops/core/runtime_contracts.py
tests/contract/test_ao47_ct_quality_scorer_external_intake_readback.py
specs/047-quality-scorer-external-intake-readback/*
program-manifest.yaml
.ai-sdlc/project/config/project-state.yaml
.ai-sdlc/state/checkpoint.yml
```

## 实施阶段

### Phase 1：formal baseline

冻结 047 spec/plan/tasks/log/summary，明确只做 receipt readback，不新增外部 scorer 执行、重放或自动 rollout。

### Phase 2：route and contract

登记 `quality_scorer_external_intake_readback.v1`；新增 `quality.scorer.intake.read` scope；实现 `GET /v1/quality/scorers/external-intake` query readback。

### Phase 3：verification

新增 AO47 contract tests，回归 AO45/AO46/AO47 与完整 pytest，运行 AI-SDLC truth/constraints/close-check。

## 风险与缓解

| 风险 | 缓解 |
|---|---|
| key-only readback 泄露跨 scope receipt metadata | HTTP route 强制 agent_id/version/idempotency_key 三者齐全 |
| readback 意外重写 execution evidence | contract test 比较查询前后 execution record count |
| audit 记录 idempotency payload 或 raw body | audit 仍只传 action/outcome/resource/error/scope，并用 JSONL 断言 forbidden marker 不存在 |
| 与 046 POST route 混淆 | 同一路径按 HTTP method 分流；create_app 分别声明 POST/GET |

## 非目标

- 不提供 list/search all receipts。
- 不支持 key-only 或 partial-scope HTTP readback。
- 不执行 scorer，不 replay payload。
- 不新增 Console UI。
