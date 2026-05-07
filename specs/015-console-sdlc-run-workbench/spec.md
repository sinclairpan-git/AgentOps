# 015 Console Ai_AutoSDLC Run Workbench

## 背景

014 已把连接器健康、DLQ 和同步轨迹放入 Console，但 `Ai_AutoSDLC Runs` 页面仍主要是一张 adapter 证明表。AgentOps PRD 要求该页面展示 Reporter、Outbox、adapter_state、L5 Eligibility 和降级原因，因此本阶段把 Ai_AutoSDLC 运行状态升级为可解释工作台。

## 范围

- Console snapshot 新增 `sdlcRunWorkbench` 只读数据域。
- `sdlcRunWorkbench` 必须包含 `summary`、`reporter`、`outbox`、`eligibility` 和 `guardrails`。
- 每个工作台行必须绑定 `sdlcRuns[]` 的 `run_id` 或 `id`。
- 页面必须中文展示 Reporter 状态、Outbox 状态、L5 条件、adapter 证明状态、降级原因和下一步动作。
- 前端 validator 必须拒绝伪 `verified_loaded`、伪 outbox delivered、伪 reporter active、危险 URL/raw 字段和缺失绑定行。

## 非目标

- 不激活真实企业 Reporter、Credential、DeviceKey 或 AgentOps L5。
- 不执行 Outbox Replay、事件重放、凭证签发、权限变更或生产写操作。
- 不把 CLI dry-run、AGENTS.md materialized 或本地仓库事实当作 `verified_loaded` 机器证明。
- 不展示 raw payload、下载链接、外部 URL、PR 原文、diff 或代码片段。

## 契约测试

- AO15-CT-001：snapshot 必须包含 `sdlcRunWorkbench.summary/reporter/outbox/eligibility/guardrails`。
- AO15-CT-002：Reporter 行必须展示 reporter_status、integration_mode、credential_status、source_signed、identity_confidence、governance_state 和下一步动作。
- AO15-CT-003：Outbox 行必须展示 outbox_status、sequence_state、pending_events、oldest_pending_age、replay_boundary、evidence_impact 和审计编号。
- AO15-CT-004：Eligibility 行必须展示 evidence_level、l5_result、failed_conditions、policy_state_known、governance_loaded、verification_fresh、outbox_delivered 和下一步动作。
- AO15-CT-005：`verified_loaded` 只能由非待采集、非 AGENTS.md、非 CLI 预演的机器证明支撑；否则必须保持 `unverified`。
- AO15-CT-006：前端必须拒绝缺失绑定、状态篡改、伪激活和危险字段。
