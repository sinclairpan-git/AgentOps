# 执行日志：AgentOps Production SDLC Runtime Operations

**功能编号**：`057-agentops-production-sdlc-runtime-operations`  
**创建日期**：2026-05-26  

## 初始化归档

- **输入来源**：
  - 用户确认 DB 采用 PostgreSQL，认证契约采用 API Gateway。
  - SDLC 侧已根据 `docs/engineering/ai-sdlc-agentops-production-integration-coding-brief.md` 开始落地。
  - AgentOps AO56 / PR #58 已合入 main，支持 span-only SDLC trace/evidence readback。
- **目标**：将 AgentOps 侧对应工作正式归档为产研工作项，进入可开发的 spec/plan/tasks 流程。
- **执行命令**：
  - `python -m ai_sdlc run --dry-run`
- **结果**：
  - dry-run 通过。
  - 已新增 057 formal docs。
- **当前边界**：
  - 本批仅归档需求和实施计划，不实现 PostgreSQL/Gateway/部署代码。
- **branch disposition 计划**：
  - 当前分支：`feature/057-agentops-production-sdlc-runtime-operations-docs`。
  - 用途：057 formal docs / planning / cross-project handoff 归档。
  - 处置：提交后创建 PR；GitHub checks、Compatibility Gate、`@codex review` 或云端 fallback review 均通过后合入 `main`，随后删除或归档该 docs 分支。
- 当前批次 branch disposition 状态：`feature/057-agentops-production-sdlc-runtime-operations-docs` 为当前 docs/planning 交付分支，计划提交后创建 PR；GitHub checks、Compatibility Gate、`@codex review` 或云端 fallback review 均通过后合入 `main`，随后归档或删除分支。

## 剩余环境前提

- 真实 compose live DB smoke 需要 Docker daemon 运行。
- 真实 Ai_AutoSDLC run 联调需要 SDLC 项目配置 Gateway endpoint/token 后执行。

## Batch 2026-05-26-001 | PostgreSQL and Gateway foundation

- **改动范围**：
  - `src/agentops/storage/migrations/001_runtime_operations.sql`
  - `src/agentops/storage/postgres_repository.py`
  - `src/agentops/storage/factory.py`
  - `src/agentops/api/server.py`
  - `tests/contract/test_ao57_ct_postgres_runtime_repository.py`
  - `tests/contract/test_ao57_ct_gateway_runtime_ingestion_auth.py`
  - `docs/engineering/agentops-api-gateway-runtime-ingestion.md`
- **改动内容**：
  1. 新增 PostgreSQL runtime operations schema，覆盖 idempotency、runtime runs、trace spans、guardrail results、DLQ、outbox receipts 和 audit records。
  2. 新增 `PostgresRepository` runtime adapter，保留 non-runtime domains 的 in-memory fallback，Postgres driver lazy import。
  3. 新增 `repository_from_env()`，支持 `AGENTOPS_DATABASE_URL` 和 `AGENTOPS_POSTGRES_AUTO_MIGRATE`；生产 auth 模式无 DB 时 fail closed。
  4. HTTP server 在未显式传入 repository 时从环境构建 repository。
  5. 新增 Gateway runtime ingestion auth contract tests，固化 Bearer token 不能替代 Gateway upstream headers、`event.ingest` 可写、viewer 不可写。
  6. 新增 Gateway 接入文档，明确清洗客户端 `X-AgentOps-*` 头并由 Gateway 注入可信 headers。
- **验证命令**：
  - `uv run pytest tests/contract/test_ao57_ct_postgres_runtime_repository.py tests/contract/test_ao57_ct_gateway_runtime_ingestion_auth.py -q`
  - `uv run ruff check src/agentops/storage/postgres_repository.py src/agentops/storage/factory.py src/agentops/api/server.py tests/contract/test_ao57_ct_postgres_runtime_repository.py tests/contract/test_ao57_ct_gateway_runtime_ingestion_auth.py`
- **结果**：
  - AO57 新增契约测试通过。
  - ruff 通过。
- **当前批次 branch disposition 状态**：`codex/057-db-gateway-foundation` 为当前实现分支，计划提交后创建 PR；GitHub checks、Compatibility Gate、`@codex review` 或云端 fallback review 均通过后合入 `main`，随后归档或删除分支。

## Batch 2026-05-26-002 | Production runtime closeout

- **改动范围**：
  - `src/agentops/core/runtime_ingestion.py`
  - `src/agentops/storage/repository.py`
  - `src/agentops/storage/postgres_repository.py`
  - `src/agentops/api/gateway.py`
  - `src/agentops/api/server.py`
  - `tests/contract/test_ao57_ct_postgres_runtime_ingestion.py`
  - `tests/contract/test_ao57_ct_gateway_runtime_ingestion_auth.py`
  - `Dockerfile`
  - `docker-compose.yml`
  - `.dockerignore`
  - `docs/engineering/agentops-production-deployment.md`
  - `docs/engineering/ai-sdlc-agentops-e2e-smoke.md`
  - `docs/engineering/agentops-api-gateway-runtime-ingestion.md`
  - `pyproject.toml`
