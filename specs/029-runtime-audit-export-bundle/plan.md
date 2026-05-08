# 实施计划：Runtime Audit Export Bundle

**编号**：`029-runtime-audit-export-bundle` | **日期**：2026-05-08 | **规格**：specs/029-runtime-audit-export-bundle/spec.md

## 概述

029 承接 028 runtime audit export manifest，新增 `POST /v1/audit/runtime/export-bundle`。该接口在生成 metadata-only bundle 前重新计算 manifest，并要求 caller 提供的 `manifest_id` 和 `content_digest` 与当前结果一致，从而把“导出清单”推进到“受清单约束的 bounded 导出内容”。本阶段不做文件落盘、签名 URL、SIEM 或 raw audit export。

## 技术背景

**语言/版本**：Python 3.11+，标准库 HTTP server
**主要依赖**：现有 `agentops.api.server`、`agentops.api.auth`、`agentops.storage.audit`
**存储**：现有 append-only JSONL audit log；不新增数据库或对象存储
**测试**：pytest contract tests + ruff + AI-SDLC constraints
**目标平台**：本地/CI 跨平台 Python
**约束**：metadata-only、manifest-gated、bounded、durably audited；不返回下载 URL 或 raw payload

## 宪章检查

| 宪章门禁 | 计划响应 |
|----------|----------|
| 不暴露 Evidence Vault / credential 原文 | bundle records 只使用 allowed audit metadata schema，resource 去 query，禁止 raw payload/token/material |
| 人工治理与可审计性 | accepted/denied/rejected 均写入 durable audit evidence |
| 生产边界明确 | 新增专用 `runtime.audit.export` scope，viewer 不具备 |
| 兼容既有 query/manifest | 复用 026-028 filters、limit 和 manifest digest 语义，不改变 `/v1/audit/runtime` |

## 项目结构

### 文档结构

```text
specs/029-runtime-audit-export-bundle/
├── spec.md
├── plan.md
├── tasks.md
├── task-execution-log.md
└── development-summary.md
```

### 源码结构

```text
src/agentops/api/auth.py
src/agentops/api/app.py
src/agentops/api/server.py
tests/contract/test_ao29_ct_runtime_audit_export_bundle.py
```

## 阶段计划

### Phase 0：正式真值冻结

**目标**：冻结 route、scope、manifest gate、bundle schema、安全边界和非目标。
**产物**：`spec.md` / `plan.md` / `tasks.md` / `task-execution-log.md`
**验证方式**：文档对账 + truth sync
**回退方式**：删除 029 docs 与 manifest mapping

### Phase 1：合同测试红灯

**目标**：用 contract tests 固定成功 bundle、scope denied、manifest mismatch、anti-leak 和 route manifest。
**产物**：`tests/contract/test_ao29_ct_runtime_audit_export_bundle.py`
**验证方式**：`uv run pytest tests/contract/test_ao29_ct_runtime_audit_export_bundle.py -q` 红灯
**回退方式**：移除 AO29 test file

### Phase 2：实现 manifest-gated bundle

**目标**：新增 scope、route、payload validation、sanitized metadata records、bundle digest 和 durable audit。
**产物**：`auth.py`、`server.py`、`app.py`
**验证方式**：AO29 合同测试绿灯
**回退方式**：移除 route/scope/helper

### Phase 3：回归与收口

**目标**：确保 AO23-AO29 生产 runtime/audit 链路无回退。
**产物**：`development-summary.md`、更新执行日志、truth snapshot
**验证方式**：AO23-AO29 regression、ruff、AI-SDLC constraints、close-check
**回退方式**：回退本阶段变更

## 工作流计划

### 工作流 A：runtime audit export bundle

**范围**：新增 `POST /v1/audit/runtime/export-bundle`。
**影响范围**：auth scope、standard-library HTTP server、route manifest、contract tests。
**验证方式**：先红灯 AO29，再绿灯 AO29 + AO23-AO29 regression。
**回退方式**：删除 route 和专用 scope，不影响 026-028 query/manifest。

## 关键路径验证策略

| 关键路径 | 主验证方式 | 次验证方式 |
|----------|------------|------------|
| manifest gate 正确拒绝 stale digest | AO29 mismatch contract | durable rejected audit assert |
| bundle metadata-only 且无泄漏 | AO29 anti-leak contract | ruff + regression |
| scope 独立于 runtime.audit.read | AO29 viewer/read-only denied contract | auth ROLE_SCOPES assert |
| 既有 audit query/manifest 不回退 | AO23-AO29 regression | route manifest assert |

## 开放问题

| 问题 | 状态 | 阻塞阶段 |
|------|------|----------|
| 是否生成真实文件/签名 URL | 决策：否，后续对象存储阶段处理 | 不阻塞 |
| 是否接 SIEM/通知 | 决策：否，后续集成阶段处理 | 不阻塞 |
| 是否新增 tenant filters | 决策：否，后续 ABAC 阶段处理 | 不阻塞 |

## 实施顺序建议

1. 冻结 029 formal docs。
2. 新增 AO29 contract tests 并确认红灯。
3. 实现 `runtime.audit.export` scope 和 export bundle route。
4. 运行 AO29、AO23-AO29 regression、ruff、truth sync、constraints、close-check。
