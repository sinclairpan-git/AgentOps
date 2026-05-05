---
related_plan: "specs/001-agentops-trusted-loop/plan.md"
related_doc:
  - "/Users/sinclairpan/project/AI-Native底座开发文档/AgentOps_项目_PRD.md"
  - "/Users/sinclairpan/project/AI-Native底座开发文档/Agent_Store_AgentOps_AiSDLC_应用底座顶层规划_PRD.md"
---
# 任务分解：AgentOps 阶段 2 Policy Check、Approval Grant 与 Evidence Vault 摘要

**编号**：`002-agentops-policy-approval-vault` | **日期**：2026-05-05  
**来源**：`spec.md` + `plan.md`

---

## 分批策略

```text
Batch 1: stage-2 formal baseline and adversarial review
Batch 2: Policy Check v2
Batch 3: Approval lifecycle and Capability Grant
Batch 4: Evidence Vault summary and raw access state
Batch 5: Store/CLI summary, SLO, admin models and close
```

## 任务状态

| 任务 | 状态 | 最新验证 |
|---|---|---|
| T11 | 已完成 | `uv run ai-sdlc verify constraints` |
| T21 | 已完成 | `uv run pytest tests/contract/test_ao2_ct_001_policy_check.py tests/unit/test_policy_engine.py -q` |
| T31 | 已完成 | `uv run pytest tests/contract/test_ao2_ct_002_approval_lifecycle.py tests/unit/test_approval_state_machine.py -q` |
| T32 | 已完成 | `uv run pytest tests/contract/test_ao2_ct_003_capability_grant.py tests/unit/test_grant_scope.py -q` |
| T41 | 已完成 | `uv run pytest tests/contract/test_ao2_ct_004_evidence_vault.py tests/unit/test_evidence_vault.py -q` |
| T51 | 已完成 | `uv run pytest tests/contract/test_ao2_ct_005_policy_summary.py -q` |
| T52 | 已完成 | `uv run pytest tests/contract/test_ao2_ct_006_stage2_slo_admin.py tests/unit/test_admin_view_models.py -q` |
| T53 | 已完成 | `ai-sdlc workitem close-check --wi specs/002-agentops-policy-approval-vault --json` |

---

## Batch 1：stage-2 formal baseline and adversarial review

### Task 1.1 冻结阶段 2 业务规格

- **任务编号**：T11
- **优先级**：P0
- **依赖**：001 已 close
- **文件**：
  - `specs/002-agentops-policy-approval-vault/spec.md`
  - `specs/002-agentops-policy-approval-vault/plan.md`
  - `specs/002-agentops-policy-approval-vault/tasks.md`
  - `specs/002-agentops-policy-approval-vault/contracts/contract-tests.md`
  - `specs/002-agentops-policy-approval-vault/contracts/stage2-contracts.schema.yaml`
- **可并行**：否
- **验收标准**：
  1. 明确阶段 2 范围、非目标、用户故事、FR、实体、契约测试和成功标准。
  2. 明确高风险未知不得 allow、Grant 必须来自 approved Approval、Evidence Vault 摘要不返回原文。
  3. 机器可读 schema 冻结 required fields、枚举和错误响应。
  4. 两个常驻对抗 agent 无 P0/P1 阻断。
- **验证**：`uv run ai-sdlc verify constraints`

---

## Batch 2：Policy Check v2

### Task 2.1 实现强 Policy Check 与裁决优先级

- **任务编号**：T21
- **优先级**：P0
- **依赖**：T11
- **文件**：
  - `src/agentops/core/policy_engine.py`
  - `src/agentops/api/policy.py`
  - `src/agentops/models/policy.py`
  - `tests/contract/test_ao2_ct_001_policy_check.py`
  - `tests/unit/test_policy_engine.py`
- **可并行**：否
- **验收标准**：
  1. 缺 resource_scope 的高风险动作返回 `POLICY_SCOPE_REQUIRED`。
  2. Policy Service 不可用时，高风险动作返回 `block` + `require_online`。
  3. active Grant 且 scope 匹配时返回 `conditional_allow`。
  4. global_deny/IAM deny/project deny/agent disabled/policy_block 覆盖 active Grant。
  5. 阶段 1 `evaluate_policy_decision` 兼容行为保留。
- **验证**：`uv run pytest tests/contract/test_ao2_ct_001_policy_check.py tests/unit/test_policy_engine.py -q`

---

## Batch 3：Approval lifecycle and Capability Grant

### Task 3.1 实现 Approval 状态机

- **任务编号**：T31
- **优先级**：P0
- **依赖**：T21
- **文件**：
  - `src/agentops/core/approvals.py`
  - `src/agentops/api/approvals.py`
  - `src/agentops/models/approvals.py`
  - `src/agentops/storage/repository.py`
  - `tests/contract/test_ao2_ct_002_approval_lifecycle.py`
  - `tests/unit/test_approval_state_machine.py`
