# 功能规格：Runtime Audit Export Manifest

**功能编号**：`028-runtime-audit-export-manifest`
**创建日期**：2026-05-08
**状态**：冻结
**输入**：Next production AgentOps slice after runtime audit pagination: expose a protected read-only Runtime Audit Export Manifest HTTP route so production operators can produce a deterministic metadata-only export manifest for durable audit records. The route must require runtime.audit.read scope, reuse bounded audit filters and limit semantics, return export metadata including record count and a deterministic digest over allowed audit metadata only, append durable audit evidence for accepted and rejected export requests, and never expose request bodies, raw payloads, tokens, device keys, credential secrets, credential material, raw audit file paths, or downloadable files. This is not a database migration, SIEM connector, notification channel, tenant ABAC implementation, or raw audit export pipeline.

**范围**：本阶段承接 026/027 的 runtime audit query 与 cursor pagination，新增一个只读 export manifest HTTP contract。它用于生成“可复核、可比对、可审计”的导出清单，而不是下载原文或写出文件。

## 用户场景与测试（必填）

### 用户故事 1 - 生产管理员生成审计导出清单（优先级：P0）

作为 AgentOps 生产管理员，我希望按既有 runtime audit filters 生成一个 metadata-only export manifest，以便把审计范围、记录数量和 digest 交给复核或外部流程，而不用暴露原始请求体、凭据或审计文件路径。

**优先级说明**：027 已支持分页读取审计记录，但生产导出流程还缺少一个不泄露原文的可复核边界；manifest 是导出管道前置的最小生产切片。

**独立测试**：通过 contract test 启动标准库 HTTP server，使用 `runtime.audit.read` scope 请求 `GET /v1/audit/runtime/export-manifest`，验证响应 schema、filters、record_count、digest、record_audit_ids 和 durable audit evidence。

**验收场景**：

1. **Given** durable audit log 存在多条 metadata records，**When** 管理员按 `action` 和 `limit` 请求 export manifest，**Then** 返回 `agentops.runtime_audit.export_manifest.v1`、稳定 digest、record_count、filters、record_audit_ids，且写入 `runtime.audit.export/accepted` audit。
2. **Given** 调用者缺少 `runtime.audit.read` scope，**When** 请求 export manifest，**Then** 返回 scope denied，且写入 `runtime.audit.export/denied` audit。
3. **Given** 请求携带非法 limit，**When** 请求 export manifest，**Then** 返回 `AUDIT_LIMIT_INVALID`，且写入 `runtime.audit.export/rejected` audit。
4. **Given** audit log path 或敏感字段 marker 存在，**When** 请求 export manifest，**Then** 响应不得包含 raw path、request body、raw payload、token、device key、credential secret、credential material 或下载 URL。

---

### 边界情况

- `limit` 复用 026/027 的正整数和最大值 clamp 语义；本阶段不新增无界导出。
- filters 仅复用 `audit_id`、`request_id`、`action`、`outcome`，不新增 tenant / ABAC filters。
- export manifest 不接收 cursor，不生成文件，不返回 raw records，不返回下载链接。
- audit log 未配置时返回 `AUDIT_LOG_UNAVAILABLE`，不伪造空导出。

## 需求（必填）

### 功能需求

- **FR-001**：系统必须新增 `GET /v1/audit/runtime/export-manifest`。
- **FR-002**：该 route 必须要求 `runtime.audit.read` scope，并在拒绝时写入 `runtime.audit.export/denied` durable audit record。
- **FR-003**：该 route 必须复用 runtime audit query 的 `audit_id`、`request_id`、`action`、`outcome` filters 和 `limit` 语义。
- **FR-004**：响应必须包含 `schema_version`、`manifest_id`、`digest_algorithm`、`content_digest`、`record_count`、`limit`、`filters`、`record_audit_ids`、`export_available`、`download_url`。
- **FR-005**：`content_digest` 必须基于 allowed audit metadata 的 canonical JSON 计算，且同一 log/filter/limit 输入稳定；无 `action` filter 的 broad manifest 必须排除 manifest 请求自身追加的 `runtime.audit.export` records，显式 `action=runtime.audit.export` filter 必须保留该 action 的过滤语义。
- **FR-006**：响应不得包含 raw audit file path、request bodies、raw payload、tokens、device keys、credential secrets、credential material 或可下载文件 URL。
- **FR-007**：accepted 和 rejected export manifest 请求都必须写入 durable audit evidence，action 分别为 `runtime.audit.export`，outcome 为 `accepted` 或 `rejected`。
- **FR-008**：本阶段不得引入数据库、迁移框架、SIEM connector、通知管道、tenant ABAC、写回能力或原文导出。

### 关键实体（如涉及数据则必填）

- **RuntimeAuditExportManifest**：导出清单响应，只包含筛选条件、数量、digest、记录 ID 列表和不可下载边界。
- **AuditMetadataDigest**：对 allowed audit metadata records 的 canonical JSON SHA-256 摘要。
- **ExportAuditEvidence**：对 manifest 请求本身的 durable audit record。

## 成功标准（必填）

### 可度量结果

- **SC-001**：有权限请求 export manifest 返回 200，且同一输入的 `content_digest` 稳定。
- **SC-002**：无权限请求返回 denied，并写入 `runtime.audit.export/denied`。
- **SC-003**：非法 limit 返回 `AUDIT_LIMIT_INVALID`，并写入 `runtime.audit.export/rejected`。
- **SC-004**：响应 JSON 不包含 raw path、raw payload、token、device key、credential secret、credential material 或 download URL。
- **SC-005**：AO23-AO28 contract regression、ruff 和 `ai-sdlc verify constraints` 全部通过。
