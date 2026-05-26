# 功能规格：AgentOps Production SDLC Runtime Operations

**功能编号**：`057-agentops-production-sdlc-runtime-operations`  
**创建日期**：2026-05-26  
**状态**：已实现，等待 PR checks / review 收口
**输入**：`docs/engineering/ai-sdlc-agentops-production-integration-coding-brief.md`、`specs/056-sdlc-v0-7-18-executable-task-runtime-bridge`、`specs/023-production-runtime-boundary`、Ai_AutoSDLC PR #66 合入状态。

## 背景

AO56 和 PR #58 已完成 AgentOps 对 Ai_AutoSDLC v0.7.18 runtime bridge 的 consumer 契约、fixture、receipt、Trace/Evidence/Console readback 支持。Ai_AutoSDLC 侧也已合入 producer bridge 基础能力。

但当前能力仍停留在 contract-complete / local-in-memory 阶段：

- AgentOps API 默认使用 `InMemoryRepository`，重启后 runtime facts、trace spans、outbox receipts 和 diagnostics 会丢失。
- 生产认证边界已支持上游 `X-AgentOps-*` 身份头，但 AI-SDLC 生产路径决定采用 API Gateway Bearer token -> upstream headers 的方式，AgentOps 侧还缺少对应部署验收与 gateway contract tests。
- Console 可以读本地 snapshot，但还没有面向 PostgreSQL facts 的生产 readback 验收。
- 两项目联调还缺少“真实 `ai-sdlc run` -> Gateway -> AgentOps -> Console”的可重复 smoke。

本工作项将 AgentOps 从 SDLC runtime bridge 的消费者实现升级为可部署、可持久化、可认证、可观测的生产接入面。

## 目标

- 使用 PostgreSQL 作为 AgentOps runtime facts、receipts、DLQ、evidence/quality summaries 和 audit 的生产主库。
- 保持 Redis 为可选实时加速层，不作为 canonical facts 主存储。
- 保持 API Gateway 作为生产认证边界：AI-SDLC 只发送 Bearer token，Gateway 注入 `X-AgentOps-*` headers，AgentOps 只信上游 identity。
- 提供本地和服务器部署入口，使 AgentOps API、PostgreSQL、Console 和 Gateway path 能被一键或清单化启动。
- 确保 receipt 只有在 canonical facts 持久化成功后才返回 delivered / accepted。
- 提供跨项目 smoke 验收，证明 Ai_AutoSDLC 主流程产生的数据能在 AgentOps Console 中看到。

## 非目标

- 不在 AgentOps 内实现统一登录、OIDC、JWT issuer 或 KMS/HSM。
- 不让 AgentOps 直接执行 SDLC、重放 SDLC outbox 或调度 AI-SDLC。
- 不把 Agent Store 变成 runtime outbox 必经中转。
- 不用 Redis 替代 PostgreSQL 作为 runtime facts 或 audit truth。
- 不改变 AO56 event schema、receipt schema 或 `verified_loaded` diagnostic-only 语义。
- 不在 Console 暴露 raw payload、diff、PR 原文、token、device key 或 credential secret。

## 用户故事与验收场景

### 用户故事 1 - 生产持久化接收 SDLC runtime facts（P0）

作为 AgentOps 管理员，我希望 Ai_AutoSDLC 上报的 runtime batch 写入 PostgreSQL，服务重启后仍可查询 Trace、EvidenceSummary、outbox receipt 和 diagnostics。

**验收场景**：

1. Given AgentOps 使用 `AGENTOPS_DATABASE_URL` 启动，When `POST /v1/runtime/events` 接收 AO56 fixture，Then PostgreSQL 中存在 runtime event、trace span、receipt 和 audit 记录。
2. Given AgentOps API 重启，When 查询 `/v1/runtime/runs/{run_id}/trace` 和 `/v1/runtime/runs/{run_id}/evidence-summary`，Then 仍返回 summary-only readback。
3. Given 同一 outbox replay，When 使用相同 idempotency keys 再次投递，Then receipt 返回 deduplicated/replayed 语义，不重复写入 canonical facts。

### 用户故事 2 - API Gateway 生产认证闭环（P0）

作为平台 Owner，我希望 AI-SDLC 生产上报只通过 Gateway Bearer token，AgentOps 只消费 Gateway 注入的 upstream identity headers，避免本地 producer 伪造生产权限。

**验收场景**：