- **改动内容**：
  1. 为 runtime ingestion 增加 repository transaction 边界，PostgreSQL adapter 在同一连接中写入 facts、DLQ、idempotency 和 receipt；commit 失败时不返回 receipt。
  2. 为 `InMemoryRepository` 增加同名 transaction context，保持 local/tests 兼容。
  3. 增加 reference Gateway，校验 Bearer token、清洗客户端 `X-AgentOps-*` headers，并向 AgentOps 注入 trusted upstream identity。
  4. 增加 Gateway header cleansing / bad token 契约测试。
  5. 增加 restart-style persisted readback 契约测试，覆盖 replay dedup、Trace、Evidence summary 和 Console SDLC workbench。
  6. 增加 deployable Dockerfile / compose：PostgreSQL、AgentOps API、Gateway、Console。
  7. Console/API deployment path 支持 `VITE_AGENTOPS_API_BASE` 指向 Gateway，并允许 compose preview origin。
  8. 增加生产部署指南和 Ai_AutoSDLC -> AgentOps E2E smoke 指南。
  9. 声明 migration SQL 为 Python package data，避免镜像安装后 migration 文件缺失。
- **验证命令**：
  - `python -m ai_sdlc run --dry-run`
  - `uv run pytest tests/contract/test_ao57_ct_postgres_runtime_ingestion.py tests/contract/test_ao57_ct_gateway_runtime_ingestion_auth.py tests/contract/test_ao57_ct_postgres_runtime_repository.py -q`
  - `uv run ruff check src/agentops/core/runtime_ingestion.py src/agentops/storage/repository.py src/agentops/storage/postgres_repository.py src/agentops/api/gateway.py src/agentops/api/server.py tests/contract/test_ao57_ct_postgres_runtime_ingestion.py tests/contract/test_ao57_ct_gateway_runtime_ingestion_auth.py`
  - `uv run pytest tests/contract/test_ao57_ct_postgres_runtime_ingestion.py tests/contract/test_ao57_ct_gateway_runtime_ingestion_auth.py tests/contract/test_ao57_ct_postgres_runtime_repository.py tests/contract/test_ao56_ct_sdlc_executable_task_runtime_bridge.py tests/contract/test_ao23_ct_production_runtime_boundary.py tests/contract/test_ao15_ct_console_sdlc_run_workbench.py -q`
  - `npm test --prefix apps/agentops-console`
  - `npm run build --prefix apps/agentops-console`
  - `docker compose config`
- **结果**：
  - AO57 新增契约测试通过。
  - AO56 / AO23 / AO15 相关回归通过。
  - Console contract tests 和 production build 通过。
  - compose 配置解析通过。
  - `docker compose build api gateway console` 未执行成功：Docker daemon 未运行，错误为无法连接 `/Users/sinclairpan/.docker/run/docker.sock`。
- **当前批次 branch disposition 状态**：`codex/057-production-runtime-closeout` 为当前实现分支，计划提交后创建 PR；GitHub checks、Compatibility Gate、`@codex review` 或云端 fallback review 均通过后合入 `main`。

## Batch 2026-05-26-003 | Reference Gateway Console snapshot proxy

- **触发原因**：
  - 端到端验收时发现 compose Console 配置为 `VITE_AGENTOPS_API_BASE=http://127.0.0.1:8766`，但 reference Gateway 只代理 runtime ingestion，无法服务 Console snapshot。
- **改动范围**：
  - `src/agentops/api/gateway.py`
  - `tests/contract/test_ao57_ct_gateway_runtime_ingestion_auth.py`
  - `docs/engineering/agentops-api-gateway-runtime-ingestion.md`
  - `docs/engineering/agentops-production-deployment.md`
- **改动内容**：
  1. reference Gateway 增加 `GET /v1/console/snapshot` 代理，向内部 AgentOps API 注入 operator read scopes。
  2. 保留 `POST /v1/runtime/events` 的 Bearer token 校验和 producer identity 注入。
  3. 增加 compose UI contract test，验证 Gateway 代理 snapshot 后 Console workbench 可读真实 task guard、receipt 和 evidence readiness。
  4. 文档说明该 Console snapshot proxy 用于 local compose smoke；生产应放在正式用户认证层之后。
- **验证命令**：
  - `uv run pytest tests/contract/test_ao57_ct_gateway_runtime_ingestion_auth.py -q`
  - `uv run ruff check src/agentops/api/gateway.py tests/contract/test_ao57_ct_gateway_runtime_ingestion_auth.py`
  - `uv run pytest tests/contract/test_ao57_ct_gateway_runtime_ingestion_auth.py tests/contract/test_ao57_ct_postgres_runtime_ingestion.py tests/contract/test_ao57_ct_postgres_runtime_repository.py -q`
  - `docker compose config`
  - live local Gateway check: `GET http://127.0.0.1:8766/v1/console/snapshot`
- **结果**：
  - Gateway auth / snapshot proxy tests 通过。
  - AO57 相关回归通过。
  - compose config 通过。
  - 本地 reference Gateway 已可代理 Console snapshot。
