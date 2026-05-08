# 功能规格：Runtime Audit Query

**功能编号**：`026-runtime-audit-query`
**创建日期**：2026-05-08
**状态**：已冻结
**输入**：Next production AgentOps slice after production audit coverage: expose a protected read-only Runtime Audit Query HTTP route for production operators to inspect durable audit records written by 024/025. The route must require a new runtime.audit.read scope, allow bounded filtering by audit_id, request_id, action, outcome, and limit, return only the stable audit metadata schema, and never expose request bodies, raw payloads, tokens, device keys, credential secrets, credential material, or raw audit file paths. This is not a database migration, SIEM connector, notification channel, or tenant ABAC implementation.

**范围**：

- 新增只读 `GET /v1/audit/runtime` HTTP route，用于查询 024/025 写入的 durable runtime audit records。
- route 必须受生产 RBAC 保护，需要 `runtime.audit.read` scope；默认允许 `agentops-admin` 与 `agentops-operator`，不授予 viewer。
- 支持 bounded query：`audit_id`、`request_id`、`action`、`outcome`、`limit`。
- 返回只包含 024 `AuditRecord` 稳定字段和查询元数据，不暴露 raw audit file path、request body、raw payload、token、device key、credential secret 或 credential material。

**明确不覆盖**：

- 不引入数据库、分页游标、SIEM connector、通知管道或租户 ABAC。
- 不改变 024/025 audit write schema。
- 不实现审计记录写回、删除、导出文件或原文访问。

## 用户场景与测试（必填）

### 用户故事 1 - 生产管理员查询 runtime audit（优先级：P0）

作为 AgentOps 管理员，我希望通过受保护 API 查询 runtime audit records，以便定位某个 request、audit id 或 route action 的生产访问记录。

**优先级说明**：024/025 已写入 durable audit，但没有生产可消费读路径，审计事实仍停留在文件适配器层。

**独立测试**：预置 JSONL audit records，带 `agentops-operator` 角色访问 `/v1/audit/runtime?action=credential.revoke&limit=1`，断言只返回匹配记录、schema 固定、无敏感字段。

**验收场景**：

1. **Given** durable audit log 中存在多条记录，**When** operator 按 action 查询，**Then** 只返回匹配 action 且 `returned <= limit`。
2. **Given** 缺少 `runtime.audit.read` 权限，**When** viewer 调用该 route，**Then** 返回 403，并由 024 auth denial audit 记录 `denied_scope=runtime.audit.read`。

---

### 用户故事 2 - 审计查询不泄露底层材料（优先级：P0）

作为安全负责人，我希望 runtime audit query 只返回 allowlisted metadata，避免把 audit 文件路径、原始请求体或 credential 材料暴露给 API 使用者。

**优先级说明**：审计查询本身是敏感读 API，必须比普通业务摘要更严格。

**独立测试**：写入包含 token-like/resource-like 字符串的审计记录和损坏 JSONL 行，查询结果仍只包含稳定字段，不包含文件路径或敏感 marker，并跳过损坏行。

**验收场景**：

1. **Given** audit log 中存在 malformed JSONL 行，**When** 查询 runtime audit，**Then** API 正常返回可解析记录。
2. **Given** 请求 limit 缺失或过大，**When** 查询 runtime audit，**Then** 使用 bounded default/max，不返回无限结果。

---

### 边界情况

- `audit_log=None` 时 route 返回可解释 `AUDIT_LOG_UNAVAILABLE`，不泄露路径。
- `limit` 非数字或小于 1 时返回 `AUDIT_LIMIT_INVALID`。
- `limit` 大于最大值时 clamp 到最大值。
- filters 无匹配时返回空 `records` 和 `returned=0`。

## 需求（必填）

### 功能需求

- **FR-001**：系统必须提供 `GET /v1/audit/runtime` 只读 route。
- **FR-002**：route 必须要求 `runtime.audit.read` scope，并拒绝 viewer 默认角色。
- **FR-003**：route 必须支持 `audit_id`、`request_id`、`action`、`outcome`、`limit` filters。
- **FR-004**：route 必须返回 bounded records，默认 limit 50，最大 limit 200。
- **FR-005**：route 响应不得包含 raw audit path、request body、raw payload、token、device key、credential secret 或 credential material。
- **FR-006**：route 必须跳过 malformed JSONL 行并返回有效记录。

### 关键实体（如涉及数据则必填）

- **RuntimeAuditQuery**：query parameters 与 limit policy。
- **RuntimeAuditResult**：records、returned、limit、filters 的只读响应模型。

## 成功标准（必填）

### 可度量结果

- **SC-001**：新增 AO26 contract tests 覆盖权限、filter、limit、unavailable、anti-leak 和 malformed readback。
- **SC-002**：`uv run pytest tests/contract/test_ao26_ct_runtime_audit_query.py -q` 通过。
- **SC-003**：`uv run pytest tests/contract/test_ao23_ct_production_runtime_boundary.py tests/contract/test_ao24_ct_durable_audit_log.py tests/contract/test_ao25_ct_production_audit_coverage.py tests/contract/test_ao26_ct_runtime_audit_query.py -q` 通过。
- **SC-004**：`uv run ruff check src tests` 与 `uv run ai-sdlc verify constraints` 通过。
