# 实施计划：Quality Scorer External Intake Index

## 摘要

AO48 在 AO47 单条 readback 后补最近 receipt index。外部 scorer 运维工具可以按完整 agent/version scope 查看最近接收状态；AgentOps 不暴露 key-only 全局索引，不回放 payload，不新增 execution evidence。

## 技术上下文

**语言/运行时**：Python 3.11+  
**HTTP 边界**：`src/agentops/api/server.py` 标准库 handler  
**数据层**：`InMemoryRepository.quality_scorer_external_receipt_records()`  
**约束**：完整 scope 查询；summary-only；只读；不记录 query payload；不执行 scorer

## 影响文件

```text
src/agentops/api/app.py
src/agentops/api/server.py
src/agentops/core/runtime_contracts.py
src/agentops/storage/repository.py
tests/contract/test_ao48_ct_quality_scorer_external_intake_index.py
specs/048-quality-scorer-external-intake-index/*
program-manifest.yaml
.ai-sdlc/project/config/project-state.yaml
.ai-sdlc/state/checkpoint.yml
```

## 实施阶段

### Phase 1：formal baseline

冻结 048 spec/plan/tasks/log/summary，明确只做 receipt index，不新增 scorer 执行、payload replay、自动 rollout 或 Console UI。

### Phase 2：route and contract

登记 `quality_scorer_external_intake_index.v1`；实现 repository scoped listing；实现 `GET /v1/quality/scorers/external-intake/index`，复用 `quality.scorer.intake.read` scope。

### Phase 3：verification

新增 AO48 contract tests，回归 AO45/AO46/AO47/AO48 与完整 pytest，运行 AI-SDLC truth/constraints/close-check。

## 风险与缓解

| 风险 | 缓解 |
|---|---|
| index 泄露跨 scope receipt | HTTP route 和 repository 均按完整 agent/version scope 过滤 |
| limit 被用于 audit/query payload 泄露 | audit 只记录 action/outcome/resource/error/scope，不记录 query string |
| index 意外新增 execution evidence | contract test 比较查询前后 execution record count |
| 与 AO47 readback 混淆 | index 使用独立 `/index` route；单条 readback 保持原路径 |

## 非目标

- 不支持 key-only 或 partial-scope index。
- 不返回 external_result 或 raw payload。
- 不执行 scorer，不 replay payload。
- 不新增 Console UI。
