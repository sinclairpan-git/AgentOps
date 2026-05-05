---
related_doc:
  - "/Users/sinclairpan/project/AI-Native底座开发文档/Agent_Store_AgentOps_AiSDLC_应用底座顶层规划_PRD.md"
  - "/Users/sinclairpan/project/AI-Native底座开发文档/AgentOps_项目_PRD.md"
---
# 实施计划：AgentOps 可信最小闭环

**编号**：`001-agentops-trusted-loop`  
**日期**：2026-05-05  
**规格**：`specs/001-agentops-trusted-loop/spec.md`

## 1. 概述

本计划按 contract-first 方式建设 AgentOps 阶段 0/1 底座。第一批产物冻结 baseline_id、Owner、追踪矩阵、Schema/API/状态/错误码 Registry、EventEnvelope v1、L5 核心事件、Bootstrap Credential、Evidence Summary、PolicyDecision、Agent Store Summary 与 AO-CT-001 到 AO-CT-006；第二批实现 Python 3.11 后端骨架和最小闭环；第三批补齐管理员页面模型、统一体验层、降级状态、contract tests 与 AI-SDLC gate。

## 2. 技术背景

**语言/版本**：Python 3.11+  
**主要依赖**：Pydantic v2 或等价 schema 校验库；HTTP 框架优先 FastAPI，若项目另行选型则保持 OpenAPI 契约不变。  
**存储**：开发期可用 SQLite；生产模型按 PostgreSQL 兼容关系结构设计。  
**测试**：pytest；contract tests 以 JSON Schema/OpenAPI 样例驱动。  
**目标平台**：部门内部 AgentOps 服务端，支持 Agent Store、Ai_AutoSDLC Reporter、SDK/Wrapper、外部 Connector 接入。  
**约束**：不得写 Agent/Skill 注册事实；不得改 Ai_AutoSDLC 本地 CLI；不得把 standalone 当作接入异常；未脱敏原文不得直接返回。

## 3. 宪章检查

| 宪章门禁 | 计划响应 |
|---|---|
| Persist decisions to the repository | AI 决策写入 `spec.md`、`research.md`，跨阶段任务写入 `tasks.md`，后续新增决策同步到 `.ai-sdlc/profiles/decisions.yml` |
| Prefer contract-level verification before closure | 每个阶段 1 核心能力绑定 AO-CT contract test，先冻结契约再实现 API |
| Keep docs and code traceable | 所有代码任务必须引用 `specs/001-agentops-trusted-loop` 下的 spec/plan/data-model/contracts，执行证据写入 task-execution-log |

## 4. 项目结构

### 文档结构

```text
specs/001-agentops-trusted-loop/
├── spec.md
├── research.md
├── data-model.md
├── plan.md
├── tasks.md
├── task-execution-log.md
└── contracts/
    ├── event-envelope-v1.schema.yaml
    ├── agentops-api.openapi.yaml
    └── contract-tests.md
```

### 源码结构

```text
src/agentops/
├── __init__.py
├── api/
│   ├── app.py
│   ├── ingestion.py
│   ├── credentials.py
│   ├── evidence.py
│   ├── policy.py
│   └── store_summary.py
├── core/
│   ├── envelope.py
│   ├── l5_gate.py
│   ├── evidence.py
│   ├── idempotency.py
│   ├── signature.py
│   └── redaction.py
├── models/
│   ├── events.py
│   ├── runs.py
│   ├── credentials.py
│   ├── evidence.py
│   └── policy.py
└── storage/
    ├── repository.py
    └── sqlite.py

tests/
├── contract/
│   ├── test_ao_ct_001_event_envelope.py
│   ├── test_ao_ct_002_credential_issue.py
│   ├── test_ao_ct_003_evidence_summary.py
│   ├── test_ao_ct_004_policy_decision.py
│   ├── test_ao_ct_005_store_summary.py
│   └── test_ao_ct_006_integration_mode.py
└── unit/
    ├── test_l5_gate.py
    ├── test_idempotency.py
    └── test_redaction.py
```

## 5. 阶段计划

### Phase 0：需求与契约冻结

**目标**：完成 PRD 到 spec/design 的收敛，冻结阶段 0/1 边界。  
**产物**：`spec.md`、`research.md`、`data-model.md`、`contracts/*`、`plan.md`，以及核心用户旅程、服务蓝图、统一 Shell、通知中心、待办中心、全局搜索、状态文案与 WCAG 2.2 AA 可访问性基线。  
**验证方式**：`ai-sdlc gate refine`、`ai-sdlc gate design`、两名对抗 agent 评审通过。  
**回退方式**：仅回退本工作项文档，不修改 PRD 基线。

### Phase 1：Python 后端骨架与契约测试框架

