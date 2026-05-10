---
related_doc:
  - "specs/031-agentops-runtime-governance-foundation/agentops-p0-p2-backlog.md"
  - "specs/032-evidence-health-summary-loop/spec.md"
  - "specs/036-p1-approval-policy-grant-operations/spec.md"
  - "specs/037-p1-evidence-eval-cost-operations/spec.md"
---
# 实施计划：P2 Replay Simulation Optimizer

**编号**：`038-p2-replay-simulation-optimizer` | **日期**：2026-05-10 | **规格**：specs/038-p2-replay-simulation-optimizer/spec.md

## 概述

AO38 承接 P2-A，把 P1 的 evidence/eval/cost/approval/policy 操作面推进到优化前置能力：safe replay plan、experiment plan、optimizer recommendation 和 policy simulation projection。第一批只做 summary-only 后端 contracts 与 API，不执行 Runtime、不发布 policy、不做自动优化。

## 技术背景

**语言/版本**：Python 3.11+  
**主要依赖**：标准库 + 现有 `agentops` core/api/storage  
**存储**：复用 `InMemoryRepository`，新增 replay/experiment plan records；optimizer/policy simulation 直接返回投影  
**测试**：pytest contract tests + focused regression  
**约束**：no raw evidence/config、no Runtime execution、no policy publish、backward compatible with P0/P1 contracts

## 宪章检查

| 宪章门禁 | 计划响应 |
|----------|----------|
| AgentOps 不执行 Runtime | SafeReplay 只生成计划，summary 标记 no-execution |
| Evidence/脱敏基线 | 所有 P2-A projection 只返回 hash/ref/summary |
| Contract-first | 先登记 `runtime_contracts.py`，再实现 API/core 投影 |
| Policy 安全 | policy simulation 不发布、不改变 active policy，保留 deny priority |
| AI-SDLC 单批提交 | 本批代码、测试、文档与执行日志合并为一次提交 |

## 项目结构

```text
src/agentops/core/operations.py                         # P2-A projection builders
src/agentops/api/operations.py                          # API wrappers
src/agentops/core/runtime_contracts.py                  # contract registry
src/agentops/storage/repository.py                      # replay/experiment records
tests/contract/test_ao38_ct_p2_replay_simulation_optimizer.py
specs/038-p2-replay-simulation-optimizer/
```

## 阶段计划

### Phase 0：Formal baseline

**目标**：冻结 038 spec/plan/tasks/log，并同步 program truth。  
**验证方式**：`ai-sdlc adapter status`、`ai-sdlc run --dry-run`、`python -m ai_sdlc program truth sync --execute --yes`。

### Phase 1：Contract registry + red tests

**目标**：新增 AO38 contract tests，证明 P2-A contract/projection 缺口。  
**验证方式**：AO38 聚焦 pytest。

### Phase 2：P2-A projection implementation

**目标**：实现 safe replay、experiment、optimizer、policy simulation projection builders。  
**验证方式**：AO38 聚焦测试通过，AO32/AO34/AO35/AO37 回归通过。

### Phase 3：Close-out

**目标**：同步任务、执行日志、development summary 和 AI-SDLC close-check。  
**验证方式**：ruff、pytest、AI-SDLC verify/close-check。

## 关键路径验证策略

| 关键路径 | 主验证方式 | 次验证方式 |
|----------|------------|------------|
| Contract registry | AO38-CT-001 | runtime contract validation |
| Safe replay no-execution | AO38-CT-002 | AO32 evidence summary regression |
| Experiment ref-only variants | AO38-CT-003 | raw leak scan |
| Optimizer summary-only | AO38-CT-004 | AO37 EvalCase regression |
| Policy simulation dry-run | AO38-CT-005 | AO36 policy operation regression |

## 开放问题

| 问题 | 状态 | 阻塞阶段 |
|------|------|----------|
| 真实 replay executor 是否进入 038 | 明确不进入，后续 Runtime-owned work item | 不阻塞 |
| UI 是否进入 038 | 本批不做 Console 页面 | 不阻塞 |
| 自动优化是否允许 | 本批只输出人工可审建议 | 不阻塞 |
