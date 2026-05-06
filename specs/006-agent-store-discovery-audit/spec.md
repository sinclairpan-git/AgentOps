# 功能规格：Agent Store 接入、未注册发现与运行审计

**功能编号**：`006-agent-store-discovery-audit`  
**分类**：`new_requirement`  
**上游依赖**：`005-agentops-live-console-source`

## 目标

本阶段承接 AgentOps PRD 阶段 3，把已能接收运行事件的 AgentOps 推进为“可消费 Agent Store 元数据、发现未注册 Agent/Skill、生成运行审计和 Store 回显摘要”的最小闭环。

完成后必须能够证明：

1. AgentOps 只消费 Agent Store 元数据快照，不写 Agent/Skill 注册事实。
2. 已接收运行事件若无法映射到 Agent Store Agent/Version/Skill，必须进入 suspected 风险发现队列。
3. 每个运行审计必须包含跨项目 deep links：agent_id、version、session_id、run_id、installation_id、trace_id、audit_id、return_url。
4. Agent Store 回显摘要必须包含 evidence、risk、approval、policy_requirement 和 run audit 摘要。
5. 任意 discovery、audit、summary 路径不得暴露 raw payload。

## 非目标

- 不实现 Agent Store 首页、详情页、上架或注册主流程。
- 不把 AgentOps 变成 Agent/Skill 注册事实源。
- 不接真实 Agent Store HTTP 服务；本期使用 repository 元数据快照模拟消费边界。
- 不做 Git/PR/CI/Test Connector、采纳分析或质量评分引擎。

## 功能需求

- **FR-001**：系统必须提供 Agent Store metadata consume API 边界，返回 fact_owner=`Agent Store`。
- **FR-002**：系统必须基于运行事件发现未注册 Agent/Version，并输出 suspected 风险。
- **FR-003**：系统必须在 Agent 已注册但 Skill 未注册时输出 skill_unregistered 风险。
- **FR-004**：系统必须提供 Run Audit view model，保留 event_ids 和 deep_links，不返回 raw_payload。
- **FR-005**：Agent Store 回显摘要必须包含 policy_requirement：required_by、source、issuer、policy_owner、policy_version、can_ignore、affected_actions。
- **FR-006**：Console snapshot 必须把 Agent Store 发现问题回显到 Risk Triage 和 Connector Status。

## 契约测试

| 测试 | 验收 |
|---|---|
| AO6-CT-001 | Agent Store metadata 被消费但 fact_owner 保持 Agent Store |
| AO6-CT-002 | 未注册 Agent 被发现为 suspected，且不含 raw_payload |
| AO6-CT-003 | 已注册 Agent 的未注册 Skill 被发现 |
| AO6-CT-004 | Run Audit 含 deep links，不含 raw_payload |
| AO6-CT-005 | Store echo summary 含 policy_requirement 和 audit |
| AO6-CT-006 | 不兼容 consumer schema 返回 SUMMARY_SCHEMA_UNSUPPORTED |
| AO6-CT-007 | Console snapshot 展示 Agent Store 风险和连接器状态 |
| AO6-CT-008 | 应用装配声明 Agent Store 和 Run Audit 路由 |

## 成功标准

- `uv run pytest tests/contract/test_ao6_ct_agent_store_discovery_audit.py -q` 通过。
- `uv run pytest tests -q` 通过。
- `uv run ruff check src tests` 通过。
- `npm test` 和 `npm run build` 继续通过。
