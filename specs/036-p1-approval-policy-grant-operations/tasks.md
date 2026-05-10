---
related_doc:
  - "specs/031-agentops-runtime-governance-foundation/agentops-p0-p2-backlog.md"
  - "specs/002-agentops-policy-approval-vault/spec.md"
  - "specs/013-approval-grant-workbench/spec.md"
  - "specs/033-policy-grant-approval-minimum-control/spec.md"
---
# 任务分解：P1 Approval Policy Grant Operations

**编号**：`036-p1-approval-policy-grant-operations` | **日期**：2026-05-10

## 分批策略

```text
Batch 1: formal baseline + contract registry
Batch 2: approval operations state machine
Batch 3: policy operations projection
Batch 4: grant lifecycle operations
Batch 5: verification, archive, PR close-out
```

## Batch 1：formal baseline + contract registry

### Task 1.1 冻结 AO36 formal docs

- **任务编号**：T11
- **优先级**：P0
- **文件**：spec.md, plan.md, tasks.md, task-execution-log.md, program-manifest.yaml
- **验收标准**：
  1. 明确承接 AO-P1-01、AO-P1-02、AO-P1-03
  2. 明确 AgentOps 不执行 Runtime、不发送真实通知、不暴露 raw payload
  3. manifest 映射新工作项
- **验证**：`uv run ai-sdlc verify constraints`

### Task 1.2 登记 P1 governance operations contracts

- **任务编号**：T12
- **优先级**：P0
- **文件**：src/agentops/core/runtime_contracts.py, tests/contract/test_ao36_ct_p1_governance_operations.py
- **验收标准**：
  1. 登记 approval operation / policy set version / grant lifecycle projection contract
  2. contract required fields 包含 operation id、subject、state、summary 和 audit_id
  3. 敏感字段不进入 contract payload
- **验证**：AO36 contract registry tests

## Batch 2：approval operations state machine

### Task 2.1 扩展 Approval Center 状态转换

- **任务编号**：T21
- **优先级**：P1
- **文件**：src/agentops/core/approvals.py, src/agentops/api/approvals.py, src/agentops/storage/repository.py
- **验收标准**：
  1. 支持 needs_input、withdraw、expire、escalate 和 SLA state
  2. supplemental_materials / required_materials / notification intent 可查询
  3. requester self-approval 防线保留，break_glass 必须带 reason 和 audit
- **验证**：AO36 approval operation tests + AO2 approval lifecycle regression

## Batch 3：policy operations projection

### Task 3.1 实现 Policy set version operations projection

- **任务编号**：T31
- **优先级**：P1
- **文件**：src/agentops/api/policy.py, src/agentops/storage/repository.py
- **验收标准**：
  1. 返回 active/canary/rolled_back 版本状态
  2. 返回 risk_templates、fallback_action、deny priority、rollback metadata
  3. 明确 deny_overrides_grant
- **验证**：AO36 policy operations tests + AO33 policy regression

## Batch 4：grant lifecycle operations

### Task 4.1 实现 Grant lifecycle query/revoke/impact

- **任务编号**：T41
- **优先级**：P1
- **文件**：src/agentops/core/grants.py, src/agentops/api/grants.py, src/agentops/storage/repository.py
- **验收标准**：
  1. 可查询 Grant status、binding、TTL、remaining_uses、consumption_count
  2. revoke/expire 写入 actor、reason、time、audit_id
  3. impact summary 包含 affected_runs、affected_sessions、offline_allowed、owner_notification_state
- **验证**：AO36 grant lifecycle tests + AO2/AO13 grant regression

## Batch 5：verification, archive, PR close-out

### Task 5.1 验证、归档、提交和 PR

- **任务编号**：T51
- **优先级**：P0
- **文件**：task-execution-log.md, development-summary.md
- **验收标准**：
  1. AO36 + AO2/AO13/AO33/AO35 定向回归通过
  2. ruff 和 AI-SDLC constraints 通过
  3. PR 创建后按项目固定规则触发 review/checks/heartbeat 收口
- **验证**：收口命令集合