- **可并行**：可与 T32 拆分但需协调 repository 字段
- **验收标准**：
  1. approval_required 可创建 ApprovalRequest。
  2. approve/reject/request_more_info/expire/escalate 状态流转可审计。
  3. requester 自批返回 `APPROVAL_SELF_APPROVAL_DENIED`。
- **验证**：`uv run pytest tests/contract/test_ao2_ct_002_approval_lifecycle.py tests/unit/test_approval_state_machine.py -q`

### Task 3.2 实现 Capability Grant 生命周期

- **任务编号**：T32
- **优先级**：P0
- **依赖**：T31
- **文件**：
  - `src/agentops/core/grants.py`
  - `src/agentops/api/grants.py`
  - `src/agentops/models/grants.py`
  - `src/agentops/storage/repository.py`
  - `tests/contract/test_ao2_ct_003_capability_grant.py`
  - `tests/unit/test_grant_scope.py`
- **可并行**：可与 T31 后半并行
- **验收标准**：
  1. 只有 approved Approval 可签发 Grant。
  2. Grant 必须绑定原 Approval 的 policy_check_id、action、agent、skill、scope、policy_version、requester，不得扩大授权范围。
  3. active Grant 可消费并写审计字段。
  4. revoked/expired/scope mismatch 不得放行。
- **验证**：`uv run pytest tests/contract/test_ao2_ct_003_capability_grant.py tests/unit/test_grant_scope.py -q`

---

## Batch 4：Evidence Vault summary and raw access state

### Task 4.1 实现 Evidence Vault 摘要访问控制

- **任务编号**：T41
- **优先级**：P0
- **依赖**：T31
- **文件**：
  - `src/agentops/core/evidence_vault.py`
  - `src/agentops/api/evidence_vault.py`
  - `src/agentops/models/evidence_vault.py`
  - `tests/contract/test_ao2_ct_004_evidence_vault.py`
  - `tests/unit/test_evidence_vault.py`
- **可并行**：否
- **验收标准**：
  1. summary 默认只返回 redacted_summary、payload_hash、raw_access_state。
  2. raw access 未授权返回 `RAW_ACCESS_DENIED`。
  3. approved raw grant 限时有效。
  4. redaction_failed 不返回 raw_payload，也不得返回不可信 redacted_summary 内容，只能返回 safe_empty/hash/告警动作。
- **验证**：`uv run pytest tests/contract/test_ao2_ct_004_evidence_vault.py tests/unit/test_evidence_vault.py -q`

---

## Batch 5：Store/CLI summary, SLO, admin models and close

### Task 5.1 实现 Policy Requirement Summary

- **任务编号**：T51
- **优先级**：P1
- **依赖**：T21
- **文件**：
  - `src/agentops/api/policy.py`
  - `tests/contract/test_ao2_ct_005_policy_summary.py`
- **可并行**：可与 T52 并行
- **验收标准**：
  1. Summary 包含 required_by、source、issuer、policy_owner、policy_version、can_ignore、affected_actions、deep_links。
  2. deep_links 包含 approval_url、policy_url、evidence_url、return_url，并返回 plain_language、primary_action、secondary_action。
  3. schema 不兼容返回 `POLICY_SUMMARY_SCHEMA_UNSUPPORTED`。
- **验证**：`uv run pytest tests/contract/test_ao2_ct_005_policy_summary.py -q`

### Task 5.2 实现阶段 2 SLO 和管理员模型

- **任务编号**：T52
- **优先级**：P1
- **依赖**：T21、T31、T41
- **文件**：
  - `src/agentops/api/view_models.py`
  - `tests/contract/test_ao2_ct_006_stage2_slo_admin.py`
  - `tests/unit/test_admin_view_models.py`
- **可并行**：可与 T51 并行
- **验收标准**：
  1. Policy Check、Approval Service、Evidence Query 的 healthy/degraded/unknown 可解释。
  2. Approval Center、Policy Center、Evidence Explorer、Risk Triage 覆盖阶段 2 状态、主动作、辅助动作、owner_hint、audit_id/request_id。
  3. permission_denied 必须有 denied_scope 且不泄露敏感事实。
  4. 缺 SLO 不得显示 healthy。
- **验证**：`uv run pytest tests/contract/test_ao2_ct_006_stage2_slo_admin.py tests/unit/test_admin_view_models.py -q`

### Task 5.3 全量验证、归档和 close

- **任务编号**：T53
- **优先级**：P0
- **依赖**：T11-T52
- **文件**：
  - `specs/002-agentops-policy-approval-vault/task-execution-log.md`
  - `specs/002-agentops-policy-approval-vault/development-summary.md`
- **可并行**：否
- **验收标准**：
  1. `uv run pytest tests -q` 通过。
  2. `uv run ruff check` 通过。
  3. `uv run ai-sdlc verify constraints` 无 BLOCKER。
  4. `ai-sdlc workitem close-check --wi specs/002-agentops-policy-approval-vault --json` 返回 ok true。
  5. 两个常驻对抗 agent 最终通过。
- **验证**：全量验证命令 + AI-SDLC close-check。
