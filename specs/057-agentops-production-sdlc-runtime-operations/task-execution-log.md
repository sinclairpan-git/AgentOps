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

## Batch 2026-05-27-001 | Gateway production boundary closeout

- **触发原因**：
  - Ai_AutoSDLC PR #68 已完成 producer 侧 Gateway Bearer delivery，但端到端生产闭环仍要求 Ops/Gateway 侧证明 token revocation、route allowlist、request size、timeout、rate limit、redacted audit 和 live smoke。
- **改动范围**：
  - `src/agentops/api/gateway.py`
  - `src/agentops/api/auth.py`
  - `tests/contract/test_ao57_ct_gateway_runtime_ingestion_auth.py`
  - `docker-compose.yml`
  - `docs/engineering/agentops-api-gateway-runtime-ingestion.md`
  - `docs/engineering/agentops-production-deployment.md`
- **改动内容**：
  1. Reference Gateway 增加 revoked token blocklist、request body size limit、upstream timeout、producer rate limit 和 redacted JSONL audit。
  2. Gateway audit 记录 route、principal、request/audit id、outcome、status、content length 和 inbound identity stripping，不记录 Bearer token 或 runtime payload body。
  3. 新增 Gateway contract tests：revoked token、oversized batch、rate limit、redacted audit、closed route allowlist。
  4. 修正生产读权限口径：`agentops-admin`、`agentops-operator`、`agentops-viewer` 具备 summary-only `runtime.evidence.read`，与 trace/evidence readback 文档和 Console 验收一致。
  5. Compose 增加 Gateway 生产边界 env：max body、upstream timeout、rate limit、audit log path。
  6. 更新 Gateway / deployment 文档，明确 revoked token、size/timeout/rate limit 和 redacted audit 要求。
- **验证命令**：
  - `python -m ai_sdlc run --dry-run`
  - `uv run pytest tests/contract/test_ao57_ct_gateway_runtime_ingestion_auth.py tests/contract/test_ao23_ct_production_runtime_boundary.py -q`
  - `uv run ruff check src/agentops/api/auth.py src/agentops/api/gateway.py tests/contract/test_ao57_ct_gateway_runtime_ingestion_auth.py`
  - `uv run pytest tests/contract/test_ao57_ct_gateway_runtime_ingestion_auth.py tests/contract/test_ao57_ct_postgres_runtime_ingestion.py tests/contract/test_ao57_ct_postgres_runtime_repository.py tests/contract/test_ao56_ct_sdlc_executable_task_runtime_bridge.py tests/contract/test_ao23_ct_production_runtime_boundary.py tests/contract/test_ao15_ct_console_sdlc_run_workbench.py -q`
  - `npm test --prefix apps/agentops-console`
  - `npm run build --prefix apps/agentops-console`
  - `uv run ai-sdlc verify constraints`
  - `docker compose config`
  - `docker compose up --build -d`
  - live Gateway checks: valid AO56 fixture, invalid token, closed route allowlist, oversized request, redacted Gateway audit.
  - live cross-project smoke: Ai_AutoSDLC producer bridge sent `run_ai_sdlc_ops_live_1779845978` to AgentOps Gateway and AgentOps read back trace/evidence/Console workbench.
- **结果**：
  - Contract tests、ruff、Console tests/build、constraints 和 compose config 均通过。
  - Compose stack healthy：PostgreSQL、AgentOps API、Gateway、Console。
  - Live Gateway smoke：canonical fixture replay/dedup readback 成功；bad token 返回 `GATEWAY_TOKEN_INVALID`；closed route 返回 `GATEWAY_ROUTE_NOT_FOUND`；oversized request 返回 `GATEWAY_REQUEST_TOO_LARGE`；Gateway audit confirmed no token/body leak。
  - Live Ai_AutoSDLC smoke：producer bridge receipt `delivered`、`accepted_count=2`、`rejected_count=0`、`dlq_count=0`；AgentOps trace readback 2 spans；evidence summary readback `evidence_level=L4`；Console snapshot 包含 live run 的 task guard、receipt 和 evidence readiness。
- **当前批次 branch disposition 状态**：`codex/063-gateway-production-boundary` 为当前实现分支，计划提交后创建 PR；GitHub checks、Compatibility Gate、`@codex review` 或云端 fallback review 均通过后合入 `main`。

## Batch 2026-05-27-002 | Access readiness gate

- **触发原因**：
  - 本地 SDLC -> Gateway -> AgentOps live smoke 已证明链路可用，但 Ops 仓库缺少可重复执行、可归档 JSON 结果的接入就绪命令。
  - SDLC 最新语义已明确 `ai-sdlc run --dry-run` 不执行外部 POST，既有 smoke 文档需改为 `ai-sdlc run` 或显式 retry outbox。
- **改动范围**：
  - `src/agentops/ops/access_readiness.py`
  - `scripts/agentops-access-readiness.py`
  - `tests/contract/test_ao64_ct_access_readiness.py`
  - `pyproject.toml`
  - `docs/engineering/agentops-access-readiness.md`
  - `docs/engineering/ai-sdlc-agentops-e2e-smoke.md`
  - `docs/engineering/agentops-production-deployment.md`
  - `docs/engineering/ai-sdlc-agentops-production-integration-coding-brief.md`
  - `specs/057-agentops-production-sdlc-runtime-operations/spec.md`
  - `specs/057-agentops-production-sdlc-runtime-operations/tasks.md`
