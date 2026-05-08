# 功能规格：Production Audit Coverage

**功能编号**：`025-production-audit-coverage`
**创建日期**：2026-05-08
**状态**：已冻结
**输入**：Next production AgentOps slice after durable audit log: extend restart-persistent runtime audit coverage to every production-protected HTTP route, not only event ingestion. Credential status reads, credential revoke/reissue writes, console snapshot reads, and Agent Store summary reads must write minimal accepted/rejected audit records without recording request bodies, tokens, device keys, credential secrets, raw payloads, or credential material. Auth denials remain covered by 023/024.

**范围**：

- 在 024 的 durable audit log 基础上，为生产模式下所有受保护 HTTP route 的成功与业务失败分支追加最小审计记录。
- 覆盖路由：`GET /v1/console/snapshot`、`GET /v1/store-summary/{agent_id}`、`GET /v1/bootstrap/credentials/{bootstrap_id}`、`POST /v1/bootstrap/credentials/{bootstrap_id}/revoke`、`POST /v1/bootstrap/credentials/{bootstrap_id}/reissue`，以及 024 已覆盖的 `POST /v1/events` 回归。
- 审计记录只保存 route/action/outcome/error_code/principal/roles/scopes/request_id/audit_id/resource 等最小元数据。
- 不写入 request body、raw payload、ingestion token、device key、credential secret、credential material 或 credential response 内容。

**明确不覆盖**：

- 不引入数据库、队列、SIEM、通知管道或 audit query HTTP API。
- 不改变 023/024 的鉴权拒绝响应和审计 schema。
- 不实现真实 IAM/JWT/OIDC、多租户 ABAC 或生产密钥管理。

## 用户场景与测试（必填）

### 用户故事 1 - 受保护读路由有成功/失败审计（优先级：P0）

作为平台管理员，我希望生产模式下的 Console snapshot、Agent Store summary 和 credential status 读路由在成功或业务失败时都留下 durable audit 记录，以便敏感读访问可复核。

**优先级说明**：023 已保护敏感读，024 已持久化鉴权拒绝；成功读访问仍缺审计事实。

**独立测试**：带 viewer/consumer 权限访问受保护读路由，断言响应与审计 JSONL 中 `outcome=accepted/rejected`、`action`、`resource`、principal 一致，且不包含敏感字段。

**验收场景**：

1. **Given** production auth 和 audit log 已启用，**When** viewer 成功读取 Console snapshot，**Then** audit log 追加 `action=console.snapshot.read`、`outcome=accepted`。
2. **Given** store summary 查询缺少必要 query，**When** consumer 调用该 route，**Then** audit log 追加 `action=store.summary.read`、`outcome=rejected`、`error_code=STORE_SUMMARY_QUERY_REQUIRED`。

---

### 用户故事 2 - Credential 写路由有成功/失败审计（优先级：P0）

作为安全/IAM 负责人，我希望 credential revoke/reissue 的成功和业务失败都进入 durable audit，以便凭证生命周期变更可以复核。

**优先级说明**：credential revoke/reissue 是生产写接口，必须与 event ingest 一样留下持久审计。

**独立测试**：构造 credential 事实后调用 revoke 成功；构造不存在的 reissue source 调用失败；断言 audit log 记录 `credential.revoke` 和 `credential.reissue` 的 accepted/rejected 且不写入 credential secret。

**验收场景**：

1. **Given** credential 已存在，**When** operator revoke，**Then** audit log 追加 `action=credential.revoke`、`outcome=accepted`、`resource` 为 bootstrap route。
2. **Given** reissue source 不存在，**When** operator reissue，**Then** audit log 追加 `action=credential.reissue`、`outcome=rejected`、`error_code=CREDENTIAL_REISSUE_NOT_FOUND`。

---

### 边界情况

- `audit_log=None` 时所有 route 保持既有行为。
- audit append 抛出 `OSError` 时不得中断 API 响应，沿用 024 隔离策略。
- 业务失败审计不得把错误响应以外的 request body 或 credential response 内容写入 audit log。
- Auth denial 继续由 024 `_send_auth_error` 覆盖，本阶段不重复扩大响应 schema。

## 需求（必填）

### 功能需求

- **FR-001**：所有生产受保护读路由成功时必须追加 `outcome=accepted` durable audit record。
- **FR-002**：所有生产受保护读路由业务失败时必须追加 `outcome=rejected` 且包含稳定 `error_code`。
- **FR-003**：credential revoke/reissue 成功与业务失败必须追加 durable audit record。
- **FR-004**：audit record 不得包含 request body、raw payload、token、device key、credential secret、credential material 或 credential response 内容。
- **FR-005**：024 event ingest audit contract 必须继续通过。

### 关键实体（如涉及数据则必填）

- **RouteAuditEvent**：受保护 HTTP route 的最小 runtime audit 事实，复用 024 `AuditRecord` schema。
- **ProtectedRouteOutcome**：route 处理结果，映射为 `accepted`、`rejected` 或 `denied`。

## 成功标准（必填）

### 可度量结果

- **SC-001**：新增 AO25 contract tests 覆盖 console/store/credential read/write 的 accepted 与 rejected audit。
- **SC-002**：`uv run pytest tests/contract/test_ao25_ct_production_audit_coverage.py -q` 通过。
- **SC-003**：`uv run pytest tests/contract/test_ao23_ct_production_runtime_boundary.py tests/contract/test_ao24_ct_durable_audit_log.py tests/contract/test_ao25_ct_production_audit_coverage.py -q` 通过。
- **SC-004**：`uv run ruff check src tests` 与 `uv run ai-sdlc verify constraints` 通过。
