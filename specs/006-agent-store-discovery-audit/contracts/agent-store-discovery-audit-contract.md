# Contract：Agent Store Discovery Audit

## AO6-CT-001 Agent Store Metadata Consume

给定 Agent Store 元数据快照，AgentOps 必须缓存用于关联，并返回：

- `metadata_state=consumed`
- `fact_owner=Agent Store`

AgentOps 不得声明自己是 Agent/Skill 注册事实源。

## AO6-CT-002 Unregistered Agent Discovery

给定运行事件包含 Agent/Version，但 repository 无对应 Store metadata：

- 输出 `gap_type=agent_unregistered`
- `state=suspected`
- 含 affected_runs 和 audit_id
- 不含 `raw_payload`

## AO6-CT-003 Unregistered Skill Discovery

给定 Agent 已注册但事件中的 Skill/Stage 未注册：

- 输出 `gap_type=skill_unregistered`
- 影响运行可追踪

## AO6-CT-004 Run Audit

Run Audit 必须包含：

- event_ids
- registration_state
- agent_id、version、session_id、run_id、installation_id、trace_id、audit_id、return_url
- raw_access_state

不得包含 raw payload。

## AO6-CT-005 Store Echo Summary

Store echo summary 必须包含：

- evidence_level、confidence、missing_evidence
- risk_state、approval_state
- policy_requirement.required_by/source/issuer/policy_owner/policy_version/can_ignore/affected_actions
- run_audit 摘要
- deep_links

## AO6-CT-006 Schema Compatibility

不支持的 consumer schema version 必须返回 `SUMMARY_SCHEMA_UNSUPPORTED`。

## AO6-CT-007 Console Snapshot

Console snapshot 必须能展示 Agent Store connector 状态和发现风险。

## AO6-CT-008 App Assembly Truth

应用装配必须声明 Agent Store metadata、discovery 和 run audit 路由。
