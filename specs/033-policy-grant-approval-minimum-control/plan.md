---
related_doc:
  - "specs/031-agentops-runtime-governance-foundation/agentops-p0-p2-backlog.md"
  - "specs/002-agentops-policy-approval-vault/spec.md"
  - "specs/031-agentops-runtime-governance-foundation/spec.md"
---
# 实施计划：Policy Grant Approval Minimum Control

**编号**：`033-policy-grant-approval-minimum-control` | **日期**：2026-05-09 | **规格**：specs/033-policy-grant-approval-minimum-control/spec.md

## 概述

本计划以 contract-first 方式承接 `AO-P0-07`、`AO-P0-08`、`AO-P0-09`。033 不重做阶段 2 完整 Policy Center，而是在 031/032 Runtime 治理地基上提供最小可验证控制闭环：Runtime 先拿 PolicyDecision，approval 通过后签发可消费 Grant，Runtime 上报 Guardrail result 供 AgentOps 解释 blocked/warn/degraded。

## 技术背景

**语言/版本**：Python 3.11+，标准库 HTTP server，pytest。  
**主要依赖**：既有 `agentops.core.policy_engine`、`approvals`、`grants`、`runtime_ingestion`、`runtime_contracts`。  
**存储**：沿用 `InMemoryRepository`，新增 guardrail result fact 和 Grant remaining uses 更新。  
**测试**：新增 AO33 contract tests，回归 AO2/AO31/AO32。  
**目标平台**：本地、CI、macOS/Linux/Windows。  
**约束**：AgentOps 不执行 Agent、不 resume Runtime、不暴露 raw payload、不把不可用策略当成 allow。

## 宪章检查

| 宪章门禁 | 计划响应 |
|----------|----------|
| 接入真值优先 | 已执行 `uv run ai-sdlc run --dry-run`，后续 close-check 前同步 Program Truth |
| Contract-first | 先更新 spec/plan/tasks 与 registry，再实现 core/API/tests |
| 证据与权限红线 | Guardrail result 只展示摘要和 evidence_ref，不返回原文 |
| 不接管 Runtime | Policy/Grant/Guardrail 均为治理事实，Runtime 自行执行或暂停 |

## 项目结构

### 文档结构

```text
specs/033-policy-grant-approval-minimum-control/
├── spec.md
├── plan.md
├── tasks.md
└── task-execution-log.md
```

### 源码结构

```text
src/agentops/api/policy.py
src/agentops/api/grants.py
src/agentops/api/runtime.py
src/agentops/api/view_models.py
src/agentops/core/policy_engine.py
src/agentops/core/grants.py
src/agentops/core/runtime_contracts.py
src/agentops/core/runtime_ingestion.py
src/agentops/storage/repository.py
tests/contract/test_ao33_ct_policy_grant_guardrail_control.py
```

## 阶段计划

### Phase 0：研究与规格冻结

**目标**：从 backlog 选择 AO-P0-07/08/09，明确本批只做最小控制闭环。  
**产物**：spec.md / plan.md / tasks.md。  
**验证方式**：文档对账 + Program Truth Sync。  
**回退方式**：若范围膨胀，退回仅 PolicyDecision + Grant，不做 P1 管理台。

### Phase 1：PolicyDecision v1 最小 API

**目标**：提供 P0 五态裁决和 stable schema。  
**产物**：`evaluate_policy_decision_v1`、contract tests。  
**验证方式**：AO33-CT-001/002。  
**回退方式**：保留既有 `evaluate_policy_check` 行为。

### Phase 2：CapabilityGrant 最小绑定和审计

**目标**：补齐 Grant required fields、remaining uses、消费审计和拒绝路径。  
**产物**：`core/grants.py`、`models/grants.py`、repository 更新。  
**验证方式**：AO33-CT-003/004 + AO2 回归。  
**回退方式**：仅拒绝不完整 Grant，不改变 approval 状态机。

### Phase 3：Guardrail Result 接入

**目标**：runtime ingestion 支持 `guardrail_result.v1`，Run Detail / Timeline 展示摘要。  
**产物**：contract registry、ingestion、repository、view model。  
**验证方式**：AO33-CT-005/006 + AO31/AO32 回归。  
**回退方式**：保留 trace span guardrail 展示，不接收新 event type。

## 工作流计划

### 工作流 A：策略裁决

**范围**：Policy request -> PolicyDecisionV1。  
**影响范围**：`api/policy.py`、`core/policy_engine.py`。  
**验证方式**：contract tests + existing policy unit tests。  
**回退方式**：保留旧 `evaluate_policy_check`。

### 工作流 B：授权签发与消费

**范围**：approved approval -> Grant -> consumption audit。  
**影响范围**：`core/grants.py`、`storage/repository.py`。  
**验证方式**：AO33 + AO2 Grant 回归。  
**回退方式**：拒绝不满足绑定的 Grant。

### 工作流 C：Guardrail 事实接入

**范围**：Runtime event -> GuardrailResult fact -> Run/Timeline projection。  
**影响范围**：`runtime_contracts.py`、`runtime_ingestion.py`、`view_models.py`。  
**验证方式**：AO33 + AO31 runtime ingestion 回归。  
**回退方式**：DLQ/拒绝不合规事件。

## 关键路径验证策略

| 关键路径 | 主验证方式 | 次验证方式 |
|----------|------------|------------|
| PolicyDecision 五态 | AO33-CT-001/002 | AO2 policy 回归 |
| Grant 绑定和剩余次数 | AO33-CT-003/004 | AO2 grant 回归 |
| Guardrail result 接入 | AO33-CT-005/006 | AO31/AO32 回归 |
| AI-SDLC 约束 | `uv run ai-sdlc verify constraints` | `workitem close-check` |

## 开放问题

| 问题 | 状态 | 阻塞阶段 |
|------|------|----------|
| 是否做 P1 Policy 管理台 | 不做，进入 P1-A | 不阻塞 |
| 是否让 AgentOps resume Runtime | 不做，Runtime 自行消费 Grant | 不阻塞 |

## 实施顺序建议

1. 冻结 AO33 文档和 tests 红灯。
2. 实现 PolicyDecision v1 和 Grant 字段/消费。
3. 实现 Guardrail result ingestion 和投影。
4. 跑定向回归、约束校验、归档、提交和 PR。
