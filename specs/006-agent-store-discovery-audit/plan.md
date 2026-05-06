# 实施计划：Agent Store 接入、未注册发现与运行审计

## 架构决策

| 决策 | 说明 |
|---|---|
| 消费快照而非写注册事实 | Agent Store 是 Agent/Skill 注册事实源，AgentOps 只缓存元数据用于关联、发现和回显 |
| 继续使用 InMemoryRepository | 本阶段验证产品语义和契约，不引入生产数据库 |
| Discovery 与 Audit 放在 core | API 只做薄边界，避免页面或 HTTP 路由承载业务判断 |
| Console 只展示风险摘要 | 未注册发现进入 Risk Triage，不自动更改 Store 注册状态 |

## 批次

### Batch 1：契约和文档

- 冻结 006 spec、plan、tasks、contract。
- 建立 AO6-CT-001 到 AO6-CT-008。

### Batch 2：Agent Store 元数据消费

- Repository 增加 Agent Store metadata snapshot。
- 实现 `consume_agent_store_metadata`。

### Batch 3：未注册发现和运行审计

- 实现 `discover_agent_store_gaps`。
- 实现 `build_run_audit`。
- Store echo summary 增加 policy_requirement、audit 和 discovery gap。

### Batch 4：Console 回显与验证

- Console snapshot 增加 Agent Store connector 和 risk。
- 全量后端、前端、跨平台约束验证。

## 风险

| 风险 | 处理 |
|---|---|
| 误把 AgentOps 当成 Store 写源 | 所有返回字段显式标记 `fact_owner=Agent Store` 或 `registry_fact_owner=Agent Store` |
| raw payload 泄露 | 契约测试对 discovery、audit、summary 做字符串级防泄露断言 |
| 未注册发现误报健康 | 缺元数据时 connector degraded，risk_state warning |
