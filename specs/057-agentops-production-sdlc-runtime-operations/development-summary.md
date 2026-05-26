# 开发摘要：AgentOps Production SDLC Runtime Operations

**工作项**：`057-agentops-production-sdlc-runtime-operations`  
**状态**：PostgreSQL / Gateway foundation 已开始实现  

## 本次归档内容

- 新增 AgentOps 侧生产化 SDLC runtime operations 规格。
- 明确 PostgreSQL 是 canonical facts 主库，Redis 仅作为可选实时加速层。
- 明确 API Gateway 是生产认证边界：AI-SDLC 发送 Bearer token，Gateway 注入 upstream identity headers，AgentOps 只信 `X-AgentOps-*`。
- 明确 Agent Store 不是 runtime outbox 必经中转。
- 明确下一阶段工程范围：PostgreSQL repository、Gateway auth tests、deployable service、Console persisted readback、cross-project smoke。

## 当前未完成

- 尚未执行真实 PostgreSQL 服务上的 live smoke。
- 尚未实现 DB migration / deployment compose。
- 尚未执行真实 Ai_AutoSDLC run 的跨项目 smoke。

## 已实现增量

- 新增 PostgreSQL runtime operations schema，覆盖 runtime facts、TraceSpan、GuardrailResult、DLQ、outbox receipt 和 audit records。
- 新增 `PostgresRepository` runtime adapter，保留 local in-memory fallback。
- 新增 repository factory：
  - 未配置 `AGENTOPS_DATABASE_URL` 时使用 local `InMemoryRepository`。
  - 配置 `AGENTOPS_DATABASE_URL` 时使用 `PostgresRepository`。
  - production auth mode 未显式传入 repository 且未配置 DB 时 fail closed。
- 新增 API Gateway runtime ingestion 文档。
- 新增 AO57 Gateway auth tests，固化 Bearer token 不能绕过 Gateway upstream identity headers。

## 验证

- `python -m ai_sdlc run --dry-run`：通过。
- `uv run pytest tests/contract/test_ao57_ct_postgres_runtime_repository.py tests/contract/test_ao57_ct_gateway_runtime_ingestion_auth.py -q`：通过。
- `uv run ruff check src/agentops/storage/postgres_repository.py src/agentops/storage/factory.py src/agentops/api/server.py tests/contract/test_ao57_ct_postgres_runtime_repository.py tests/contract/test_ao57_ct_gateway_runtime_ingestion_auth.py`：通过。
