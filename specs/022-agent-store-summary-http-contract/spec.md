# 规格：Agent Store Summary HTTP Contract

**功能编号**：`022-agent-store-summary-http-contract`

## 背景

001 已要求 Agent Store 只能消费 AgentOps 输出的证据、风险、审批和质量摘要，不能读取 raw evidence，也不能把展示态推导为治理态。006/007 已经让 Console 能复用 AgentOps 的 Agent Store echo summary；018-021 完成了 credential 查询、撤销和重新签发闭环。当前缺口是 `/v1/store-summary/{agent_id}` 已在 API route manifest 和 OpenAPI 中声明，但标准库 HTTP server 尚未实现真实路由，Agent Store 仍无法通过 HTTP 消费这个 summary contract。

## 目标

- 新增 `GET /v1/store-summary/{agent_id}` 的 HTTP 实现，基于 AgentOps repository 中的运行事件和 Agent Store metadata 构建 summary。
- 请求必须指定 `version` 和 `run_id`；可选 `schema_version` 默认为 `1.0`，不支持的 schema 必须返回明确 contract error。
- HTTP 响应必须使用 `agentops.agent_store.echo.v1`，包含 score template、evidence、risk、approval、validity、deep links、run audit 和 policy requirement。
- summary 必须声明 `agentops_fact_owner=AgentOps`，并显式给出 Agent Store display-only 消费边界。
- summary 只能暴露 redacted/summary 字段，不返回 raw payload、raw evidence、ingestion token、credential token 或 device key。
- Console 已有 summary workbench 继续复用同一核心构建器，避免 Console 自己推导风险或治理态。

## 非目标

- 不修改 Agent Store 仓库或注册事实源。
- 不允许 Agent Store 发布/下架 Agent、签发 credential、推导 active、推导 `verified_loaded` 或提升 L5。
- 不新增 raw evidence 授权流程；raw 访问仍归 Evidence Vault。
- 不实现跨项目持久化查询、分页、鉴权或外部网络暴露。

## 验收契约

- AO22-CT-001：`GET /v1/store-summary/{agent_id}?version=...&run_id=...` 返回真实 AgentOps summary、CORS header 和 `agentops.agent_store.echo.v1`。
- AO22-CT-002：HTTP summary 基于同一 run 的 L5 gate event chain 计算 evidence level，缺失事件时不得声称 L5。
- AO22-CT-003：缺少 `version` 或 `run_id` 返回 `STORE_SUMMARY_QUERY_REQUIRED`。
- AO22-CT-004：不支持的 `schema_version` 返回 `SUMMARY_SCHEMA_UNSUPPORTED`。
- AO22-CT-005：run 与请求的 `agent_id/version` 不匹配时返回 `STORE_SUMMARY_RUN_MISMATCH`。
- AO22-CT-006：summary 明示 AgentOps fact owner、Agent Store display-only boundary、允许动作和禁止动作。
- AO22-CT-007：summary 序列化结果不得包含 raw payload、raw evidence、token、device key 或 credential secret。
- AO22-CT-008：OpenAPI 与 route manifest 均声明 HTTP store summary contract。

## 落地结果

本阶段完成后，Agent Store 可以通过本地 AgentOps HTTP API 消费一个稳定、可回显、不可越权的 summary contract；AgentOps 仍是证据、风险、审批和质量摘要事实源，Agent Store 只负责展示和跳转。
