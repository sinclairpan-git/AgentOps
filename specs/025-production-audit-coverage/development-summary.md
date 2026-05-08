# 开发总结：Production Audit Coverage

**功能编号**：`025-production-audit-coverage`
**完成日期**：2026-05-08

## 交付内容

- 在 024 durable audit log 基础上，补齐生产受保护 HTTP route 的成功/业务失败审计。
- `GET /v1/console/snapshot` 成功读取写入 `console.snapshot.read/accepted`。
- `GET /v1/store-summary/{agent_id}` 成功读取和 query 缺失/业务失败写入 `store.summary.read` accepted/rejected。
- `GET /v1/bootstrap/credentials/{bootstrap_id}` 成功和 not-found 写入 `credential.read` accepted/rejected。
- `POST /v1/bootstrap/credentials/{bootstrap_id}/revoke` 成功和业务失败写入 `credential.revoke` accepted/rejected。
- `POST /v1/bootstrap/credentials/{bootstrap_id}/reissue` 成功和业务失败写入 `credential.reissue` accepted/rejected。

## 安全边界

- 025 不改变 023 authorization response contract 和 024 `AuditRecord` schema。
- Audit JSONL 只记录 route outcome 元数据，不记录 request body、raw payload、token、device key、credential secret、credential material 或 credential response 内容。
- `audit_log=None` 时 route 行为保持兼容；audit append `OSError` 仍由 024 隔离策略处理。
- 本阶段不新增数据库、audit query API、通知/SIEM、真实 IAM/JWT/OIDC 或多租户 ABAC。

## 验证

- `uv run pytest tests/contract/test_ao25_ct_production_audit_coverage.py -q`：通过。
- `uv run pytest tests/contract/test_ao23_ct_production_runtime_boundary.py tests/contract/test_ao24_ct_durable_audit_log.py tests/contract/test_ao25_ct_production_audit_coverage.py -q`：通过，1 个既有环境相关检查跳过。
- `uv run ruff check src tests`：通过。
- `uv run ai-sdlc verify constraints`：通过，无 BLOCKER。

## 后续缺口

- 生产数据库/迁移框架、audit query API、通知/SIEM 集成仍未实现。
- 完整 IAM/JWT/OIDC、多租户 ABAC、租户级审计筛选仍属于后续生产化阶段。
