---
related_doc:
  - "specs/031-agentops-runtime-governance-foundation/agentops-p0-p2-backlog.md"
  - "specs/032-evidence-health-summary-loop/spec.md"
  - "specs/034-runtime-outbox-sdlc-trace-bridge/spec.md"
  - "specs/037-p1-evidence-eval-cost-operations/spec.md"
  - "specs/038-p2-replay-simulation-optimizer/spec.md"
---
# 实施计划：P2 Ecosystem Governance

**编号**：`039-p2-ecosystem-governance` | **日期**：2026-05-10 | **规格**：specs/039-p2-ecosystem-governance/spec.md

## 概述

AO39 承接 P2-B，把 AgentOps 从单体运行治理扩展到生态边界：MCP/A2A gateway governance、多 exporter dry-run 生态、multi-agent handoff evaluation 和 complex risk profile。第一批只做 summary-only backend contracts/API，不执行外部连接、export、handoff 或自动处置。

## 技术背景

**语言/版本**：Python 3.11+  
**主要依赖**：标准库 + 现有 `agentops` core/api/storage  
**存储**：复用 `InMemoryRepository` 已有 runtime facts / DLQ / summaries；不新增外部 DB  
**测试**：pytest contract tests + focused regression  
**约束**：no raw evidence/config、no Runtime execution、no exporter dispatch、no external gateway execution、backward compatible with P0/P1/P2-A contracts

## 宪章检查

| 宪章门禁 | 计划响应 |
|----------|----------|
| AgentOps 不执行 Runtime | 所有 P2-B 能力只生成 projection，不调度 handoff 或 gateway |
| Evidence/脱敏基线 | 输出只保留 hash/ref/summary，不返回 raw config/payload |
| Contract-first | 先登记 `runtime_contracts.py`，再实现 API/core 投影 |
| Exporter 安全 | 多 exporter 生态固定 dry-run/no-write |
| AI-SDLC 单批提交 | 本批代码、测试、文档与执行日志合并为一次提交 |

## 项目结构

```text
src/agentops/core/operations.py                         # P2-B projection builders
src/agentops/api/operations.py                          # API wrappers
src/agentops/core/runtime_contracts.py                  # contract registry
tests/contract/test_ao39_ct_p2_ecosystem_governance.py
specs/039-p2-ecosystem-governance/
```

## 阶段计划

### Phase 0：Formal baseline

**目标**：冻结 039 spec/plan/tasks/log，并同步 program truth。  
**验证方式**：`ai-sdlc adapter status`、`ai-sdlc run --dry-run`、`python -m ai_sdlc program truth sync --execute --yes`。

### Phase 1：Contract registry + red tests

**目标**：新增 AO39 contract tests，证明 P2-B contract/projection 缺口。  
**验证方式**：AO39 聚焦 pytest。

### Phase 2：P2-B projection implementation

**目标**：实现 MCP/A2A governance、exporter ecosystem、handoff evaluation、complex risk profile builders。  
**验证方式**：AO39 聚焦测试通过，AO32/AO34/AO37/AO38 回归通过。

### Phase 3：Close-out

**目标**：同步任务、执行日志、development summary 和 AI-SDLC close-check。  
**验证方式**：ruff、pytest、AI-SDLC verify/close-check。

## 关键路径验证策略

| 关键路径 | 主验证方式 | 次验证方式 |
|----------|------------|------------|
| Contract registry | AO39-CT-001 | runtime contract validation |
| MCP/A2A gateway boundary | AO39-CT-002 | raw leak scan |
| Exporter no-write ecosystem | AO39-CT-003 | AO37 exporter regression |
| Multi-agent handoff summary | AO39-CT-004 | AO32 runtime trace regression |
| Complex risk profile | AO39-CT-005 | AO34 DLQ + AO37 health/SLO regression |

## 开放问题

| 问题 | 状态 | 阻塞阶段 |
|------|------|----------|
| 真实 MCP/A2A Gateway 是否进入 039 | 明确不进入，Runtime-owned gateway work item | 不阻塞 |
| 多 exporter 是否真实发送 | 本批只做 dry-run projection | 不阻塞 |
| UI 是否进入 039 | 本批不做 Console 页面 | 不阻塞 |
