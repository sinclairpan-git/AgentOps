---
related_doc:
  - "specs/031-agentops-runtime-governance-foundation/agentops-p0-p2-backlog.md"
  - "specs/002-agentops-policy-approval-vault/spec.md"
  - "specs/013-approval-grant-workbench/spec.md"
  - "specs/033-policy-grant-approval-minimum-control/spec.md"
---
# 实施计划：P1 Approval Policy Grant Operations

**编号**：`036-p1-approval-policy-grant-operations` | **日期**：2026-05-10 | **规格**：specs/036-p1-approval-policy-grant-operations/spec.md

## 概述

AO36 是 P0 完整验收后的第一组 P1 运营能力，承接 backlog 的 P1-A。它把 P0 的最小 PolicyDecision / Approval / CapabilityGrant 扩展为可运营的审批队列、策略版本管理和 Grant 生命周期投影。实现仍保持 AgentOps 的治理边界：只登记、解释、投影和审计事实，不执行 Runtime、不加载 Agent 包、不直接变更外部 IAM。

## 技术背景

**语言/版本**：Python 3.11+  
**主要依赖**：标准库、pytest、ruff、AI-SDLC CLI  
**存储**：复用 `InMemoryRepository`，新增 P1 policy/approval/grant operation records；不引入外部 DB  
**测试**：AO36 contract tests + AO2/AO13/AO33/AO35 定向回归  
**约束**：summary-only projection；不暴露 raw payload；不绕过 approval binding；不把 P1 操作面提升为 Runtime 执行器

## 宪章检查

| 宪章门禁 | 计划响应 |
|----------|----------|
| Contract-first | 先冻结 AO36 contract tests 和 runtime_contracts registry，再实现操作面。 |
| Source truth | 036 formal docs 位于 `specs/036-p1-approval-policy-grant-operations/`，并同步 `program-manifest.yaml`。 |
| Runtime boundary | Approval/Policy/Grant operations 只管理治理状态，不执行 Runtime。 |
| Evidence safety | 所有投影只返回摘要、状态、引用和 audit_id，不返回 raw payload 或 secret。 |
| Compatibility | AO2/AO13/AO33/AO35 必须继续通过。 |

## 项目结构

```text
src/agentops/core/runtime_contracts.py                 # P1 governance operations registry
src/agentops/core/approvals.py                         # Approval operation state machine
src/agentops/core/grants.py                            # Grant lifecycle revoke/expire/impact
src/agentops/core/policy_engine.py                     # Policy set version helpers if needed
src/agentops/api/approvals.py                          # Approval operation API wrapper
src/agentops/api/grants.py                             # Grant lifecycle API wrapper
src/agentops/api/policy.py                             # Policy operations projection
src/agentops/storage/repository.py                     # P1 operation records
tests/contract/test_ao36_ct_p1_governance_operations.py
specs/036-p1-approval-policy-grant-operations/
```

## 阶段计划

### Phase 0：Formal baseline

冻结 AO36 spec/plan/tasks/log，并将 manifest 加入新工作项。明确 P1-A 承接 AO-P1-01/02/03，P2 能力不进入本工作项。

### Phase 1：Contracts and repository surface

登记 P1 governance operations contract；新增 repository helper 保存 approval operation event、policy set version record、grant lifecycle audit record。

### Phase 2：Approval operations

扩展 approval 状态机，支持 supplemental materials、needs_input、withdraw、expire、escalate、SLA state 和 break_glass audit。

### Phase 3：Policy operations

新增 policy set version projection，支持 active/canary/rolled_back、risk templates、fallback_action、deny priority 和 rollback explanation。

### Phase 4：Grant lifecycle

新增 Grant lifecycle query、expire/revoke metadata、consumption summary 和 impact analysis，继续复用 P0 binding / scope 防线。

### Phase 5：Verification and close-out

运行 AO36 contract tests、AO2/AO13/AO33/AO35 回归、ruff、AI-SDLC constraints、program truth sync，并按固定 PR 收口规则处理。

## 关键路径验证策略

| 关键路径 | 主验证方式 | 次验证方式 |
|----------|------------|------------|
| Approval 状态机 | AO36 approval operation contract tests | AO2 approval lifecycle 回归 |
| Policy version projection | AO36 policy operations contract tests | AO33 policy decision 回归 |
| Grant lifecycle | AO36 grant lifecycle contract tests | AO2/AO13 grant 回归 |
| P0 不回退 | AO35 acceptance gate 回归 | AI-SDLC constraints |

## 开放问题

| 问题 | 状态 | 阻塞阶段 |
|------|------|----------|
| 是否要 HTTP route 暴露 P1 operations | P1 先冻结 API/helper 和 contract tests，HTTP route 可在后续 Console 工作台批次接入 | 不阻塞 |
| 是否接真实通知系统 | 本工作项只输出 notification intent，不发送真实通知 | 不阻塞 |
| 是否持久化到外部 DB | P1 contract 先沿用 InMemoryRepository，外部 DB 属部署层 | 不阻塞 |
