---
related_doc:
  - "/Users/sinclairpan/project/AI-Native底座开发文档/AgentOps_项目_PRD.md"
  - "/Users/sinclairpan/project/AI-Native底座开发文档/Agent_Runtime_项目_PRD.md"
  - "/Users/sinclairpan/project/AI-Native底座开发文档/Agent_Store_AgentOps_AiSDLC_应用底座顶层规划_PRD.md"
---
# 实施计划：AgentOps Runtime Governance Foundation

**编号**：`031-agentops-runtime-governance-foundation` | **日期**：2026-05-09 | **规格**：specs/031-agentops-runtime-governance-foundation/spec.md

## 概述

本计划以 contract-first 方式承接 AO-P0-01 到 AO-P0-04。先冻结 Runtime -> AgentOps 的 P0 契约和状态语义，再实现 Ingestion、Run Detail、Trace Timeline 的最小可验证切片。实现阶段必须保持 AgentOps “管治理，不管执行”的边界：AgentOps 接收和解释 Runtime 事实，不加载 Agent 包、不执行 Tool/Model、不生成 RuntimeRun。

## 技术背景

**语言/版本**：Python 3.11+。  
**前端**：Vue 2.x，`apps/agentops-console`，沿用现有 provider whitelist 和 DataTable/StatusBadge/AppShell 组件。  
**主要依赖**：无新增运行时依赖；优先使用现有 `src/agentops/core`、`src/agentops/api`、`src/agentops/storage`。  
**存储**：P0 沿用 `InMemoryRepository` / repository abstraction；后续生产持久化另拆。  
**测试**：Python contract tests、unit tests、console API/前端契约测试、AI-SDLC gates。  
**目标平台**：macOS / Linux / Windows，保持 GitHub Compatibility Gate 口径。  
**约束**：严格遵守 `.ai-sdlc/memory/constitution.md`：决策入库、契约优先验证、文档与代码可追踪。

## 宪章检查

| 宪章门禁 | 计划响应 |
|---|---|
| Persist decisions to the repository | 031 spec/research/data-model/plan/tasks/contract-tests 全部落在 `specs/031-*`。 |
| Prefer contract-level verification before closure | AO31-CT-001 到 AO31-CT-008 先冻结，执行阶段转为 `tests/contract/test_ao31_*`。 |
| Keep docs and code traceable | 每个任务引用 FR/CT；实现文件、测试文件与 contract id 对齐。 |

## 项目结构

### 文档结构

```text
specs/031-agentops-runtime-governance-foundation/
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
src/agentops/core/runtime_contracts.py
src/agentops/core/runtime_ingestion.py
src/agentops/models/runtime.py
src/agentops/api/runtime.py
src/agentops/api/console_snapshot.py
src/agentops/api/view_models.py
src/agentops/storage/repository.py
apps/agentops-console/src/data/mockAgentOpsData.js
apps/agentops-console/src/data/agentOpsApiClient.js
apps/agentops-console/src/views/RunsView.js
apps/agentops-console/src/views/OverviewView.js
tests/contract/test_ao31_ct_runtime_governance_foundation.py
tests/unit/test_runtime_contracts.py
tests/unit/test_runtime_ingestion.py
```

## 阶段计划

### Phase 0：AI-SDLC refine/design/decompose 冻结

**目标**：完成需求、研究、数据模型、计划、任务和 contract test 草案。  
**产物**：`spec.md`、`research.md`、`data-model.md`、`plan.md`、`tasks.md`、`contracts/contract-tests.md`。  
**验证方式**：`ai-sdlc gate refine`、`ai-sdlc gate design`、`ai-sdlc gate decompose`、`ai-sdlc run --dry-run`。  
**回退方式**：若 gate 失败，只调整 031 文档，不改动既有 001-030 工作项。

### Phase 1：Registry 与模型基础

