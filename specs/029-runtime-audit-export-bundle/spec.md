# 功能规格：Runtime Audit Export Bundle

**功能编号**：`029-runtime-audit-export-bundle`
**创建日期**：2026-05-08
**状态**：冻结
**输入**：Next production AgentOps slice after runtime audit export manifest: add a manifest-gated metadata-only Runtime Audit Export Bundle HTTP route so production operators can materialize bounded audit metadata for external review only when the submitted manifest id and digest still match the current filtered audit metadata. The route must require a dedicated runtime.audit.export scope, reuse audit filters and limit semantics, return records only in the stable allowed audit metadata schema, include bundle and manifest digests, append durable audit evidence for accepted, denied, and rejected requests, and never expose request bodies, raw payloads, tokens, device keys, credential secrets, credential material, raw audit file paths, or downloadable URLs. This is not a database migration, SIEM connector, notification channel, tenant ABAC implementation, signed URL service, or raw audit export pipeline.

**范围**：本阶段承接 028 export manifest，新增一个 manifest-gated 的 metadata-only export bundle HTTP contract。它允许生产管理员在 manifest 仍匹配当前审计元数据时导出 bounded audit metadata records，用于外部复核；不生成文件、不返回下载 URL、不暴露 raw payload 或凭据材料。

## 用户场景与测试（必填）

### 用户故事 1 - 生产管理员生成受 manifest 约束的审计导出包（优先级：P0）

作为 AgentOps 生产管理员，我希望先用 028 manifest 锁定过滤条件和 digest，再用该 manifest 生成 metadata-only export bundle，以便外部复核方可以验证导出内容没有偏离清单。

**优先级说明**：028 已能生成导出清单，但生产导出链路仍缺少“manifest 与导出内容绑定”的最小闭环。029 先交付 bounded inline bundle，不引入对象存储、签名 URL 或真实 SIEM。

**独立测试**：通过 contract test 启动标准库 HTTP server，先请求 `GET /v1/audit/runtime/export-manifest`，再使用 manifest id/digest 调用 `POST /v1/audit/runtime/export-bundle`，验证 response schema、records、bundle digest、manifest mismatch、专用 scope 和 durable audit evidence。

**验收场景**：

1. **Given** durable audit log 存在多条 metadata records，**When** 管理员提交匹配的 manifest id/digest 和相同 filters/limit，**Then** 返回 `agentops.runtime_audit.export_bundle.v1`、bounded metadata records、manifest digest、bundle digest，且写入 `runtime.audit.export.bundle/accepted` audit。
2. **Given** 调用者只有 `runtime.audit.read` 或 viewer 权限，**When** 请求 export bundle，**Then** 返回 scope denied，且写入 `runtime.audit.export.bundle/denied` audit。
3. **Given** 调用者提交过期或伪造的 manifest digest，**When** 请求 export bundle，**Then** 返回 `AUDIT_EXPORT_MANIFEST_MISMATCH`，不返回 records，并写入 rejected audit。
4. **Given** audit log path、query token 或敏感字段 marker 存在，**When** 请求 export bundle，**Then** 响应不得包含 raw path、request body、raw payload、token、device key、credential secret、credential material 或下载 URL。

---

### 边界情况

- `filters` 仅支持 `audit_id`、`request_id`、`action`、`outcome`；未知 filter 或非字符串 filter 值必须拒绝。
- `limit` 复用 026-028 的正整数和最大值 clamp 语义；不支持无界导出。
- broad bundle 与 028 broad manifest 一样，在未提供 `action` filter 时排除 `runtime.audit.export` / `runtime.audit.export.bundle` 自身审计记录，避免导出请求污染后续 digest。
- 显式 `action=runtime.audit.export` 或 `action=runtime.audit.export.bundle` 必须保留 action filter 语义。
- audit log 未配置时返回 `AUDIT_LOG_UNAVAILABLE`，不伪造空导出。

## 需求（必填）

### 功能需求

- **FR-001**：系统必须新增 `POST /v1/audit/runtime/export-bundle`。
- **FR-002**：该 route 必须要求专用 `runtime.audit.export` scope；`agentops-admin` 和 `agentops-operator` 默认具备该 scope，viewer 不具备。
- **FR-003**：请求体必须包含 `manifest_id`、`content_digest`、`filters` 和 `limit`，并用当前 filtered audit metadata 重新计算 manifest；`manifest_id` 必须绑定 `content_digest`、`filters` 和 `limit`，任一不匹配都必须拒绝。
- **FR-004**：响应必须包含 `schema_version`、`bundle_id`、`bundle_format`、`digest_algorithm`、`bundle_digest`、`manifest_id`、`manifest_digest`、`record_count`、`limit`、`filters`、`records`、`download_url`。
- **FR-005**：`records` 必须只包含 allowed audit metadata schema，且 `resource` 不得包含 query string 或敏感 marker。
- **FR-006**：`bundle_digest` 必须基于 manifest id、manifest digest 和 records 的 canonical JSON SHA-256 计算，且同一 log/filter/limit/manifest 输入稳定。
- **FR-007**：accepted、denied 和 rejected export bundle 请求都必须写入 durable audit evidence，action 为 `runtime.audit.export.bundle`。
- **FR-008**：本阶段不得引入数据库、迁移框架、SIEM connector、通知管道、tenant ABAC、签名 URL、对象存储、写回能力或原文导出。

### 关键实体（如涉及数据则必填）

- **RuntimeAuditExportBundle**：metadata-only 导出响应，包含 manifest 绑定信息、digest、bounded audit metadata records 和不可下载边界。
- **ManifestGate**：使用 caller 提交的 `manifest_id` / `content_digest` 与当前计算结果比较的导出前置门禁。
- **BundleDigest**：对 manifest 绑定信息与 records 的 canonical JSON SHA-256 摘要。

## 成功标准（必填）

### 可度量结果

- **SC-001**：匹配 manifest 的有权限请求返回 200，且 records、record_count、manifest_digest、bundle_digest 可验证。
- **SC-002**：缺少 `runtime.audit.export` scope 的请求返回 denied，并写入 `runtime.audit.export.bundle/denied`。
- **SC-003**：manifest id/digest mismatch 返回 `AUDIT_EXPORT_MANIFEST_MISMATCH`，不返回 records，并写入 rejected audit。
- **SC-004**：响应 JSON 不包含 raw path、request body、raw payload、token、device key、credential secret、credential material 或非空 download URL。
- **SC-005**：AO23-AO29 contract regression、ruff 和 `ai-sdlc verify constraints` 全部通过。
