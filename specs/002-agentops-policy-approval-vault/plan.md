---
related_plan: "specs/001-agentops-trusted-loop/plan.md"
related_doc:
  - "/Users/sinclairpan/project/AI-Native底座开发文档/AgentOps_项目_PRD.md"
  - "/Users/sinclairpan/project/AI-Native底座开发文档/Agent_Store_AgentOps_AiSDLC_应用底座顶层规划_PRD.md"
---
# 实施计划：AgentOps 阶段 2 Policy Check、Approval Grant 与 Evidence Vault 摘要

**编号**：`002-agentops-policy-approval-vault` | **日期**：2026-05-05 | **规格**：`specs/002-agentops-policy-approval-vault/spec.md`

## 概述

本计划按 contract-first 方式建设 AgentOps 阶段 2 运行治理闭环。阶段 1 已提供可信事件、Evidence Summary、L5 Gate 和 PolicyDecision 降级口径；阶段 2 将 Policy Check 推进为强治理路径，补齐 Approval Center、Capability Grant、Evidence Vault 摘要访问控制、SLO 降级和 Store/CLI 可解释摘要。

## 技术背景

**语言/版本**：Python 3.11。  
**主要依赖**：保持当前标准库 + pytest + ruff；如后续接入 HTTP 层再引入 FastAPI/Pydantic。  
**存储**：阶段 2 继续扩展 `InMemoryRepository` 用于 contract verification；生产持久化另起后续工作项。  
**测试**：pytest contract tests + focused unit tests。  
**目标平台**：AgentOps Python 后端内核，供后续 HTTP/API adapter 和 UI 消费。  
**约束**：不泄露 raw evidence；高风险未知不得 allow；Grant 必须来自 approved Approval；docs/code/tests 必须可追踪。

## 宪章检查

| 宪章门禁 | 计划响应 |
|---|---|
| Persist decisions to the repository | 阶段 2 决策写入 `spec.md` 的 AD2 表，批次事实写入 `task-execution-log.md` |
| Prefer contract-level verification before closure | AO2-CT-001 到 AO2-CT-006 先冻结，再实现内核 |
| Keep docs and code traceable | `tasks.md` 逐项绑定源码、测试、验证命令和归档记录 |

## 项目结构

### 文档结构

```text
specs/002-agentops-policy-approval-vault/
├── spec.md
├── plan.md
├── tasks.md
├── task-execution-log.md
└── contracts/
    ├── contract-tests.md
    └── stage2-contracts.schema.yaml
```

### 源码结构

```text
src/agentops/
├── api/
│   ├── policy.py              # 扩展 Policy Check v2
│   ├── approvals.py           # Approval lifecycle API
│   ├── grants.py              # Capability Grant API
│   ├── evidence_vault.py      # Evidence Vault summary/raw access state
│   └── view_models.py         # 阶段 2 页面模型状态
├── core/
│   ├── policy_engine.py       # 裁决优先级、scope、Grant 消费
│   ├── approvals.py           # Approval 状态机
│   ├── grants.py              # Grant 状态机与 scope matching
│   └── evidence_vault.py      # 原文访问控制与脱敏失败降级
├── models/
│   ├── policy.py              # RuntimePolicy/Decision 常量扩展
│   ├── approvals.py
│   ├── grants.py
│   └── evidence_vault.py
└── storage/
    └── repository.py          # in-memory policy/approval/grant/vault facts
```

### 测试结构

```text
tests/contract/
├── test_ao2_ct_001_policy_check.py
├── test_ao2_ct_002_approval_lifecycle.py
├── test_ao2_ct_003_capability_grant.py
├── test_ao2_ct_004_evidence_vault.py
├── test_ao2_ct_005_policy_summary.py
└── test_ao2_ct_006_stage2_slo_admin.py
tests/unit/
├── test_policy_engine.py
├── test_approval_state_machine.py
├── test_grant_scope.py
└── test_evidence_vault.py
```

## 阶段计划

### Phase 0：规格与契约冻结

**目标**：冻结阶段 2 范围、非目标、实体、错误码、契约测试和验收口径。  
**产物**：`spec.md`、`plan.md`、`tasks.md`、`contracts/contract-tests.md`。  
**验证方式**：对抗评审 + `uv run ai-sdlc verify constraints` + refine/design gate。  
**回退方式**：保持 001 已关闭状态，不修改阶段 1 合同。

### Phase 1：Policy Check v2

**目标**：实现强 Policy Check、裁决优先级、resource_scope、service_unavailable 降级、active Grant 消费。  
**产物**：`core/policy_engine.py`、`api/policy.py` 扩展、AO2-CT-001。  
**验证方式**：Policy Check contract tests + unit tests。  
**回退方式**：保留阶段 1 `evaluate_policy_decision` 兼容函数。

### Phase 2：Approval 与 Capability Grant