**目标**：实现 Contract / Schema / State / Error Registry 最小结构和 runtime model。  
**产物**：runtime contract/model 模块、AO31-CT-001/008、unit tests。  
**验证方式**：`uv run pytest tests/unit/test_runtime_contracts.py tests/contract/test_ao31_ct_runtime_governance_foundation.py -q`。  
**回退方式**：保持 registry 只读常量/数据类，失败时不影响既有 ingestion。

### Phase 2：Runtime Ingestion API v1

**目标**：接收 RuntimeRun + TraceSpan 批次，完成 schema、签名状态、幂等、sequence、parent integrity 校验。  
**产物**：runtime ingestion core、API route、repository 方法、AO31-CT-002/003/004/005。  
**验证方式**：contract tests + 既有 AO-CT-001/AO23 回归。  
**回退方式**：保持旧 `/v1/events` 兼容；新 runtime ingestion route 独立开关。

### Phase 3：Run Detail / Trace Timeline 投影

**目标**：提供 API / view model 和 console mock 数据，展示 P0 运行详情与 Trace Timeline。  
**产物**：Run Detail projection、Trace Timeline projection、console 数据契约、AO31-CT-006/007。  
**验证方式**：console API contract、unit tests、前端构建/测试。  
**回退方式**：Console 在缺新接口时展示 `trace_pending` 安全空态。

### Phase 4：AI-SDLC verify/close

**目标**：完成全量验证、执行日志、development summary 和工作项收口。  
**验证方式**：

```text
uv run pytest tests -q
uv run ruff check src tests
uv run ruff format --check src tests
uv run ai-sdlc verify constraints
uv run ai-sdlc run --dry-run
```

## 工作流计划

### 工作流 A：Runtime 批量上报

**范围**：Runtime 生产批次，AgentOps 校验并返回 IngestionReceipt。  
**影响范围**：`src/agentops/api`、`src/agentops/core`、`src/agentops/storage`。  
**验证方式**：AO31-CT-002/003/004/005。  
**回退方式**：拒绝批次进入可解释 rejected/dlq，不产生半结构事实。

### 工作流 B：管理员查看运行详情

**范围**：查询 run detail，展示状态、policy、approval、guardrail、artifact、outbox。  
**影响范围**：API view model、console snapshot、RunsView。  
**验证方式**：AO31-CT-006 + console API contract。  
**回退方式**：权限不足或 trace 缺失时返回脱敏摘要/trace_pending。

### 工作流 C：管理员查看 Trace Timeline

**范围**：查询 span tree，展示链路、耗时、错误码、input/output ref。  
**影响范围**：runtime projection、console timeline UI。  
**验证方式**：AO31-CT-007。  
**回退方式**：parent 缺失或乱序时 degraded 展示，不伪装成功。

## 关键路径验证策略

| 关键路径 | 主验证方式 | 次验证方式 |
|---|---|---|
| Contract Registry 完整性 | AO31-CT-001/008 | `ai-sdlc verify constraints` |
| Runtime 批量上报 | AO31-CT-002/003/004/005 | 既有 AO-CT-001 回归 |
| Run Detail 查询 | AO31-CT-006 | Console API snapshot 回归 |
| Trace Timeline 查询 | AO31-CT-007 | 前端逐页 smoke |
| 不破坏既有闭环 | `uv run pytest tests -q` | `ai-sdlc run --dry-run` |

## 开放问题

| 问题 | 状态 | 阻塞阶段 |
|---|---|---|
| Runtime Ingestion route 命名使用 `/v1/runtime/events` 还是并入 `/v1/events` | 待执行阶段技术确认 | Phase 2 |
| Console Timeline 是否本期新建组件还是先扩展 RunsView | 待前端实现时确认 | Phase 3 |
| 签名状态是否复用现有 credential/signature 模块或新增 Runtime 专用 adapter | 待代码阅读后确认 | Phase 2 |

## 实施顺序建议

1. 先完成 registry/model 与 AO31-CT-001/008，冻结状态和错误码。
2. 再实现 ingestion batch，并保证幂等、sequence、parent integrity。
3. 然后实现 Run Detail / Trace Timeline 投影。
4. 最后接 Console 数据契约与验证，不提前进入 HealthSummary/Store 回写。
