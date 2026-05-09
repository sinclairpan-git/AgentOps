---
related_doc:
  - "/Users/sinclairpan/project/AI-Native底座开发文档/AgentOps_项目_PRD.md"
  - "/Users/sinclairpan/project/AI-Native底座开发文档/Agent_Runtime_项目_PRD.md"
  - "/Users/sinclairpan/project/AI-Native底座开发文档/Agent_Store_项目_PRD.md"
  - "/Users/sinclairpan/project/AI-Native底座开发文档/Agent_Store_AgentOps_AiSDLC_应用底座顶层规划_PRD.md"
---
# 实施计划：AgentOps Evidence and Health Summary Loop

**编号**：`032-evidence-health-summary-loop` | **日期**：2026-05-09 | **规格**：specs/032-evidence-health-summary-loop/spec.md

## 概述

本计划以 AO31 已落地的 RuntimeRun / TraceSpan 事实为输入，完成 AO-P0-05、AO-P0-06、AO-P0-11、AO-P0-13。实现方式保持 AgentOps 的边界：只接收、解释、合成和回显治理摘要，不执行 Agent，不调度 Runtime，不让 Store 反推治理事实。

## 技术背景

**语言/版本**：Python 3.11+。  
**前端**：本期以 API / contract 为主，Console 如需展示只消费已有 summary 字段，不新增大页面。  
**主要依赖**：无新增运行时依赖；沿用 `src/agentops/core`、`src/agentops/api`、`src/agentops/storage`。  
**存储**：P0 沿用 `InMemoryRepository` 和 runtime facts；不新增外部数据库。  
**测试**：Python contract tests、AO22/AO31 回归、AI-SDLC gates。  
**目标平台**：macOS / Linux / Windows，保持 GitHub Compatibility Gate 口径。  
**约束**：遵守 `.ai-sdlc/memory/constitution.md`：决策入库、契约优先验证、文档与代码可追踪。

## 宪章检查

| 宪章门禁 | 计划响应 |
|---|---|
| Persist decisions to the repository | 032 spec/research/data-model/plan/tasks/contract-tests 全部落在 `specs/032-*`。 |
| Prefer contract-level verification before closure | AO32-CT-001 到 AO32-CT-006 先冻结，再实现 `tests/contract/test_ao32_*`。 |
| Keep docs and code traceable | 每个任务引用 FR/CT；实现文件、测试文件与需求包 AO-P0-05/06/11/13 对齐。 |

## 项目结构

### 文档结构

```text
specs/032-evidence-health-summary-loop/
├── spec.md
├── research.md
├── data-model.md
├── plan.md
├── tasks.md
├── task-execution-log.md
├── development-summary.md
└── contracts/
    └── contract-tests.md
```

### 预计源码结构

```text
src/agentops/core/runtime_summary.py
src/agentops/api/runtime.py
src/agentops/api/store_summary.py
src/agentops/api/app.py
src/agentops/api/server.py
src/agentops/storage/repository.py
tests/contract/test_ao32_ct_evidence_health_summary_loop.py
```

## 阶段计划

### Phase 0：AI-SDLC refine/design/decompose 冻结

**目标**：完成真实业务规格、研究、数据模型、计划、任务和 contract test 草案。  
**产物**：`spec.md`、`research.md`、`data-model.md`、`plan.md`、`tasks.md`、`contracts/contract-tests.md`。  
**验证方式**：`uv run ai-sdlc gate refine`、`uv run ai-sdlc gate design`、`uv run ai-sdlc gate decompose`、`uv run ai-sdlc verify constraints`。  
**回退方式**：仅调整 032 文档，不改动 001-031 工作项。

### Phase 1：EvidenceSummary 合成

**目标**：从 RuntimeRun / TraceSpan 事实生成 `evidence_summary.v1`。  
**产物**：`runtime_summary.py` evidence builder、AO32-CT-001/002。  
**验证方式**：`uv run pytest tests/contract/test_ao32_ct_evidence_health_summary_loop.py -q`。  
**回退方式**：builder 为纯投影逻辑，不写 Runtime facts。

