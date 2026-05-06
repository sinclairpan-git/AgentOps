# Contract：AgentOps Console 运行事实数据源

## AO5-CT-001 Repository-backed Snapshot

给定仓库内存在一组完整 L5 核心事件，调用 `build_console_snapshot(repository=repo)` 时：

- `source_detail.mode` 必须为 `repository_backed`。
- `runs` 必须包含对应 `run_id`。
- 完整事件链必须显示 `l5_state=healthy`。
- evidence summary 只能包含摘要和 hash，不得包含 raw payload。

## AO5-CT-002 HTTP Ingestion to Snapshot

给定本地 HTTP server 和空仓库，调用 `POST /v1/events` 写入合法事件后，再调用 `GET /v1/console/snapshot`：

- 写入结果必须包含 `accepted` 或 `deduplicated`。
- snapshot 必须展示对应 run。
- response 必须为 JSON。

## AO5-CT-003 Empty State

空仓库 snapshot 必须保持 schema 完整，前端 validator 必须接受 `empty` 状态并显示中文标签“暂无数据”。

## AO5-CT-004 No Raw Payload

snapshot 任意层级不得包含 `raw_payload`。

## AO5-CT-005 Adapter Truth

repository-backed 只证明数据源可用，不证明治理宿主加载成功。除非有非占位、机器可验证证明，否则 adapter 和 sdlcRuns 不得展示 `verified_loaded`。

## AO5-CT-006 Event Ingestion Safety

`POST /v1/events` 必须覆盖：

- 重复 `idempotency_key` 返回 `deduplicated` 且不重复增加 run。
- 缺签名或坏 envelope 返回 `rejected`，包含既有 `error_code`、`retryable`、`human_action_required`。
- mixed batch 同时返回 accepted/rejected，snapshot 只反映 accepted。
- 非 JSON 或缺少 `events` 返回 400 JSON。
- allowed Origin 返回 CORS header，disallowed Origin 返回 403 JSON。

## AO5-CT-007 API Assembly Truth

`src/agentops/api/app.py` 必须把 ingestion 真值声明为 `POST /v1/events`，避免契约文档、HTTP server 和应用装配漂移。
