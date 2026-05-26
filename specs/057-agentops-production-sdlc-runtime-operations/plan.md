# 实施计划：AgentOps Production SDLC Runtime Operations

## 总体策略

本工作项分为三个可交付边界：生产持久化、Gateway 认证路径、跨项目可用联调。优先保证 canonical facts 不丢，再解决实时反馈和运维体验。

## 技术切片

### Slice 1：PostgreSQL runtime repository

- 新增 PostgreSQL schema / migration。
- 抽象 repository construction，保留 `InMemoryRepository` 作为 tests/local fallback。
- 实现 runtime facts、trace spans、guardrail results、outbox receipts、DLQ、audit 的持久化读写。
- 使用 transaction 保证 receipt 返回前 facts 已提交。

验证：repository contract tests、AO56 fixture DB path、API 重启 readback。

### Slice 2：Production auth through API Gateway

- 固化 AgentOps 对 upstream identity headers 的生产依赖。
- 增加 Gateway path contract tests：ingestor role/scope accepted，viewer denied，missing identity denied。
- 明确 AgentOps 不消费客户端自带 Bearer token 作为主生产路径。
- 文档化 Gateway 清洗并注入 `X-AgentOps-*` headers 的要求。

验证：AO23 + 新 AO57 auth tests。

### Slice 3：Deployable AgentOps service

- 增加或更新部署入口：
  - API env config
  - PostgreSQL connection
  - production auth flag
  - Console `VITE_AGENTOPS_API_BASE`
  - local compose / server deployment notes
- API health 不依赖认证，runtime ingestion 在 production mode fail closed。

验证：compose/local smoke、health、ingestion、Console snapshot。

### Slice 4：Console persisted readback

- 确认 Console snapshot 从 repository persisted facts 构建。
- 增加 regression test，避免仅内存同进程可见。
- 保留 AO56 span-only readback 能力。

验证：AO4/AO15/AO56 contract tests。

### Slice 5：Cross-project smoke

- 编写联调脚本或手册：
  - 启动 AgentOps + DB
  - 启动 Gateway
  - 配置 Ai_AutoSDLC
  - 执行 `ai-sdlc run`
  - 验证 receipt / trace / evidence / console
- 记录失败场景：bad token、missing scope、AgentOps down、schema invalid、network replay。

验证：手工或自动 smoke 归档到 task execution log。

## 数据库设计原则

- PostgreSQL 是 canonical facts 主库。
- JSON payload 只保存 summary-only envelope / diagnostics；不得保存 raw diff、raw file、token 或 secret。
- 关键字段独立列化，半结构化摘要进入 `jsonb`。
- 所有幂等和 replay 相关字段必须有唯一索引或冲突处理。
- Redis 仅作为后续可选实时层，不阻塞 P0。

## 风险与缓解

| 风险 | 缓解 |
|---|---|
| DB schema 太早过度设计 | 先覆盖 AO56 runtime path 和 existing operations，保留 jsonb 扩展字段 |
| Gateway 与 AgentOps auth 责任混淆 | AgentOps 只信 upstream headers；Gateway 校验 Bearer 并注入 headers |
| Console 仍读 mock 或内存 | 增加 persisted readback contract tests |
| receipt 在 DB 失败前返回 accepted | ingestion transaction 必须先 commit 再返回 receipt |
| Redis 被误用成 facts truth | spec 明确 Redis 仅缓存/队列/实时层 |

## 验证命令

```bash
python -m ai_sdlc run --dry-run
uv run pytest tests/contract/test_ao56_ct_sdlc_executable_task_runtime_bridge.py tests/contract/test_ao23_ct_production_runtime_boundary.py -q
npm test --prefix apps/agentops-console
npm run build --prefix apps/agentops-console
```

