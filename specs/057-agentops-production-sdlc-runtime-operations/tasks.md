# 任务清单：AgentOps Production SDLC Runtime Operations

## 当前落地状态

| Task | 状态 | 说明 |
|---|---|---|
| 1.1 | Done | 057 formal docs / SDLC handoff 已归档 |
| 1.2 | Done | PostgreSQL runtime schema、repository contract、package data 已落地 |
| 2.1 | Done | `AGENTOPS_DATABASE_URL` factory、local fallback、production fail-closed 已落地 |
| 2.2 | Done | runtime ingestion 已包裹 repository transaction，新增 restart readback / replay regression |
| 3.1 | Done | Gateway upstream auth、scope denied、reference Gateway header cleansing 已测试 |
| 3.2 | Done | Gateway 接入说明已补充 reference Gateway 启动方式 |
| 4.1 | Done | `Dockerfile` / `docker-compose.yml` / production deployment doc 已补齐；compose config 已验证 |
| 4.2 | Done | Console persisted readback contract 覆盖重启后 task guard、receipt、evidence readiness |
| 5.1 | Done | E2E smoke 指南已归档；本地 reference Gateway/API fixture smoke 由 AO57 contract tests 覆盖 |
| 5.2 | In progress | 本批 PR 创建、checks、Compatibility Gate、review、合入按 AGENTS.md 收口 |

## Batch 1：Formal baseline and DB design

### Task 1.1 归档 Ops 侧生产接入需求

- **文件**：
  - `specs/057-agentops-production-sdlc-runtime-operations/spec.md`
  - `specs/057-agentops-production-sdlc-runtime-operations/plan.md`
  - `specs/057-agentops-production-sdlc-runtime-operations/tasks.md`
  - `docs/engineering/ai-sdlc-agentops-production-integration-coding-brief.md`
- **目标**：
  1. 明确 AgentOps 侧从 contract-complete 到 production-usable 的差距。
  2. 固化 PostgreSQL 主库、Redis 可选实时层、API Gateway 认证边界。
  3. 与 SDLC 侧 coding brief 对齐。
- **验证**：文档审查、`python -m ai_sdlc run --dry-run`。

### Task 1.2 设计 PostgreSQL schema 和 repository contract

- **文件**：
  - `src/agentops/storage/postgres_repository.py`
  - `src/agentops/storage/migrations/*`
  - `tests/contract/test_ao57_ct_postgres_runtime_repository.py`
- **目标**：
  1. 定义 runtime events、trace spans、guardrail results、receipts、DLQ、audit 表。
  2. 增加 idempotency、run/trace 查询、outbox replay 所需索引。
  3. 保持 `InMemoryRepository` 测试兼容。
- **验证**：PostgreSQL repository contract tests。

## Batch 2：Persistent ingestion path

### Task 2.1 接入 repository factory 和环境变量

- **文件**：
  - `src/agentops/api/server.py`
  - `src/agentops/storage/repository.py`
  - `src/agentops/storage/postgres_repository.py`
- **目标**：
  1. 支持 `AGENTOPS_DATABASE_URL`。
  2. 未配置 DB 时保持 local in-memory。
  3. production mode 配置 DB 失败时 fail closed。
- **验证**：local mode / production mode contract tests。

### Task 2.2 事务化 runtime ingestion receipt

- **文件**：
  - `src/agentops/core/runtime_ingestion.py`
  - `src/agentops/storage/postgres_repository.py`
  - `tests/contract/test_ao57_ct_postgres_runtime_ingestion.py`
- **目标**：
  1. DB commit 成功后才返回 accepted/delivered receipt。
  2. 支持 replay dedup、stale ignored、DLQ diagnostics。
  3. 服务重启后 trace/evidence/receipt 可读。
- **验证**：AO56 fixture DB path + restart readback。

## Batch 3：Gateway production auth path

### Task 3.1 增加 Gateway upstream auth 契约测试

- **文件**：
  - `tests/contract/test_ao57_ct_gateway_runtime_ingestion_auth.py`
  - `specs/057-agentops-production-sdlc-runtime-operations/task-execution-log.md`
- **目标**：
  1. 缺 identity 返回 `UPSTREAM_IDENTITY_REQUIRED`。
  2. viewer role/scope 返回 `AGENTOPS_SCOPE_DENIED`。
  3. `agentops-ingestor` 或 `event.ingest` 可以写入 runtime events。
  4. 拒绝响应不泄露 token/raw payload。
- **验证**：AO23 + AO57 auth tests。

### Task 3.2 编写 Gateway 接入说明

- **文件**：
  - `docs/engineering/agentops-api-gateway-runtime-ingestion.md`
- **目标**：
  1. 说明 Bearer token -> upstream headers 的职责。
  2. 要求 Gateway 清洗外部 `X-AgentOps-*` headers。
  3. 给出 Nginx/Envoy/Cloudflare Worker 或等价伪配置。
- **验证**：文档审查。

## Batch 4：Deployable service and Console readback

### Task 4.1 增加本地/服务器部署配置

- **文件**：
  - `Dockerfile`
  - `docker-compose.yml`
  - `docs/engineering/agentops-production-deployment.md`
- **目标**：
  1. 启动 AgentOps API + PostgreSQL。
  2. 配置 production auth 和 DB env。
  3. Console 支持 `VITE_AGENTOPS_API_BASE` 指向 Gateway/API。
- **验证**：local compose smoke。

### Task 4.2 Console persisted SDLC readback

- **文件**：
  - `src/agentops/api/console_snapshot.py`
  - `apps/agentops-console/tests/console-contract.test.mjs`
  - `tests/contract/test_ao57_ct_console_persisted_sdlc_readback.py`
- **目标**：
  1. Console 从 persisted facts 构建 SDLC workbench。
  2. 重启 API 后仍可展示 task guard、receipt、evidence readiness。
  3. 不回退到 mock 或 raw payload。
- **验证**：AO4/AO15/AO56/AO57 tests。

## Batch 5：Cross-project closeout

### Task 5.1 端到端 smoke

- **文件**：
  - `docs/engineering/ai-sdlc-agentops-e2e-smoke.md`
  - `specs/057-agentops-production-sdlc-runtime-operations/task-execution-log.md`
- **目标**：
  1. 启动 AgentOps + DB + Gateway。
  2. 配置 Ai_AutoSDLC Gateway endpoint/token。
  3. 执行真实或受控 `ai-sdlc run`。
  4. 验证 receipt、trace、evidence、Console snapshot。
  5. 覆盖 bad token、missing scope、network replay、schema invalid。
- **验证**：smoke 结果归档。

### Task 5.2 收口验证

- **文件**：
  - `specs/057-agentops-production-sdlc-runtime-operations/development-summary.md`
  - `specs/057-agentops-production-sdlc-runtime-operations/task-execution-log.md`
  - `program-manifest.yaml`
- **目标**：
  1. 记录实现范围、验证命令和跨项目联调状态。
  2. 刷新 program truth sync。
  3. 创建 PR 并按 AGENTS.md PR 收口规则处理。
- **验证**：
  - `python -m ai_sdlc run --dry-run`
  - `uv run pytest ...`
  - `npm test --prefix apps/agentops-console`
  - `npm run build --prefix apps/agentops-console`
