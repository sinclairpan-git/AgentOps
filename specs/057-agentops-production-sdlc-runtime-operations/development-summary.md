# 开发摘要：AgentOps Production SDLC Runtime Operations

**工作项**：`057-agentops-production-sdlc-runtime-operations`  
**状态**：需求归档完成，待实现  

## 本次归档内容

- 新增 AgentOps 侧生产化 SDLC runtime operations 规格。
- 明确 PostgreSQL 是 canonical facts 主库，Redis 仅作为可选实时加速层。
- 明确 API Gateway 是生产认证边界：AI-SDLC 发送 Bearer token，Gateway 注入 upstream identity headers，AgentOps 只信 `X-AgentOps-*`。
- 明确 Agent Store 不是 runtime outbox 必经中转。
- 明确下一阶段工程范围：PostgreSQL repository、Gateway auth tests、deployable service、Console persisted readback、cross-project smoke。

## 当前未完成

- 尚未实现 PostgreSQL repository。
- 尚未实现 DB migration / deployment compose。
- 尚未实现 Gateway 示例配置。
- 尚未执行真实 Ai_AutoSDLC run 的跨项目 smoke。

## 验证

- `python -m ai_sdlc run --dry-run`：通过。