1. Given AgentOps `require_auth=true`，When 请求缺少 `X-AgentOps-Principal`，Then 返回 `UPSTREAM_IDENTITY_REQUIRED`。
2. Given Gateway 注入 `X-AgentOps-Roles=agentops-ingestor` 或 `X-AgentOps-Scopes=event.ingest`，When 转发 batch，Then AgentOps 接收并返回 receipt。
3. Given viewer scope 调用 runtime ingestion，Then 返回 `AGENTOPS_SCOPE_DENIED` 且不写入 facts。
4. Given 外部请求自带 `X-AgentOps-*` 头进入 Gateway，Then Gateway 必须清洗并重建 headers；AgentOps contract tests 固化只信上游边界。

### 用户故事 3 - 可部署运行（P0）

作为运维人员，我希望本地和服务器都能用清晰命令启动 AgentOps API、PostgreSQL 和 Console，并能把 Console 指向 Gateway 或 API base URL。

**验收场景**：

1. Given docker compose 或等价部署配置，When 执行启动命令，Then AgentOps API health、PostgreSQL migration、Console 静态资源/API base config 都可用。
2. Given `VITE_AGENTOPS_API_BASE` 指向 Gateway/AgentOps，When Console 打开 SDLC workbench，Then 从真实 API 获取 snapshot，不依赖 mock。
3. Given production mode，When AgentOps API 没有 DB connection，Then fail closed，不返回虚假的 delivered receipt。

### 用户故事 4 - 跨项目可用联调（P0）

作为 AI-Native 底座 Owner，我希望执行一次真实或受控 `ai-sdlc run` 后，AgentOps Console 能展示对应 run 的 task guard、receipt、Trace 和 Evidence readiness。

**验收场景**：

1. Given Ai_AutoSDLC 配置 Gateway endpoint 和 token，When 执行 `ai-sdlc run --dry-run` 或受控 test run，Then AI-SDLC 本地 receipt summary 显示 `accepted_count > 0`。
2. Given AgentOps PostgreSQL 持久化成功，When 查询 Console snapshot，Then `sdlcRunWorkbench.taskGuard`、`outboxReceipts`、`evidenceReadiness`、`adapterDiagnostics` 包含该 run。
3. Given AgentOps temporarily unavailable，When AI-SDLC retry 后恢复，Then AgentOps receipt 体现 `network_replay` 并保持 idempotency。

## 功能需求

- **FR-001**：AgentOps 必须提供 PostgreSQL-backed repository，实现 runtime events、trace spans、guardrail results、runtime outbox receipts、DLQ、evidence summaries、quality summaries 和 audit records 的持久化。
- **FR-002**：PostgreSQL schema 必须包含唯一约束和索引：`event_id`、`idempotency_key`、`batch_id`、`outbox_id`、`run_id`、`trace_id`、`run_id + attempt_no + span_id`。
- **FR-003**：`POST /v1/runtime/events` 的 accepted/delivered receipt 必须在 DB transaction commit 成功后返回。
- **FR-004**：AgentOps 生产模式必须继续使用 upstream identity headers；Gateway Bearer token 校验不在 AgentOps API 内实现为主路径。
- **FR-005**：AgentOps 必须补充 Gateway path 契约测试：缺 identity、scope denied、ingestor accepted、headers 不泄露 token/raw payload。
- **FR-006**：AgentOps 必须提供部署配置或文档，覆盖本地 compose、服务器环境变量、DB migration、Console API base 和 production auth。
- **FR-007**：Console 必须支持读取真实 persisted runtime facts 后的 SDLC workbench，不依赖内存进程状态。
- **FR-008**：AgentOps 必须提供可重复的 cross-project smoke 指南或脚本，覆盖 Ai_AutoSDLC -> Gateway -> AgentOps -> Console。
- **FR-009**：Redis 如引入，只能作为缓存、实时状态、队列或推送加速层；不得作为 runtime facts、receipt 或 audit 的唯一真相。
- **FR-010**：所有 rejected、stale、DLQ 和 auth failures 必须有 summary-only diagnostics，不得静默吞掉。

## 成功标准

- **SC-001**：新增 PostgreSQL repository contract tests 通过，并覆盖重启后 readback。
- **SC-002**：AO56 fixture 通过 production auth + DB persistence path。
- **SC-003**：Gateway path contract tests 覆盖 `UPSTREAM_IDENTITY_REQUIRED`、`AGENTOPS_SCOPE_DENIED` 和 `event.ingest` accepted。
- **SC-004**：Console snapshot 从 persisted data 构建 SDLC workbench。
- **SC-005**：跨项目 smoke 证明真实 Ai_AutoSDLC run 被 AgentOps 接收并展示。
- **SC-006**：`python -m ai_sdlc run --dry-run`、相关 `uv run pytest`、Console `npm test` 和 `npm run build` 通过。
