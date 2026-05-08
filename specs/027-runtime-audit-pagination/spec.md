# 功能规格：Runtime Audit Pagination

**功能编号**：`027-runtime-audit-pagination`
**创建日期**：2026-05-08
**状态**：已冻结
**输入**：Next production AgentOps slice after runtime audit query: add an opaque cursor pagination contract to GET /v1/audit/runtime so production operators can page through durable audit records with stable bounded responses. The cursor must preserve metadata-only behavior, avoid raw audit file paths or sensitive material, reject malformed cursor input with a durable audit record, and remain backwards compatible with the existing limit/filter query contract. This is not a database migration, SIEM connector, notification channel, export pipeline, or tenant ABAC implementation.

**范围**：

- 在既有 `GET /v1/audit/runtime` 上新增 `cursor` query parameter。
- 响应新增 `page_info`，包含当前游标、下一页游标和是否存在更多匹配记录。
- 游标必须为 opaque token，仅由服务端生成并验证；游标绑定当前 filters，不能跨 filters 复用。
- 保持 026 的 bounded `limit`、RBAC、metadata-only 和 malformed JSONL 跳过语义。

**明确不覆盖**：

- 不引入数据库、迁移框架、SIEM connector、通知管道、导出文件或租户 ABAC。
- 不改变 024 `AuditRecord` 写入 schema。
- 不提供任意 offset 参数、排序参数、删除、写回或原文访问。

## 用户场景与测试（必填）

### 用户故事 1 - 生产管理员分页查询 runtime audit（优先级：P0）

作为 AgentOps 生产管理员，我希望按页读取 runtime audit records，以便在审计记录较多时逐页定位问题，而不是一次性返回过多数据。

**优先级说明**：026 已提供 bounded query，但缺少下一页语义；生产审计读取需要稳定 continuation 才能处理超过单页上限的记录。

**独立测试**：预置 5 条匹配 audit records，使用 `limit=2` 查询第一页，断言返回 2 条、`has_more=true`、`next_cursor` 非空；携带该 cursor 查询第二页，断言返回后续记录且不重复。

**验收场景**：

1. **Given** durable audit log 中存在超过 limit 的匹配记录，**When** operator 按 action 查询，**Then** 返回当前页和下一页 cursor。
2. **Given** client 使用上一页 `next_cursor` 与相同 filters 查询，**When** 服务端处理 cursor，**Then** 返回后续匹配记录且不重复第一页记录。

---

### 用户故事 2 - malformed 或跨过滤条件游标安全拒绝（优先级：P0）

作为安全负责人，我希望 runtime audit cursor 不能被伪造或跨过滤条件误用，以免审计读取产生不可解释或越界的结果。

**优先级说明**：审计读取 API 是受保护生产面，错误 cursor 必须可解释、可审计、且不能泄露底层文件或敏感材料。

**独立测试**：使用 malformed cursor 查询，断言返回 `AUDIT_CURSOR_INVALID`，追加 `runtime.audit.read/rejected` audit record，响应不包含 audit 文件路径或敏感 marker。

**验收场景**：

1. **Given** malformed cursor，**When** operator 查询 audit runtime，**Then** 返回 400 `AUDIT_CURSOR_INVALID` 并留下 rejected audit record。
2. **Given** cursor 由 action=A 的第一页生成，**When** client 携带该 cursor 但改用 action=B 查询，**Then** 返回 400 `AUDIT_CURSOR_INVALID`。

---

### 边界情况

- 缺少 cursor 时行为与 026 保持兼容，从第一页开始。
- 最后一页返回 `has_more=false` 且 `next_cursor=""`。
- cursor 不得包含 raw audit path、request body、raw payload、token、device key、credential secret 或 credential material。
- 成功分页查询和非法 cursor 查询都必须继续写入 durable audit record。

## 需求（必填）

### 功能需求

- **FR-001**：系统必须在 `GET /v1/audit/runtime` 支持 opaque `cursor` query parameter。
- **FR-002**：系统必须在响应中返回 `page_info.cursor`、`page_info.next_cursor` 和 `page_info.has_more`。
- **FR-003**：缺少 cursor 时必须从第一页开始，并保持 026 response fields 兼容。
- **FR-004**：`next_cursor` 必须仅在还有更多匹配记录时返回。
- **FR-005**：cursor 必须绑定当前 filters；filters 不匹配或 cursor malformed 时必须返回 `AUDIT_CURSOR_INVALID`。
- **FR-006**：cursor 错误和成功分页读取都必须写入 durable audit record。
- **FR-007**：cursor/response 不得暴露 raw audit path、request body、raw payload、token、device key、credential secret 或 credential material。

### 关键实体（如涉及数据则必填）

- **RuntimeAuditCursor**：服务端生成的 opaque continuation token，包含版本、匹配 filters 和下一页偏移。
- **RuntimeAuditPageInfo**：响应分页元数据，包含当前 cursor、下一页 cursor 和 has_more。

## 成功标准（必填）

### 可度量结果

- **SC-001**：新增 AO27 contract tests 覆盖第一页、第二页、最后一页、malformed cursor、filter mismatch 和 anti-leak。
- **SC-002**：`uv run pytest tests/contract/test_ao27_ct_runtime_audit_pagination.py -q` 通过。
- **SC-003**：`uv run pytest tests/contract/test_ao23_ct_production_runtime_boundary.py tests/contract/test_ao24_ct_durable_audit_log.py tests/contract/test_ao25_ct_production_audit_coverage.py tests/contract/test_ao26_ct_runtime_audit_query.py tests/contract/test_ao27_ct_runtime_audit_pagination.py -q` 通过。
- **SC-004**：`uv run ruff check src tests` 与 `uv run ai-sdlc verify constraints` 通过。
