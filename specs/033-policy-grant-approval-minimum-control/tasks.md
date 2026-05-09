---
related_doc:
  - "specs/031-agentops-runtime-governance-foundation/agentops-p0-p2-backlog.md"
  - "specs/002-agentops-policy-approval-vault/spec.md"
  - "specs/031-agentops-runtime-governance-foundation/spec.md"
---
# 任务分解：Policy Grant Approval Minimum Control

**编号**：`033-policy-grant-approval-minimum-control` | **日期**：2026-05-09
**来源**：plan.md + spec.md

---

## 分批策略

```text
Batch 1: AO33 formal baseline + PolicyDecision v1
Batch 2: CapabilityGrant binding and consumption audit
Batch 3: Guardrail result ingestion and runtime projections
Batch 4: verification, archive, PR close-out
```

---

## Batch 1：AO33 formal baseline + PolicyDecision v1

### Task 1.1 冻结 AO33 formal docs

- **任务编号**：T11
- **优先级**：P0
- **依赖**：031 backlog、002 policy/grant spec、031 runtime contract spec
- **文件**：spec.md, plan.md, tasks.md, task-execution-log.md
- **可并行**：否
- **验收标准**：
  1. spec/plan/tasks 明确承接 AO-P0-07/08/09
  2. 明确 AgentOps 不执行 Runtime、不暴露 raw payload、不做 P1 管理台
- **验证**：`uv run ai-sdlc verify constraints`

### Task 1.2 实现 PolicyDecision v1 最小裁决

- **任务编号**：T12
- **优先级**：P0
- **依赖**：T11
- **文件**：src/agentops/api/policy.py, src/agentops/core/policy_engine.py, tests/contract/test_ao33_ct_policy_grant_guardrail_control.py
- **可并行**：否
- **验收标准**：
  1. 返回 `policy_decision.v1` required fields
  2. 支持 allow/warn/approval_required/block/policy_unavailable
  3. 高风险缺 scope 返回 `POLICY_SCOPE_REQUIRED`
- **验证**：`uv run pytest tests/contract/test_ao33_ct_policy_grant_guardrail_control.py -q`

## Batch 2：CapabilityGrant binding and consumption audit

### Task 2.1 补齐 Grant 最小 P0 字段和绑定

- **任务编号**：T21
- **优先级**：P0
- **依赖**：T12
- **文件**：src/agentops/core/grants.py, src/agentops/models/grants.py, src/agentops/storage/repository.py
- **可并行**：否
- **验收标准**：
  1. Grant 绑定 agent/version/artifact/installation/device/user/session/run/skill/resource_scope
  2. 签发不得扩大 approval 原始 scope 或替换主体
  3. Grant 包含 TTL、remaining_uses、signature/key_id 占位
- **验证**：AO33 Grant tests + AO2 Grant 回归

### Task 2.2 实现 Grant 消费审计和剩余次数

- **任务编号**：T22
- **优先级**：P0
- **依赖**：T21
- **文件**：src/agentops/core/grants.py, tests/contract/test_ao33_ct_policy_grant_guardrail_control.py
- **可并行**：否
- **验收标准**：
  1. 消费成功写入 `grant_consumptions`
  2. 每次消费扣减 `remaining_uses`
  3. revoked/expired/exhausted/scope mismatch 均拒绝
- **验证**：AO33 + AO2 Grant 回归

## Batch 3：Guardrail result ingestion and runtime projections

### Task 3.1 登记并接收 GuardrailResult

- **任务编号**：T31
- **优先级**：P0
- **依赖**：T12
- **文件**：src/agentops/core/runtime_contracts.py, src/agentops/core/runtime_ingestion.py, src/agentops/storage/repository.py
- **可并行**：否
- **验收标准**：
  1. Contract Registry 登记 `guardrail_result.v1`
  2. Runtime ingestion 接收并幂等处理 guardrail result
  3. 不合规 schema/signature 仍按既有路径拒绝
- **验证**：AO33 Guardrail tests + AO31 回归

### Task 3.2 Run Detail / Timeline 展示 Guardrail 摘要

- **任务编号**：T32
- **优先级**：P0
- **依赖**：T31
- **文件**：src/agentops/api/view_models.py, tests/contract/test_ao33_ct_policy_grant_guardrail_control.py
- **可并行**：否
- **验收标准**：
  1. Run Detail 返回 summary-only guardrail 摘要
  2. Timeline span projection 返回 guardrail result refs 和状态摘要
  3. 不返回 raw payload
- **验证**：AO33 projection tests

## Batch 4：verification, archive, PR close-out

### Task 4.1 验证、归档、提交和 PR

- **任务编号**：T41
- **优先级**：P0
- **依赖**：T11-T32
- **文件**：task-execution-log.md, program-manifest.yaml
- **可并行**：否
- **验收标准**：
  1. AO33 + AO2/AO31/AO32 定向回归通过
  2. ruff、format check、AI-SDLC constraints、workitem close-check 通过
  3. PR 创建后触发 @codex review 和 5 分钟 heartbeat
- **验证**：收口命令集合