**目标**：实现 Approval 状态机、审批 SLA、approved 后 Grant 签发、Grant 撤销/过期/scope mismatch。  
**产物**：`api/approvals.py`、`api/grants.py`、`core/approvals.py`、`core/grants.py`、AO2-CT-002/003。  
**验证方式**：审批和 Grant contract tests。  
**回退方式**：高风险动作维持 approval_required/block，不签发 Grant。

### Phase 3：Evidence Vault 摘要访问控制

**目标**：实现 EvidenceVaultSummary、RawAccessRequest/Grant、summary 不返回原文、redaction_failed 降级。  
**产物**：`api/evidence_vault.py`、`core/evidence_vault.py`、AO2-CT-004。  
**验证方式**：Evidence Vault contract tests 和 raw payload 泄露断言。  
**回退方式**：只提供 Evidence Summary，raw access 全部 denied。

### Phase 4：Store/CLI 摘要、SLO 与管理员模型

**目标**：输出 PolicyRequirement Summary、阶段 2 SLO Snapshot 和页面状态模型。  
**产物**：policy summary API、SLO builder、view model 扩展、AO2-CT-005/006。  
**验证方式**：contract tests + admin view model unit tests。  
**回退方式**：只展示阶段 1 降级摘要，不展示 allow。

### Phase 5：验证、对抗评审与 close

**目标**：完成全量测试、ruff、AI-SDLC constraints、workitem close-check 和两个常驻对抗 agent 合议。  
**产物**：`development-summary.md`、更新 `task-execution-log.md`、Git 提交。  
**验证方式**：`uv run pytest tests -q`、`uv run ruff check`、`uv run ai-sdlc verify constraints`、`ai-sdlc workitem close-check`。  
**回退方式**：修复 P0/P1 后重新进入同一门禁。

## 工作流计划

### 工作流 A：高风险动作进入 Policy Check

**范围**：SDK/Wrapper 执行前调用 Policy Check。  
**影响范围**：`PolicyDecision`、`CapabilityGrant`、Run policy_state。  
**验证方式**：AO2-CT-001。  
**回退方式**：service unavailable 时 require_online/block。

### 工作流 B：Approval 到 Grant

**范围**：approval_required 创建审批，审批通过后签发短期 Grant。  
**影响范围**：Approval Center、Policy Center、Store/CLI 摘要。  
**验证方式**：AO2-CT-002/003。  
**回退方式**：Approval 未通过时不得签发 Grant。

### 工作流 C：Evidence Vault 原文访问

**范围**：默认摘要、原文申请、限时 raw access state、redaction_failed。  
**影响范围**：Evidence Explorer、审计、权限失败页。  
**验证方式**：AO2-CT-004。  
**回退方式**：只返回脱敏摘要和 hash。

### 工作流 D：阶段 2 降级和可解释摘要

**范围**：SLO snapshot、PolicyRequirement Summary、管理员页面状态。  
**影响范围**：Risk Triage、Policy Center、Approval Center、Agent Store、CLI。  
**验证方式**：AO2-CT-005/006。  
**回退方式**：unknown/degraded 状态不得显示 healthy 或 allow。

## 关键路径验证策略

| 关键路径 | 主验证方式 | 次验证方式 |
|---|---|---|
| 高风险未知不得 allow | AO2-CT-001 | unit test policy priority |
| 高优先级 deny 覆盖 active Grant | AO2-CT-001 | schema enum + priority test |
| Approval 前不得签发 Grant | AO2-CT-002 | unit test approval state |
| Grant 不得扩大 Approval 原 scope | AO2-CT-002 | binding mismatch tests |
| Revoked/expired/scope mismatch Grant 不放行 | AO2-CT-003 | unit test grant scope |
| Evidence Vault 不泄露 raw_payload | AO2-CT-004 | grep/contract assertion |
| redaction_failed 不返回不可信摘要 | AO2-CT-004 | safe_empty assertion |
| Store/CLI 摘要字段完整 | AO2-CT-005 | schema field assertion |
| SLO 降级可解释 | AO2-CT-006 | admin view model assertion |

## 开放问题

| 问题 | 状态 | 阻塞阶段 |
|---|---|---|
| IAM 真实 API | 使用 mock input；真实联调前再适配 | 生产联调 |
| Store/CLI 摘要最终文案 | 先冻结必填字段和 deep link | Store 联调 |
| Evidence Vault 原文后端 | 本期不落真实原文 | 生产存储 |

## 实施顺序建议

1. 完成 Phase 0 文档和对抗评审。
2. 先写 AO2-CT-001/002/003，形成治理红线。
3. 实现 Policy Engine、Approval、Grant。
4. 写 AO2-CT-004 并实现 Evidence Vault。
5. 写 AO2-CT-005/006 并补 Store/CLI 摘要、SLO 和 view models。
6. 全量验证、合议评审、close-check、正式 close。