**目标**：建立可运行的 Python 3.11 服务骨架、schema 校验、测试目录与契约样例。  
**产物**：`src/agentops` 基础模块、pytest 配置、AO-CT 测试骨架。  
**验证方式**：contract tests 可执行且初始实现覆盖正反例。  
**回退方式**：保留 contracts，撤销未通过的实现模块。

### Phase 2：Ingestion、Evidence 与 L5 Gate 最小闭环

**目标**：实现签名事件接入、幂等写入、Evidence Summary、L5 Evaluation。  
**产物**：Ingestion API、event repository、l5 evaluator、run/evidence 查询。  
**验证方式**：AO-CT-001、AO-CT-003、AO-CT-006；完整/缺证据 run 的单元测试。  
**回退方式**：关闭 HTTP route，保留本地 evaluator 和 schema。

### Phase 3：Bootstrap Credential 与 Agent Store 回显

**目标**：实现 credential issue、signature test、Agent Store summary 契约。  
**产物**：credential API、device key 状态、summary API。  
**验证方式**：AO-CT-002、AO-CT-005。  
**回退方式**：禁用签发 route，保留验证/查询能力。

### Phase 4：Policy 降级口径与管理员页面模型

**目标**：定义阶段 1 policy_unknown、高风险 require_online/block、Risk Triage/Evidence Explorer/Approval Center/Policy Center/Quality Center 状态模型，并固化统一 Shell、通知中心、待办中心、全局搜索和权限失败页体验契约。  
**产物**：PolicyDecision 契约实现、UI view model JSON、空/错/降级状态。  
**验证方式**：AO-CT-004、可访问性字段检查、页面模型 snapshot。  
**回退方式**：将 policy route 标记为 read-only/degraded。

## 6. 工作流计划

### 工作流 A：Reporter 事件进入 Evidence

**范围**：Reporter -> Ingestion -> Raw Event -> Domain Event -> Evidence Summary。  
**影响范围**：事件 schema、签名校验、幂等、运行查询。  
**验证方式**：AO-CT-001、AO-CT-003、AO-CT-006。  
**回退方式**：拒绝高置信写入，返回可解释错误；本地 outbox 可重试。

### 工作流 B：Bootstrap 激活进入可信身份

**范围**：Agent Store signed assertion -> Credential Issue -> Signature Test。  
**影响范围**：installation/device/user 绑定、ReporterCredential、IngestionToken、DeviceKey。  
**验证方式**：AO-CT-002。  
**回退方式**：credential 不签发，Agent Store 显示 activation failed/expired。

### 工作流 C：Run 级 L5 判定与降级

**范围**：L5 核心事件 -> L5 evaluator -> Evidence Summary -> Store/Admin 回显。  
**影响范围**：证据等级、missing_evidence、confidence、degraded/pending 状态。  
**验证方式**：完整 run、缺 verification、governance degraded、outbox pending 四组测试。  
**回退方式**：最高 L4 或 pending L5 verification，不展示 L5。

### 工作流 D：管理员 triage 与跨项目回显

**范围**：Risk Triage、Evidence Explorer、Agent Store Summary 的 view model。  
**影响范围**：权限失败页、deep link、通知和下一步动作。  
**验证方式**：页面模型字段检查、权限失败脱敏断言。  
**回退方式**：返回脱敏摘要和 request_id，不返回原文。

## 7. 关键路径验证策略

| 关键路径 | 主验证方式 | 次验证方式 |
|---|---|---|
| EventEnvelope 接入 | AO-CT-001 | schema 样例校验、signature mock |
| Credential 签发 | AO-CT-002 | bootstrap 状态机单元测试 |
| Evidence Summary | AO-CT-003 | redaction/raw_access_state snapshot |
| PolicyDecision 降级 | AO-CT-004 | 高风险 unknown 状态测试 |
| Store Summary 回显 | AO-CT-005 | consumer schema 兼容测试 |
| integration_mode 语义 | AO-CT-006 | standalone/custom_sink/unknown 测试 |
| L5 Gate | unit + contract fixture | 完整/缺失事件矩阵 |

## 8. 开放问题

| 问题 | 状态 | 阻塞阶段 |
|---|---|---|
| IAM API 真实形态 | 使用 adapter + mock contract | Phase 4 强策略实现前 |
| Agent Store Registry 字段最终版 | 使用 consumer-driven contract | Phase 3 联调前 |
| 生产存储选型 | 当前按 PostgreSQL 兼容模型设计 | Phase 1 代码实现前 |

## 9. 实施顺序建议

1. 先冻结 contracts 和 contract fixtures。
2. 再搭 Python 服务与测试骨架。
3. 先实现 schema、幂等、签名校验接口，再实现业务查询。
4. L5 evaluator 先做纯函数，避免和 HTTP/DB 耦合。
5. Evidence Summary 与 Store Summary 只返回脱敏摘要和 deep links。
6. 最后补 Risk Triage/UX view model 与降级状态。
