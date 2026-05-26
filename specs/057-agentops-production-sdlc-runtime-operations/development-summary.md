# 开发摘要：AgentOps Production SDLC Runtime Operations

**工作项**：`057-agentops-production-sdlc-runtime-operations`  
**状态**：production runtime closeout 已完成实现，等待 PR checks / review 收口

## 已落地能力

- PostgreSQL 是 AgentOps runtime facts、TraceSpan、GuardrailResult、outbox receipt、DLQ、audit schema 的生产 canonical store。
- `AGENTOPS_DATABASE_URL` 驱动 repository factory；未配置 DB 时 local 使用 `InMemoryRepository`；production auth mode 未配置 DB 时 fail closed。
- Runtime ingestion 已进入 repository transaction：facts / DLQ / idempotency / receipt 在同一事务边界内完成，commit 失败时不返回 delivered/accepted receipt。
- API Gateway 生产认证路径已固化：
  - Producer 只向 Gateway 发送 Bearer token。
  - Gateway 清洗客户端 `X-AgentOps-*` headers。
  - Gateway 注入 `X-AgentOps-Principal`、roles、scopes、request id、audit id。
  - AgentOps API 只信 upstream identity headers。
- 新增 reference Gateway：`python -m agentops.api.gateway`，用于本地和小型服务器 smoke；生产可替换为正式 API Gateway。
- 新增 deployable stack：
  - `Dockerfile`
  - `docker-compose.yml`
  - `docs/engineering/agentops-production-deployment.md`
- Console persisted SDLC readback 已用 restart-style contract 覆盖：重启后仍可读取 task guard、outbox receipt、Trace、Evidence readiness。
- Cross-project E2E smoke 指南已归档：`docs/engineering/ai-sdlc-agentops-e2e-smoke.md`。

## 验证状态

- `python -m ai_sdlc run --dry-run`：当前仍会在 close 阶段提示 Final tests open，原因是本批 PR 尚未完成远端 checks / review / 合入收口。
- `uv run pytest tests/contract/test_ao57_ct_postgres_runtime_ingestion.py tests/contract/test_ao57_ct_gateway_runtime_ingestion_auth.py tests/contract/test_ao57_ct_postgres_runtime_repository.py -q`：通过。
- `uv run pytest tests/contract/test_ao57_ct_postgres_runtime_ingestion.py tests/contract/test_ao57_ct_gateway_runtime_ingestion_auth.py tests/contract/test_ao57_ct_postgres_runtime_repository.py tests/contract/test_ao56_ct_sdlc_executable_task_runtime_bridge.py tests/contract/test_ao23_ct_production_runtime_boundary.py tests/contract/test_ao15_ct_console_sdlc_run_workbench.py -q`：通过。
- `uv run ruff check ...`：通过。
- `npm test --prefix apps/agentops-console`：通过。
- `npm run build --prefix apps/agentops-console`：通过。
- `docker compose config`：通过。

## 环境限制

- 本机 Docker daemon 未运行，`docker compose build api gateway console` 无法连接 `/Users/sinclairpan/.docker/run/docker.sock`，因此本轮未执行真实 compose live DB smoke。
- 本机未安装 `postgres` binary，未用裸本地 PostgreSQL 替代 compose。
- 可重复 live smoke 已通过 `docker-compose.yml` 和 `docs/engineering/ai-sdlc-agentops-e2e-smoke.md` 固化；有 Docker daemon 的环境可直接执行。
