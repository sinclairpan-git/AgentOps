---
related_doc:
  - "/Users/sinclairpan/project/AI-Native底座开发文档/AgentOps_项目_PRD.md"
---
# 实施计划：Production Runtime Boundary

**编号**：`023-production-runtime-boundary` | **日期**：2026-05-08 | **规格**：specs/023-production-runtime-boundary/spec.md

## 概述

以最小可验证切片补上生产运行边界：HTTP server 在显式生产模式下消费上游 IAM/RBAC header，按 route scope 执行只读/写入权限检查，并给出可审计拒绝响应。同步补齐 frontend generation artifacts，恢复 program status 的治理可运行性。

## 技术背景

**语言/版本**：Python 3.11+，标准库 HTTP server。
**主要依赖**：无新增运行时依赖。
**存储**：沿用 `InMemoryRepository`，本阶段不引入生产数据库。
**测试**：Python contract tests、全量 pytest、ruff、AI-SDLC program/status gates。
**目标平台**：macOS / Linux / Windows，保持 GitHub Compatibility Gate 口径。
**约束**：不自建 IAM；只消费上游可信 header；local/dev 默认兼容既有测试。

## 宪章检查

| 宪章门禁 | 计划响应 |
| --- | --- |
| Persist decisions to repository | 023 spec/plan/tasks/log 与 contract tests 一起提交。 |
| Prefer contract-level verification | 新增 AO23 契约测试覆盖身份缺失、scope 不足、授权通过和治理 recipe。 |
| Keep docs and code traceable | `create_app()` route manifest、spec 验收契约和测试文件互相引用。 |

## 项目结构

```text
src/agentops/api/auth.py
src/agentops/api/server.py
src/agentops/api/app.py
tests/contract/test_ao23_ct_production_runtime_boundary.py
governance/frontend/generation/recipe.yaml
governance/frontend/generation/exceptions.yaml
specs/023-production-runtime-boundary/
```

## 阶段计划

### Phase 1：契约冻结

冻结生产运行边界、非目标和 AO23 验收口径。

验证方式：`uv run ai-sdlc verify constraints`、文档对账。

### Phase 2：生产模式鉴权实现

新增上游身份解析和 route scope enforcement；`create_http_handler(..., require_auth=True)` 启用生产边界，默认 local/dev 不启用。

验证方式：AO23 契约测试、AO4/AO18/AO22 回归。

### Phase 3：治理 artifact 修复与收口

补 `recipe.yaml`、`exceptions.yaml` 并将它们登记到 generation manifest；确认 `ai-sdlc program status` 可执行。

验证方式：`uv run ai-sdlc program status`、`uv run ai-sdlc program validate`、`uv run ai-sdlc run --dry-run`。

## 风险与回退

| 风险 | 缓解 |
| --- | --- |
| 生产鉴权破坏本地联调 | 默认 `require_auth=False`，契约明确生产模式才启用。 |
| 上游 header 被误认为强身份系统 | spec/错误文案声明 AgentOps 只消费上游 IAM/RBAC 证明。 |
| 拒绝响应泄露敏感数据 | 错误体只包含 code/message/retryable/request_id/audit_id/denied_scope。 |
