# Console API Contract

## AO4-CT-001 Console Snapshot Schema

`GET /v1/console/snapshot` 必须返回 JSON：

- `schema_version`: `agentops.console.snapshot.v1`
- `generated_at`: ISO-8601 字符串
- `source`: `api_snapshot`
- `routes`: ConsoleRoute 列表
- `consoleData`: 003 Console 已冻结的数据结构

`consoleData` 至少包含：

- `summary`
- `runs`
- `evidence`
- `approvals`
- `policies`
- `quality`
- `risks`
- `connectors`
- `sdlcRuns`

## AO4-CT-002 HTTP API

- `GET /v1/health` 返回 `service=agentops-api`、`status=healthy`、`version`。
- `GET /v1/console/snapshot` 返回 200 JSON。
- 未知路径返回 404 JSON，包含 `error_code=NOT_FOUND`。

## AO4-CT-003 CORS

本地开发 Origin 的 JSON 响应必须包含：

- `Access-Control-Allow-Origin: <request origin>`
- `Access-Control-Allow-Methods: GET, OPTIONS`
- `Access-Control-Allow-Headers: Content-Type`

默认允许：

- `http://127.0.0.1:5173`
- `http://127.0.0.1:5174`
- `http://localhost:5173`
- `http://localhost:5174`

不得默认返回 `Access-Control-Allow-Origin: *`。非白名单 Origin 必须返回 403 JSON。

## AO4-CT-004 Evidence Safety

任意响应层级不得出现 `raw_payload` 字段。`redaction_failed` 只能展示 hash、告警与补救动作。

## AO4-CT-005 Adapter Truth

当 `proof_source` 或 `captured_at` 仍包含 `AGENTS.md`、`CLI 预演`、`待采集`、`待接入` 时，`verified_loaded` 必须保持 `unverified`。

## AO4-CT-006 Frontend Fallback

前端 API client 必须：

- API 成功时返回 `source=api_snapshot`。
- API 失败、超时、JSON 不合法、schema 不合法、非法状态枚举时返回 `source=mock_fallback`。
- 面向用户的错误/降级文案必须是中文，可保留 AgentOps、API、mock、snapshot 等固定名词。
