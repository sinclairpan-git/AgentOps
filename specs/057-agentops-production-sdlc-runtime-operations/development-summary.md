# 开发摘要：AgentOps Production SDLC Runtime Operations

**工作项**：`057-agentops-production-sdlc-runtime-operations`  
**状态**：production runtime closeout、access readiness gate 和 SDLC quality analysis 已完成实现；本地 final tests / close dry-run 已通过，等待 git close-out / PR checks / review 收口

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
- Access readiness gate 已落地：
  - `uv run agentops-access-readiness --json`
  - `python scripts/agentops-access-readiness.py --token <redacted> --json`
  - 覆盖 Gateway/API health、正向 runtime ingestion、Trace/Evidence readback、bad token、raw API bypass、closed route allowlist。
- SDLC smoke 文档已升级为最新语义：`ai-sdlc run --dry-run` 不作为 live delivery 证明；真实上报使用 `ai-sdlc run` 或显式 retry 已审阅 outbox。
- SDLC run health analysis 已落地：
  - 基于 summary-only receipts、TraceSpan、Evidence readiness 和 diagnostic code 自动生成 run health summary。
  - 生成 `agentops_sdlc_finding.v1`，覆盖 close gate failure、missing failure reason、task guard blocked、missing executable task、insufficient evidence、repeated retry、reporter delivery issue、stage coverage gap。
  - 按 workitem / stage / run_type 聚合趋势，区分 `real_run`、`readiness_fixture`、`live_smoke`、`dry_run_retry`。
  - Console Ai_AutoSDLC 运行工作台展示最新真实上报、本轮结论、历史趋势、Top findings 和给 SDLC 的建议。
  - 新增只读 API：`/v1/runtime/sdlc/runs/{run_id}/health-summary`、`/v1/runtime/sdlc/findings`、`/v1/runtime/sdlc/trends`；`/v1/console/snapshot` 包含 `sdlcFindings` / `sdlcTrends` / `sdlcRecommendations`。
  - 安全边界保持 summary/ref/hash/count/status/diagnostic code，不展示 raw payload、raw diff、patch、源码原文、PR 原文、token 或 secret；Console 不执行 outbox replay、不自动修复、不写回 SDLC。

## 验证状态

- `uv run pytest`：通过，583 passed，1 skipped。
- `uv run ruff check`：通过。
- `uv run ruff format --check`：通过，130 files already formatted。
- `npm test --prefix apps/agentops-console`：通过。
- `uv run ai-sdlc verify constraints`：通过，no BLOCKERs。
- `ai-sdlc run --dry-run`：`Stage close: PASS`。
- `uv run ai-sdlc workitem close-check --wi specs/057-agentops-production-sdlc-runtime-operations --json`：final tests、execution log、review gate、verification profile 均通过；当前唯一剩余 blocker 是 git close-out 尚未提交。
- `uv run pytest tests/contract/test_ao57_ct_postgres_runtime_ingestion.py tests/contract/test_ao57_ct_gateway_runtime_ingestion_auth.py tests/contract/test_ao57_ct_postgres_runtime_repository.py -q`：通过。
- `uv run pytest tests/contract/test_ao57_ct_postgres_runtime_ingestion.py tests/contract/test_ao57_ct_gateway_runtime_ingestion_auth.py tests/contract/test_ao57_ct_postgres_runtime_repository.py tests/contract/test_ao56_ct_sdlc_executable_task_runtime_bridge.py tests/contract/test_ao23_ct_production_runtime_boundary.py tests/contract/test_ao15_ct_console_sdlc_run_workbench.py -q`：通过。
- `uv run ruff check ...`：通过。
- `npm test --prefix apps/agentops-console`：通过。
- `npm run build --prefix apps/agentops-console`：通过。
- `docker compose config`：通过。
- `uv run pytest tests/contract/test_ao64_ct_access_readiness.py -q`：通过。
- `uv run ruff check src/agentops/ops/access_readiness.py scripts/agentops-access-readiness.py tests/contract/test_ao64_ct_access_readiness.py`：通过。
- `uv run agentops-access-readiness --token local-agentops-gateway-token --json`：通过，`overall=pass`。

## 环境限制

- 默认 sandbox 网络无法访问 compose 暴露端口，`python scripts/agentops-access-readiness.py --token local-agentops-gateway-token --json` 在 sandbox 内返回 fail-closed `TRANSPORT_ERROR` JSON。
- 提升到本机网络后 live access readiness 已通过，确认本地 compose 服务稳定；该限制属于执行环境网络隔离，不属于 AgentOps 服务异常。
- 可重复 live smoke 已通过 `docker-compose.yml`、`docs/engineering/ai-sdlc-agentops-e2e-smoke.md` 和 `docs/engineering/agentops-access-readiness.md` 固化。
