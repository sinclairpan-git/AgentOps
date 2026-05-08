# 实施计划：Production Audit Coverage

**编号**：`025-production-audit-coverage` | **日期**：2026-05-08 | **规格**：specs/025-production-audit-coverage/spec.md

## 概述

024 已提供 durable audit log，并覆盖 auth denial 与 event ingest。025 将同一审计边界扩展到剩余生产受保护 HTTP route 的成功/业务失败分支，让敏感读和 credential 生命周期写操作都具备重启后可读取的最小审计证据。

## 技术背景

**语言/版本**：Python 3.11+。
**主要依赖**：无新增运行时依赖。
**存储**：复用 `JsonlAuditLog`。
**测试**：pytest contract tests + AO23/AO24 回归 + ruff + AI-SDLC constraints。
**目标平台**：本地与 CI。
**约束**：不改变 023 authorization contract，不扩大 024 audit schema，不写敏感 payload/credential material。

## 宪章检查

| 宪章门禁 | 计划响应 |
|----------|----------|
| AI-SDLC 入口 | 已执行 `ai-sdlc adapter status`、`ai-sdlc run --dry-run`、`workitem init` 与 truth sync。 |
| 合同优先 | 新增 AO25 contract tests，联跑 AO23/AO24 防回退。 |
| 最小事实 | 仅写 route outcome 元数据，不复制 request/response 敏感内容。 |
| 兼容性 | `audit_log` 仍为可选注入，未配置时行为不变。 |

## 项目结构

### 文档结构

```text
specs/025-production-audit-coverage/
├── spec.md
├── plan.md
├── tasks.md
└── task-execution-log.md
```

### 源码结构

```text
src/agentops/api/server.py
tests/contract/test_ao25_ct_production_audit_coverage.py
```

## 阶段计划

### Phase 0：研究与决策冻结

**目标**：冻结受保护 route audit coverage 的范围和非目标。
**产物**：spec.md / plan.md / tasks.md / task-execution-log.md
**验证方式**：文档对账 + truth sync。
**回退方式**：回退 025 docs 与 manifest mapping。

### Phase 1：Protected read route audit

**目标**：console snapshot、store summary、credential status 成功/业务失败均写审计。
**产物**：`server.py` route audit calls + AO25 read tests。
**验证方式**：AO25 contract tests。
**回退方式**：移除 read route audit calls。

### Phase 2：Credential write route audit

**目标**：credential revoke/reissue 成功/业务失败均写审计。
**产物**：`server.py` credential audit calls + AO25 write tests。
**验证方式**：AO25 contract tests + AO23/AO24 regression。
**回退方式**：移除 credential route audit calls。

## 工作流计划

### 工作流 A：读路由审计

**范围**：`GET /v1/console/snapshot`、`GET /v1/store-summary/{agent_id}`、`GET /v1/bootstrap/credentials/{bootstrap_id}`。
**影响范围**：仅 audit side effect；响应 body/status 不变。
**验证方式**：accepted/rejected audit records + no sensitive material assertion。
**回退方式**：删除 `_append_audit_record` 调用。

### 工作流 B：credential 写路由审计

**范围**：`POST /v1/bootstrap/credentials/{bootstrap_id}/revoke`、`/reissue`。
**影响范围**：仅 audit side effect；credential behavior 不变。
**验证方式**：success and not-found/rejected tests。
**回退方式**：删除 `_append_audit_record` 调用。

## 关键路径验证策略

| 关键路径 | 主验证方式 | 次验证方式 |
|----------|------------|------------|
| Console/store/credential read accepted audit | AO25 CT | AO23 auth regression |
| Store/credential business failure audit | AO25 CT | response status assertions |
| Credential revoke/reissue audit | AO25 CT | repository status assertions |
| Sensitive material exclusion | JSONL raw text assertion | AO24 anti-leak regression |

## 开放问题

| 问题 | 状态 | 阻塞阶段 |
|------|------|----------|
| 是否新增 audit query API | 决策：不新增，本阶段只补 coverage | 不阻塞 |
| 是否覆盖 anonymous health/CORS/not-found | 决策：不覆盖，仅生产受保护 route | 不阻塞 |

## 实施顺序建议

1. 冻结 025 docs/tasks。
2. 在 protected read route 成功/业务失败分支追加 audit calls。
3. 在 credential revoke/reissue 成功/业务失败分支追加 audit calls。
4. 新增 AO25 contract tests。
5. 联跑 AO23/AO24/AO25、ruff、constraints 后提交 PR。