### Phase 2：HealthSummary 聚合

**目标**：按 agent/version/window 生成 `health_summary.v1`。  
**产物**：health builder、repository runtime run list helper、AO32-CT-003。  
**验证方式**：contract tests 覆盖 success/failure/block/sample_size=0。  
**回退方式**：无样本返回 watching/expired，不影响 ingestion。

### Phase 3：Store Runtime Summary 回显

**目标**：在既有 Store summary contract 中接入 runtime evidence/health 摘要。  
**产物**：`get_agent_store_summary_for_run` runtime 优先路径、HTTP route manifest 字段、AO32-CT-004/005。  
**验证方式**：AO22/AO32 contract tests。  
**回退方式**：runtime facts 不存在时沿用 AO22 SDLC event summary。

### Phase 4：P0 端到端验收与收口

**目标**：串起 ingestion、run detail、trace timeline、evidence summary、store summary。  
**产物**：AO32-CT-006、execution log、development summary。  
**验证方式**：

```text
uv run pytest tests/contract/test_ao32_ct_evidence_health_summary_loop.py tests/contract/test_ao31_ct_runtime_governance_foundation.py tests/contract/test_ao22_ct_agent_store_summary_http_contract.py -q
uv run pytest tests -q
uv run ruff check src tests
uv run ruff format --check src tests
uv run ai-sdlc verify constraints
uv run ai-sdlc run --dry-run
```

## 工作流计划

### 工作流 A：运行证据摘要

**范围**：run detail + trace timeline -> EvidenceSummary。  
**影响范围**：`src/agentops/core/runtime_summary.py`、`src/agentops/api/runtime.py`。  
**验证方式**：AO32-CT-001/002。  
**回退方式**：缺字段只降级 summary，不改写原事实。

### 工作流 B：版本健康摘要

**范围**：agent/version 最近窗口 runtime runs -> HealthSummary。  
**影响范围**：`src/agentops/storage/repository.py`、`runtime_summary.py`。  
**验证方式**：AO32-CT-003。  
**回退方式**：无样本返回可解释 watching/expired。

### 工作流 C：Store 回显

**范围**：`/v1/store-summary/{agent_id}` 消费 EvidenceSummary / HealthSummary。  
**影响范围**：`src/agentops/api/store_summary.py`、`src/agentops/api/server.py`、`src/agentops/api/app.py`。  
**验证方式**：AO32-CT-004/005/006 + AO22 回归。  
**回退方式**：无 runtime facts 时回落 AO22 legacy summary。

## 关键路径验证策略

| 关键路径 | 主验证方式 | 次验证方式 |
|---|---|---|
| EvidenceSummary 完整/降级 | AO32-CT-001 | AO31 run/timeline 回归 |
| Raw access 边界 | AO32-CT-002 | AO12 Evidence Vault 回归 |
| HealthSummary 推荐动作 | AO32-CT-003 | 单元边界样本 |
| Store 回显兼容 | AO32-CT-004/005 | AO22 contract 回归 |
| P0 端到端 | AO32-CT-006 | `ai-sdlc verify constraints` |

## 开放问题

| 问题 | 状态 | 阻塞阶段 |
|---|---|---|
| P0 HealthSummary 窗口大小是否固定 | 已决：P0 使用最近 20 条同 agent/version runtime run | Phase 2 |
| Store summary 是否新增新 route | 已决：保留 AO22 `/v1/store-summary/{agent_id}`，runtime facts 存在时增强响应 | Phase 3 |
| 摘要过期测试是否需要可控时间注入 | 已决：builder 接受 `now`/`valid_until_override` 测试参数 | Phase 1/3 |

## 实施顺序建议

1. 冻结 AO32 文档和 contract tests。
2. 实现 runtime summary builder 与 repository 查询 helper。
3. 接入 Store summary runtime 优先路径。
4. 补 HTTP/manifest 与端到端 contract test。
5. 跑 AO22/AO31/AO32 回归和 AI-SDLC gates。