- **改动内容**：
  1. 新增 `agentops-access-readiness` CLI，输出 `agentops_access_readiness.v1` JSON。
  2. Readiness gate 覆盖 Gateway/API health、canonical AO56 fixture ingestion、Trace/Evidence readback。
  3. Readiness gate 覆盖 bad token、raw API bypass、Gateway route allowlist closed 负例。
  4. 输出结果只包含摘要、状态码和错误码，不输出 Bearer token、raw payload 或事件 id。
  5. 更新 E2E/SDLC handoff 文档：真实上报证明使用 `ai-sdlc run` 或显式 `ai-sdlc agentops retry --json`，不再把 `run --dry-run` 写作 live delivery 证明。
- **验证命令**：
  - `uv run pytest tests/contract/test_ao64_ct_access_readiness.py -q`
  - `uv run ruff check src/agentops/ops/access_readiness.py scripts/agentops-access-readiness.py tests/contract/test_ao64_ct_access_readiness.py`
  - `python scripts/agentops-access-readiness.py --token local-agentops-gateway-token --json`
  - `uv run agentops-access-readiness --token local-agentops-gateway-token --json`
- **结果**：
  - 新增 AO64 access readiness contract tests 通过。
  - ruff 通过。
  - 当前默认 sandbox 网络无法访问 compose 端口，readiness CLI 返回 fail-closed `TRANSPORT_ERROR` JSON；提升到本机网络后确认是 sandbox 网络隔离，不是服务异常。
  - Compose stack 已在本机运行且健康：PostgreSQL、AgentOps API、Gateway、Console。
  - Live access readiness 通过：`overall=pass`；valid Gateway ingestion 返回 `runtime_outbox_receipt.v1`，`deduplicated_count=2`，`rejected_count=0`，`dlq_count=0`；Trace readback `span_count=2`；Evidence `evidence_level=L4`、`raw_access_state=summary_only`；bad token / raw API bypass / route allowlist 负例均通过。
- **当前批次 branch disposition 状态**：`codex/064-agentops-access-readiness` 为当前实现分支，计划提交后创建 PR；GitHub checks、Compatibility Gate、`@codex review` 或云端 fallback review 均通过后合入 `main`。

## Batch 2026-06-02-001 | SDLC quality analysis close validation

- **触发原因**：
  - AgentOps 已从 Ai_AutoSDLC receipts 展示升级为 SDLC 自迭代质量分析器；close 阶段 dry-run 仍因最新执行日志缺少验证画像和统一验证证据，无法把已通过的全量测试识别为 final tests passed。
- **验证画像**：code-change
- **改动范围**：`src/agentops/core/sdlc_analysis.py`, `src/agentops/api/runtime.py`, `src/agentops/api/server.py`, `src/agentops/api/console_snapshot.py`, `src/agentops/api/app.py`, `apps/agentops-console/src/data/agentOpsApiClient.js`, `apps/agentops-console/src/data/mockAgentOpsData.js`, `apps/agentops-console/src/views/SdlcRunsView.js`, `apps/agentops-console/tests/console-contract.test.mjs`, `tests/contract/test_ao65_ct_sdlc_quality_analysis.py`, `tests/contract/test_ao15_ct_console_sdlc_run_workbench.py`
- **改动内容**：
  1. 新增 AgentOps SDLC run health summary / finding / trends 分析层，基于 summary-only spans、receipt counters、DLQ/rejected 状态和 diagnostic code 输出结论。
  2. 新增只读 API：`GET /v1/runtime/sdlc/runs/{run_id}/health-summary`、`GET /v1/runtime/sdlc/findings`、`GET /v1/runtime/sdlc/trends`。
  3. Console snapshot 增加 `sdlcFindings`、`sdlcTrends`、`sdlcRecommendations`，并在 Ai_AutoSDLC 运行工作台展示最新真实上报、上报类型标签、本轮结论、历史趋势、重点发现和给 SDLC 的建议。
  4. 保持安全边界：不展示 raw payload、raw diff、patch、源码原文、PR 原文、token 或 secret；Console 不执行 outbox replay、不自动修复、不写回 SDLC。
  5. 修复 close 阶段格式化阻断：按 `ruff format --check` 点名结果格式化 9 个文件，随后复跑全量格式检查通过。
- **统一验证命令**：
  - `uv run pytest`
  - `uv run ruff check`
  - `uv run ruff format --check`
  - `npm test --prefix apps/agentops-console`
  - `uv run ai-sdlc verify constraints`
- **结果**：
  - `uv run pytest`：通过，583 passed，1 skipped。
  - `uv run ruff check`：通过。
  - `uv run ruff format --check`：通过，130 files already formatted。
  - `npm test --prefix apps/agentops-console`：通过。
  - `uv run ai-sdlc verify constraints`：通过，no BLOCKERs。
- **代码审查**：
  - 已完成本地自检：新增分析层只消费 summary/ref/hash/count/status/diagnostic code，不读取或暴露 raw payload、diff、patch、PR 原文、token 或 secret。
  - 新增契约测试覆盖最新真实 run delivered/accepted=4/failed_span_count=0、历史 close gate failure finding、Console snapshot SDLC findings/trends/recommendations 和 HTTP 只读端点。
- **任务/计划同步状态**：
  - 057 Task 5.3 收口验证进入最终收口；实现范围与 `spec.md` / `plan.md` / `tasks.md` 的 production runtime operations 和 Ai_AutoSDLC readback/Console 分析目标一致。
  - 无 related_plan 声明；close-check related_plan_drift 为 skipped/ok。
- **已完成 git 提交**：是，本批实现、测试和归档将在当前 close-out 提交中一并提交。
- **提交哈希**：见当前 Git HEAD。
