# 实施计划：Runtime Audit Pagination

**编号**：`027-runtime-audit-pagination` | **日期**：2026-05-08 | **规格**：specs/027-runtime-audit-pagination/spec.md

## 概述

027 承接 026 runtime audit query，为 `GET /v1/audit/runtime` 增加 opaque cursor pagination。目标是在不引入数据库和外部服务的前提下，让生产管理员可以稳定逐页读取 durable audit records，同时保持 metadata-only、bounded、RBAC 和 audit-on-read 语义。

## 技术背景

**语言/版本**：Python 3.11+。
**主要依赖**：无新增运行时依赖，使用标准库 `base64/json`。
**存储**：复用 `JsonlAuditLog.records()`。
**测试**：pytest contract tests + AO23-AO27 回归 + ruff + AI-SDLC constraints。
**目标平台**：本地与 CI。
**约束**：cursor opaque、绑定 filters、bounded、metadata-only；不泄露 audit 文件路径或敏感 request/credential material。

## 宪章检查

| 宪章门禁 | 计划响应 |
|----------|----------|
| AI-SDLC 入口 | 已执行 adapter status、dry-run、workitem init，并将在实现后 truth sync。 |
| 合同优先 | 新增 AO27 contract tests，联跑 AO23-AO27 防回退。 |
| 安全边界 | cursor 不可跨 filters 复用，非法 cursor 400 且 durable audit rejected。 |
| 兼容性 | 缺少 cursor 时保持 026 首屏查询语义与 response fields。 |

## 项目结构

### 文档结构

```text
specs/027-runtime-audit-pagination/
├── spec.md
├── plan.md
├── tasks.md
└── task-execution-log.md
```

### 源码结构

```text
src/agentops/api/server.py
tests/contract/test_ao27_ct_runtime_audit_pagination.py
```

## 阶段计划

### Phase 0：研究与决策冻结

**目标**：冻结 cursor contract、filter binding、错误码和非目标。
**产物**：spec.md / plan.md / tasks.md / task-execution-log.md
**验证方式**：文档对账 + truth sync。
**回退方式**：回退 027 docs 与 manifest mapping。

### Phase 1：Cursor parser and response metadata

**目标**：在 runtime audit query 中解析/生成 cursor，返回 `page_info`。
**产物**：`server.py`
**验证方式**：AO27 pagination tests。
**回退方式**：删除 cursor helpers 与 `page_info` fields。

### Phase 2：Cursor safety and regression closure

**目标**：覆盖 malformed cursor、filter mismatch、anti-leak 和 AO23-AO27 回归。
**产物**：AO27 tests、execution log、development summary、truth sync。
**验证方式**：pytest/ruff/constraints。
**回退方式**：回退 AO27 test/docs/code commit。

## 工作流计划

### 工作流 A：第一页与后续页

**范围**：operator/admin 通过 filters+limit 获取第一页，再用 `next_cursor` 获取后续页。
**影响范围**：只影响 `/v1/audit/runtime` response construction。
**验证方式**：AO27 CT first/second/final page assertions。
**回退方式**：删除 cursor 分页逻辑。

### 工作流 B：非法 cursor 拒绝

**范围**：malformed cursor 或 cursor 与 filters 不匹配。
**影响范围**：新增 `AUDIT_CURSOR_INVALID` 错误路径，复用 026 audit-on-reject。
**验证方式**：AO27 CT invalid cursor / mismatch assertions。
**回退方式**：删除 cursor validation。

## 关键路径验证策略

| 关键路径 | 主验证方式 | 次验证方式 |
|----------|------------|------------|
| cursor continuation | AO27 CT | direct record id order assertions |
| filter binding | AO27 CT | invalid cursor response assertions |
| no sensitive material/path | AO27 CT | AO26 anti-leak regression |
| audit-on-read preserved | AO27 CT | AO25/AO26 audit regression |

## 开放问题

| 问题 | 状态 | 阻塞阶段 |
|------|------|----------|
| 是否使用数据库 cursor | 决策：不新增数据库，先 opaque offset cursor | 不阻塞 |
| cursor 是否绑定 limit | 决策：不绑定 limit，允许下一页调整页大小；绑定 filters | 不阻塞 |
| 是否接 SIEM/通知 | 决策：不新增，本阶段只扩展查询 API | 不阻塞 |

## 实施顺序建议

1. 冻结 027 docs/tasks。
2. 新增 AO27 contract tests。
3. 实现 cursor encode/decode、filter binding 和 `page_info`。
4. 联跑 AO23-AO27、ruff、constraints。
5. 更新执行日志、summary、truth sync、提交 PR。
