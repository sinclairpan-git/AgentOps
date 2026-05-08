# 实施计划：Runtime Audit Export Manifest

**编号**：`028-runtime-audit-export-manifest` | **日期**：2026-05-08 | **规格**：specs/028-runtime-audit-export-manifest/spec.md

## 概述

028 承接 026/027 的 runtime audit query/pagination，新增 `GET /v1/audit/runtime/export-manifest`。该接口只生成 metadata-only manifest 和 digest，帮助生产管理员把“这一批审计记录是什么”交给复核或外部流程，而不提供文件下载、不暴露 raw audit file path、不输出请求原文或凭据材料。

## 技术背景

**语言/版本**：Python 3.11+，标准库 HTTP server。
**主要依赖**：沿用现有 `agentops.api.server`、`JsonlAuditLog`、`AuditRecord`、`AgentOpsError`。
**存储**：沿用 append-only JSONL durable audit log；本阶段不新增数据库或迁移。
**测试**：pytest contract tests，覆盖 HTTP scope、digest、anti-leak、durable audit evidence。
**目标平台**：macOS/Linux/Windows Python contract tests。
**约束**：metadata-only、bounded、read-only、durably audited；不引入 SIEM/通知/导出文件/tenant ABAC。

## 宪章检查

| 宪章门禁 | 计划响应 |
|----------|----------|
| 生产边界必须有机器可验证证据 | 新增 AO28 contract tests 验证 accepted/denied/rejected audit evidence |
| 不得暴露 Evidence Vault / credential 原文 | manifest 只包含 digest、record_count、record_audit_ids 和 filters，不包含 raw records 或下载 URL |
| 兼容既有 runtime audit query | 复用 026/027 filters 和 limit parser，不改变 `/v1/audit/runtime` response |
| 变更必须可回归 | 跑 AO23-AO28 contract regression、ruff、constraints、close-check |

## 项目结构

### 文档结构

```text
specs/028-runtime-audit-export-manifest/
├── spec.md
├── plan.md
├── tasks.md
├── task-execution-log.md
└── development-summary.md
```

### 源码结构

```text
src/agentops/api/server.py
src/agentops/storage/audit.py
tests/contract/test_ao28_ct_runtime_audit_export_manifest.py
program-manifest.yaml
```

## 阶段计划

### Phase 0：范围冻结

**目标**：冻结 export manifest route、response contract、安全边界和非目标。
**产物**：`spec.md`、`plan.md`、`tasks.md`。
**验证方式**：文档对账 + constraints。
**回退方式**：删除 028 spec mapping 和新增 docs。

### Phase 1：契约测试红灯

**目标**：新增 AO28 contract tests，先证明接口不存在或行为未实现。
**产物**：`tests/contract/test_ao28_ct_runtime_audit_export_manifest.py`。
**验证方式**：`uv run pytest tests/contract/test_ao28_ct_runtime_audit_export_manifest.py -q` 红灯。
**回退方式**：移除 AO28 测试文件。

### Phase 2：实现 export manifest

**目标**：在标准库 HTTP handler 中实现受保护的 metadata-only manifest。
**产物**：`src/agentops/api/server.py`。
**验证方式**：AO28 定向测试绿灯。
**回退方式**：移除 route 和 helper。

### Phase 3：归档与收口

**目标**：同步 docs、manifest、truth snapshot，完成 close-check。
**产物**：`development-summary.md`、`task-execution-log.md`、`program-manifest.yaml`。
**验证方式**：AO23-AO28 回归、ruff、constraints、close-check。
**回退方式**：回滚本批提交。

## 工作流计划

### 工作流 A：runtime audit export manifest

**范围**：新增 `GET /v1/audit/runtime/export-manifest`。
**影响范围**：HTTP handler route、audit query helper、AO28 contract tests。
**验证方式**：权限、digest、anti-leak、invalid limit 和 durable audit evidence。
**回退方式**：删除新增 route/helper/test/doc。

## 关键路径验证策略

| 关键路径 | 主验证方式 | 次验证方式 |
|----------|------------|------------|
| 有权限 manifest 生成 | AO28 contract test | AO23-AO28 回归 |
| 无权限 denied audit | AO28 contract test | 024/025 audit regression |
| 非法 limit rejected audit | AO28 contract test | 026 query regression |
| anti-leak | JSON serialized assertion | ruff + code review |
| SDLC 收口 | `ai-sdlc verify constraints` / close-check | Program Truth Sync |

## 开放问题

| 问题 | 状态 | 阻塞阶段 |
|------|------|----------|
| 是否直接生成下载文件 | 决策：否，只输出 manifest 和 digest | 不阻塞 |
| 是否接 SIEM/通知 | 决策：否，后续阶段处理 | 不阻塞 |
| 是否支持 tenant filters | 决策：否，后续 ABAC 阶段处理 | 不阻塞 |

## 实施顺序建议

1. 冻结 028 spec/plan/tasks。
2. 新增 AO28 红灯 contract tests。
3. 实现 route 和 digest helper。
4. 跑 AO28、AO23-AO28、ruff、constraints、truth sync、close-check。
5. 提交、推送、创建 PR 并触发固定 GitHub 收口流程。
