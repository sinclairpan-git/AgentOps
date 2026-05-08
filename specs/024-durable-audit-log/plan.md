# 实施计划：Durable Audit Log

**编号**：`024-durable-audit-log` | **日期**：2026-05-08 | **规格**：specs/024-durable-audit-log/spec.md

## 概述

本阶段承接 023 生产运行边界，把“拒绝响应含审计线索”推进为“生产边界会留下重启后仍可读取的最小审计事实”。实现选择标准库 JSONL append-only adapter，避免在本阶段引入数据库和迁移复杂度，同时为后续生产数据库/持久化审计表提供稳定 schema。

## 技术背景

**语言/版本**：Python 3.11+，沿用项目标准库优先策略。
**主要依赖**：无新增运行时依赖。
**存储**：append-only JSONL file，后续可替换为数据库适配器。
**测试**：pytest contract tests + ruff + AI-SDLC constraints。
**目标平台**：本地与 CI；文件路径由调用方显式注入。
**约束**：不得改变 023 authorization response contract；不得写入敏感 request body 或 credential material。

## 宪章检查

| 宪章门禁 | 计划响应 |
|----------|----------|
| 入口真值 | 已执行 `ai-sdlc adapter status` 与 `ai-sdlc run --dry-run`，024 通过 `workitem init` 纳入 manifest。 |
| 可验证合同 | 新增 AO24 contract tests 覆盖 durable readback、生产 auth denial、成功 ingest audit 和防敏感字段。 |
| 最小事实所有权 | 审计日志只记录运行边界事实，不复制 raw event payload 或 request body。 |
| 兼容性 | `audit_log` 为显式可选注入；未配置时保持 023 行为。 |

## 项目结构

### 文档结构

```text
specs/024-durable-audit-log/
├── spec.md
├── plan.md
├── tasks.md
└── task-execution-log.md
```

### 源码结构

```text
src/agentops/storage/audit.py
src/agentops/api/server.py
src/agentops/api/app.py
tests/contract/test_ao24_ct_durable_audit_log.py
```

## 阶段计划

### Phase 0：研究与决策冻结

**目标**：冻结 024 生产审计持久化的最小范围、非目标与合同。
**产物**：spec.md / plan.md / tasks.md / task-execution-log.md
**验证方式**：文档对账 + program truth sync。
**回退方式**：回退 024 文档与 manifest 条目。

### Phase 1：durable audit adapter

**目标**：新增稳定 `AuditRecord` schema 与 JSONL adapter。
**产物**：`src/agentops/storage/audit.py`
**验证方式**：contract test 读取重建后的 JSONL 记录。
**回退方式**：移除 adapter 文件和调用点。

### Phase 2：HTTP production boundary integration

**目标**：生产模式鉴权拒绝与事件写入结果写入 durable audit log。
**产物**：`create_http_handler(..., audit_log=...)`、manifest 声明、AO24 contract tests。
**验证方式**：AO23 + AO24 contract tests。
**回退方式**：移除 `audit_log` 参数和调用点，保留 023 行为。

## 工作流计划

### 工作流 A：授权拒绝审计

**范围**：`_send_auth_error` 在生产模式 scope 检查失败后追加 denied audit record。
**影响范围**：HTTP handler 内部；API 响应 schema 不变。
**验证方式**：缺失 identity 与 scope denied 合同测试。
**回退方式**：删除 audit append 调用。

### 工作流 B：事件写入结果审计

**范围**：`POST /v1/events` 与 `/v1/events/batch` 在 ingest 结果返回前追加 accepted/rejected audit record。
**影响范围**：事件写入路由；不改变 ingestion outcome。
**验证方式**：授权 ingestor 写入后读取 JSONL。
**回退方式**：删除 ingest audit append 调用。

## 关键路径验证策略

| 关键路径 | 主验证方式 | 次验证方式 |
|----------|------------|------------|
| Authorization denial durable audit | AO24 contract test | AO23 production boundary regression |
| Event ingest accepted audit | AO24 contract test | repository raw_event_count |
| No sensitive data in audit file | JSONL raw text assertion | response anti-leak regression |

## 开放问题

| 问题 | 状态 | 阻塞阶段 |
|------|------|----------|
| 是否直接上数据库 | 决策：本阶段不引入；先冻结 JSONL schema | 不阻塞 |
| 是否覆盖 credential revoke/reissue | 决策：后续阶段；本阶段覆盖最高频 event ingest 和 auth denial | 不阻塞 |

## 实施顺序建议

1. 冻结 024 formal docs 与 tasks。
2. 新增 `AuditRecord` / `JsonlAuditLog`。
3. 将 audit log 以可选参数接入 HTTP handler。
4. 补 AO24 contract tests 并跑 AO23/AO24 回归。
5. 更新执行日志、manifest、提交并进入 PR 收口。
