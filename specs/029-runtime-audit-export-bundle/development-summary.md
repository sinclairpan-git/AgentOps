# 开发总结：Runtime Audit Export Bundle

**功能编号**：`029-runtime-audit-export-bundle`
**完成日期**：2026-05-08

## 交付内容

- 新增 `POST /v1/audit/runtime/export-bundle`。
- 新增专用 `runtime.audit.export` scope，`agentops-admin` 与 `agentops-operator` 具备，viewer 不具备。
- export bundle 要求 caller 提交 028 manifest 的 `manifest_id` 和 `content_digest`，并在生成 bundle 前重新计算当前 manifest。
- `manifest_id` 绑定 `content_digest`、`filters` 和 `limit`，防止相同 record set 被不同 query 复用。
- export bundle 使用同一份 audit records snapshot 进行 manifest gate 和 bundle response 构造，避免并发写入导致 manifest 与 records 不一致。
- 响应返回 `bundle_id`、`bundle_format`、`bundle_digest`、`manifest_id`、`manifest_digest`、`record_count`、`records`、`download_url=""`。
- bundle records 只包含 allowed audit metadata schema；`resource` 去除 query string，避免 token-like marker 泄漏。
- accepted、denied、rejected 请求均写入 `runtime.audit.export.bundle` durable audit evidence。

## 安全边界

- 不返回 raw request body、raw payload、tokens、device keys、credential secrets、credential material、raw audit file paths 或下载 URL。
- 本阶段不新增数据库、迁移框架、SIEM connector、通知管道、对象存储、签名 URL、租户 ABAC 或写回能力。
- manifest mismatch 返回 `AUDIT_EXPORT_MANIFEST_MISMATCH`，不返回 records。

## 验证

- `uv run pytest tests/contract/test_ao29_ct_runtime_audit_export_bundle.py -q`：通过，9 个测试通过。
- `uv run pytest tests/contract/test_ao23_ct_production_runtime_boundary.py tests/contract/test_ao24_ct_durable_audit_log.py tests/contract/test_ao25_ct_production_audit_coverage.py tests/contract/test_ao26_ct_runtime_audit_query.py tests/contract/test_ao27_ct_runtime_audit_pagination.py tests/contract/test_ao28_ct_runtime_audit_export_manifest.py tests/contract/test_ao29_ct_runtime_audit_export_bundle.py -q`：通过，57 个测试通过，1 个既有环境相关检查跳过。
- `uv run ruff check src tests`：通过。
- `uv run ai-sdlc verify constraints`：通过，无 BLOCKER。

## 后续缺口

- 生产数据库/迁移框架、SIEM connector、通知管道、对象存储、签名 URL 和真实导出文件管道仍未实现。
- 完整 IAM/JWT/OIDC、多租户 ABAC、租户级审计筛选仍属于后续生产化阶段。
