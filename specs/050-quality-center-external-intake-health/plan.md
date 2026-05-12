# 实施计划：Quality Center External Intake Health

## 摘要

AO50 把 AO49 的 external intake 健康信息接入 Quality Center backend workbench。新增能力只读取 receipt metadata，输出每个 agent/version 的 intake health 和 workbench 级 panel，帮助人工判断外部 scorer 输入是否健康；不执行 scorer、不 replay payload、不自动 rollout。

## 技术上下文

**语言/运行时**：Python 3.11+  
**核心聚合**：`src/agentops/core/operations.py::build_quality_center_workbench`  
**数据层**：复用 `InMemoryRepository.quality_scorer_external_receipt_records()`  
**约束**：summary-only、hash scope lookup、no raw echo、no auto action

## 影响文件

```text
src/agentops/core/operations.py
src/agentops/core/runtime_contracts.py
tests/contract/test_ao50_ct_quality_center_external_intake_health.py
specs/050-quality-center-external-intake-health/*
program-manifest.yaml
.ai-sdlc/project/config/project-state.yaml
.ai-sdlc/state/checkpoint.yml
```

## 实施阶段

### Phase 1：formal baseline

冻结 050 spec/plan/tasks/log/summary，明确本阶段只做 Quality Center backend 聚合，不新增 HTTP route 或 Console UI。

### Phase 2：contract and projection

登记 `quality_center_external_intake_health.v1`；扩展 `quality_center_workbench.v1` 输出 `external_intake_panel`；为每个 agent summary 增加 `external_intake_health`。

### Phase 3：manual review and safety

当 `external_intake_required=true` 且无 receipt，生成 `external_intake` review item；保持所有 automatic action flags 为 false，URI identity 只通过 hash 匹配不回显。

### Phase 4：verification

新增 AO50 contract tests，回归 AO42/AO49/AO50，运行 ruff、AI-SDLC constraints/truth/close-check。

## 风险与缓解

| 风险 | 缓解 |
|---|---|
| Workbench 查询被误解为触发 scorer | test 比较 execution record count；输出 `scorer_execution_performed=false` |
| 默认无 receipt 导致过多 review queue | 只有 `external_intake_required=true` 或 `needs_review` 才进入队列 |
| URI-style identity 泄露 | 继续复用 `_safe_label` 和 identity hash；AO50 no-raw test 覆盖 |
| 扩展 workbench 破坏既有消费者 | 新字段向后兼容添加，并回归 AO42 |

## 非目标

- 不新增 external intake HTTP route。
- 不新增 Console UI。
- 不支持跨 agent/version 汇总。
- 不执行 scorer、rollout、Store write、notification 或 publish。
