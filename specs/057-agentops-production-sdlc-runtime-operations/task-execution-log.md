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

## 待执行

- PostgreSQL runtime repository live DB smoke（需要真实 PostgreSQL 服务）。
- Deployable AgentOps service config。
- Console persisted SDLC readback tests。
- Ai_AutoSDLC -> Gateway -> AgentOps cross-project smoke。

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
