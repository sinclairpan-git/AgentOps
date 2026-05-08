# 功能规格：Durable Audit Log

**功能编号**：`024-durable-audit-log`
**创建日期**：2026-05-08
**状态**：已冻结
**输入**：Next production AgentOps slice after the production runtime boundary: introduce a durable append-only audit log so production authorization denials and accepted runtime actions have restart-persistent, machine-verifiable audit evidence without recording sensitive request bodies, tokens, device keys, credential secrets, or raw event payloads. This is the first bounded step toward the PRD production database / persistent audit gap.

**范围**：

- 新增生产运行边界的 append-only durable audit log，先覆盖鉴权拒绝与事件写入结果。
- 审计记录必须跨 HTTP handler / repository 实例重建后仍可读取，并且字段稳定、机器可验证。
- 审计记录只保存最小运行元数据：`audit_id`、`request_id`、`principal`、`roles`、`scopes`、`action`、`resource`、`outcome`、`denied_scope`、`error_code`、`recorded_at`。
- 审计记录不得保存 request body、raw payload、ingestion token、device key、credential secret 或 credential material。

**明确不覆盖**：

- 不引入生产数据库、迁移框架或外部服务依赖。
- 不实现完整 SIEM / 通知 / 告警管道。
- 不改变 023 已定义的 HTTP authorization contract。
- 不实现多租户隔离或 OIDC/JWT 校验；这些仍作为后续生产化阶段。

## 用户场景与测试（必填）

### 用户故事 1 - 生产拒绝可持久审计（优先级：P0）

作为平台管理员，我希望生产模式下的授权拒绝不仅返回 `audit_id`，还会写入可重启读取的审计日志，以便事后复核不依赖内存态。

**优先级说明**：023 已建立生产模式鉴权边界，但持久化审计仍是生产数据库缺口中的第一风险点。

**独立测试**：启动生产模式 HTTP handler，未带上游身份调用 `POST /v1/events`，断言响应仍为 401，审计 JSONL 文件新增拒绝记录；重新构造 audit log reader 后仍可读取该记录。

**验收场景**：

1. **Given** 生产模式启用 durable audit log，**When** 请求缺少上游 principal，**Then** 返回 `UPSTREAM_IDENTITY_REQUIRED` 且审计记录包含 `outcome=denied`、`denied_scope=event.ingest`。
2. **Given** 审计文件已写入，**When** 创建新的 audit log 实例读取同一路径，**Then** 记录仍可按稳定 schema 解析。

---

### 用户故事 2 - 生产写入结果有最小审计证据（优先级：P0）

作为平台管理员，我希望成功的事件写入也留下最小审计证据，以便确认生产运行边界接受了哪些上游主体的写操作。

**优先级说明**：事件写入是当前最核心 mutating route，必须先覆盖。

**独立测试**：带 `agentops-ingestor` 角色调用 `POST /v1/events`，断言响应为 202 且审计 JSONL 记录 `action=event.ingest`、`outcome=accepted`，不包含事件 payload。

**验收场景**：

1. **Given** 生产模式启用 durable audit log，**When** 授权 ingestor 写入事件，**Then** 事件被接受且审计记录包含 principal、roles/scopes、request_id、audit_id。
2. **Given** 请求体包含敏感字段名，**When** 写入完成或拒绝，**Then** 审计 JSONL 原文不包含 `raw_payload`、`token`、`device_key`、`credential_secret`。

---

### 边界情况

- audit log 未传入时，HTTP handler 行为与 023 完全兼容。
- audit file parent directory 不存在时，append 操作必须自动创建目录。
- 上游 header 使用大小写不同的名称时，审计记录仍沿用 023 的 case-insensitive identity parsing。
- 审计写入失败不得回显敏感请求体；本阶段通过标准库文件写入合同覆盖正常路径。

## 需求（必填）

### 功能需求

- **FR-001**：系统必须提供 append-only JSONL durable audit log，支持写入与重建后读取。
- **FR-002**：生产模式授权拒绝必须写入 `outcome=denied` 审计记录，包含 `audit_id`、`request_id`、`denied_scope` 和 `error_code`。
- **FR-003**：生产模式事件写入结果必须写入 `action=event.ingest` 审计记录，成功为 `outcome=accepted`，业务校验失败为 `outcome=rejected`。
- **FR-004**：审计记录不得包含 request body、raw payload、ingestion token、device key、credential secret 或 credential material。
- **FR-005**：route/application manifest 必须声明 durable audit boundary，便于治理和合同测试发现。

### 关键实体（如涉及数据则必填）

- **AuditRecord**：生产运行边界的最小审计事实，包含请求线索、主体、动作、结果、错误与时间戳。
- **JsonlAuditLog**：append-only 文件适配器，负责将 `AuditRecord` 追加到 JSONL 并按 schema 读回。

## 成功标准（必填）

### 可度量结果

- **SC-001**：`tests/contract/test_ao24_ct_durable_audit_log.py` 覆盖拒绝、成功写入、重启读取、防敏感字段泄露与 manifest 声明。
- **SC-002**：`uv run pytest tests/contract/test_ao24_ct_durable_audit_log.py -q` 通过。
- **SC-003**：`uv run pytest tests/contract/test_ao23_ct_production_runtime_boundary.py tests/contract/test_ao24_ct_durable_audit_log.py -q` 通过，证明 023 contract 未回退。
- **SC-004**：`uv run ruff check src tests` 与 `uv run ai-sdlc verify constraints` 通过。
