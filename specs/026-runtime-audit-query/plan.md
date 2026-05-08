# 实施计划：Runtime Audit Query

**编号**：`026-runtime-audit-query` | **日期**：2026-05-08 | **规格**：specs/026-runtime-audit-query/spec.md

## 概述

026 将 024/025 已经写入的 durable runtime audit records 暴露为生产受保护的只读查询 API。目标是让管理员可以按 request/audit/action/outcome 快速定位记录，同时保持 metadata-only、bounded、无敏感材料泄露。

## 技术背景

**语言/版本**：Python 3.11+。
**主要依赖**：无新增运行时依赖。
**存储**：复用 `JsonlAuditLog.records()`。
**测试**：pytest contract tests + AO23/AO24/AO25/AO26 回归 + ruff + AI-SDLC constraints。
**目标平台**：本地与 CI。
**约束**：只读、bounded、metadata-only；不泄露 audit 文件路径或敏感 request/credential material。

## 宪章检查

| 宪章门禁 | 计划响应 |
|----------|----------|
| AI-SDLC 入口 | 已执行 adapter status、dry-run、workitem init 与 truth sync。 |
| 合同优先 | 新增 AO26 contract tests，联跑 AO23/AO24/AO25 防回退。 |
| 安全边界 | 新 scope `runtime.audit.read`，viewer 默认不可读；响应 metadata-only。 |
| 兼容性 | 无 audit log 注入时返回可解释错误，不改变现有 route。 |

## 项目结构

### 文档结构

```text
specs/026-runtime-audit-query/
├── spec.md
├── plan.md
├── tasks.md
└── task-execution-log.md
```

### 源码结构

```text
src/agentops/api/auth.py
src/agentops/api/server.py
src/agentops/api/app.py
tests/contract/test_ao26_ct_runtime_audit_query.py
```

## 阶段计划

### Phase 0：研究与决策冻结

**目标**：冻结 runtime audit query 的安全范围、filters、limit 和非目标。
**产物**：spec.md / plan.md / tasks.md / task-execution-log.md
**验证方式**：文档对账 + truth sync。
**回退方式**：回退 026 docs 与 manifest mapping。

### Phase 1：RBAC scope and route manifest

**目标**：新增 `runtime.audit.read` scope，manifest 声明 route。
**产物**：`auth.py`、`app.py`
**验证方式**：viewer denied / operator allowed contract。
**回退方式**：移除 scope 与 manifest route。

### Phase 2：Runtime audit query route

**目标**：实现 `GET /v1/audit/runtime` filters、limit、metadata-only response。
**产物**：`server.py`、AO26 tests。
**验证方式**：filter、limit、unavailable、anti-leak tests。
**回退方式**：移除 route block 和 tests。

## 工作流计划

### 工作流 A：授权查询

**范围**：operator/admin 查询 runtime audit；viewer 无权访问。
**影响范围**：新增 route，不影响 existing route。
**验证方式**：AO26 RBAC tests。
**回退方式**：删除 route/scope。

### 工作流 B：过滤和限流

**范围**：支持 audit_id、request_id、action、outcome、limit；默认 50、最大 200。
**影响范围**：只读 response construction。
**验证方式**：AO26 filter/limit tests。
**回退方式**：删除 query helper。

## 关键路径验证策略

| 关键路径 | 主验证方式 | 次验证方式 |
|----------|------------|------------|
| runtime.audit.read RBAC | AO26 CT | AO23 auth regression |
| filter and bounded limit | AO26 CT | direct JSON assertions |
| no sensitive material/path | AO26 CT | AO24/AO25 anti-leak regression |
| malformed JSONL resilience | AO26 CT | JsonlAuditLog records regression |

## 开放问题

| 问题 | 状态 | 阻塞阶段 |
|------|------|----------|
| 是否新增 pagination cursor | 决策：不新增，先 bounded list | 不阻塞 |
| 是否接 SIEM/通知 | 决策：不新增，只读 API 后续可作为上游 | 不阻塞 |

## 实施顺序建议

1. 冻结 026 docs/tasks。
2. 新增 `runtime.audit.read` scope 和 manifest route。
3. 实现 runtime audit query route 与 helpers。
4. 新增 AO26 contract tests 并联跑 AO23-AO26。
5. 更新执行日志、summary、truth sync、提交 PR。
