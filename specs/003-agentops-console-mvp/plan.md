---
related_plan: "specs/002-agentops-policy-approval-vault/plan.md"
related_doc:
  - "/Users/sinclairpan/project/AI-Native底座开发文档/AgentOps_项目_PRD.md"
  - "/Users/sinclairpan/project/AI-Native底座开发文档/Agent_Store_AgentOps_AiSDLC_应用底座顶层规划_PRD.md"
  - "/Users/sinclairpan/project/Ai_AutoSDLC/specs/016-frontend-enterprise-vue2-provider-baseline/spec.md"
---
# 实施计划：AgentOps Console MVP 前端界面

**编号**：`003-agentops-console-mvp` | **日期**：2026-05-05 | **规格**：`specs/003-agentops-console-mvp/spec.md`

## 概述

本计划先把 SDLC 框架级的前端治理约束实例化到 AgentOps 项目，再实现 Vue 2 控制台 MVP。核心判断是：SDLC 框架有企业 Vue2 Provider baseline，但 AgentOps 项目此前没有项目级前端 profile，也没有可打开的前端应用。因此本期不是绕过框架搭页面，而是按 `016-frontend-enterprise-vue2-provider-baseline` 的口径落地：Vue 2、企业组件库白名单 Provider、禁止全量 `Vue.use`、浏览器可验证。

## 技术背景

**语言/版本**：Vue 2.x、JavaScript、CSS。  
**主要依赖**：Vue 2；SDLC 企业 Vue2 组件库来源 `/Users/sinclairpan/project/前端组件库1`，包名 `@sxf/er-components`。  
**前端入口**：`apps/agentops-console/`。  
**组件库策略**：本期实现项目内 `enterprise-vue2-provider` 白名单包装层，只暴露 Console MVP 用到的基础 UI 能力；不得默认全量注册公司组件库。  
**数据来源**：阶段 3 使用 mock data adapter，字段对齐 001/002 Python view model 与 contract summary；后续 HTTP adapter 另起工作项。  
**测试**：前端单元/静态约束、浏览器截图验证、现有 Python contract tests、AI-SDLC constraints、GitHub Actions 三端测试与打包矩阵。  
**目标平台**：本地浏览器可运行的 AgentOps 管理控制台，后续可纳入 SDLC managed delivery/browser gate。  
**约束**：unknown 不得显示 healthy；高风险未知不得显示 allow；Evidence 不泄露 raw_payload；adapter dry-run 不得标记 verified_loaded；移动端不得遮挡关键操作。

## 宪章检查

| 宪章门禁 | 计划响应 |
|---|---|
| 先检查 adapter truth 与 dry-run | 已执行 `ai-sdlc adapter status` 与 `ai-sdlc run --dry-run`，dry-run 仅作为预演，不作为 verified_loaded 证明 |
| Persist decisions to the repository | 前端技术栈、组件库、Provider 禁止项写入 `spec.md`、`plan.md`、`contracts/frontend-console-contract.md` 与 `.ai-sdlc/profiles/tech-stack.yml` |
| Prefer contract-level verification before closure | 先冻结 AO3-CT-001 到 AO3-CT-006，再实现页面与浏览器验证 |
| Keep docs and code traceable | `tasks.md` 逐项绑定 docs、frontend files、验证命令和执行归档 |
| Respect framework frontend provider truth | 对齐 `016`，企业组件库只能作为 Provider 能力来源，禁止全量 `Vue.use` 默认入口 |
| Cross-platform claims require target evidence | 参考 Ai_AutoSDLC `181`，AgentOps 的 Windows/Linux/macOS 兼容性必须由 GitHub Actions 目标平台矩阵证明 |

## 项目结构

### 文档结构

```text
specs/003-agentops-console-mvp/
├── spec.md
├── plan.md
├── tasks.md
├── task-execution-log.md
└── contracts/
    └── frontend-console-contract.md
.github/workflows/
└── agentops-cross-platform.yml
docs/engineering/
└── cross-platform-compatibility.md
```

### 源码结构

```text
apps/agentops-console/
├── package.json
├── index.html
├── src/
│   ├── main.js
│   ├── App.js
│   ├── data/
│   │   └── mockAgentOpsData.js
│   ├── provider/
│   │   └── enterpriseVue2Provider.js
│   ├── components/
│   │   ├── AppShell.js
│   │   ├── StatusBadge.js
│   │   ├── MetricTile.js
│   │   └── DataTable.js
│   └── views/
│       ├── OverviewView.js
│       ├── RunsView.js
│       ├── EvidenceExplorerView.js
│       ├── ApprovalCenterView.js
│       ├── PolicyCenterView.js
│       ├── QualityCenterView.js
│       ├── RiskTriageView.js
│       ├── ConnectorStatusView.js
│       └── SdlcRunsView.js
└── tests/
    └── console-contract.test.js
```

### 验证结构

```text
tests/frontend/
└── test_agentops_console_contract.py

.ai-sdlc/memory/frontend-browser-gate/
└── latest.yaml               # 若本期命令可用则写入；否则记录缺口与后续接入点
```

## 阶段计划

### Phase 0：项目级前端约束冻结

**目标**：回答“SDLC 是否有内置企业 Vue2 组件库约束”，并将框架级约束落成 AgentOps 项目级 truth。  
**产物**：`spec.md`、`plan.md`、`tasks.md`、`contracts/frontend-console-contract.md`、`.ai-sdlc/profiles/tech-stack.yml`。  
**验证方式**：文档对账、对抗评审、`uv run ai-sdlc verify constraints`。  
**回退方式**：不进入前端实现，保留 002 已关闭后端状态。

### Phase 1：Console 骨架与企业 Provider

**目标**：搭建 Vue 2 应用、Shell、导航、mock adapter 和企业组件库白名单 Provider。  
**产物**：`apps/agentops-console` 基础结构。  
**验证方式**：依赖安装/构建、provider 静态约束测试、首页可打开。  
**回退方式**：Provider 回退到本项目轻量 shim，但保留白名单边界和禁用全量注册。

### Phase 2：核心页面 MVP

**目标**：实现 Overview、Runs、Evidence Explorer、Approval Center、Policy Center、Quality Center、Risk Triage、Connector Status、Ai_AutoSDLC Runs 九个页面。  
**产物**：页面组件、状态 badge、筛选、详情区域、响应式布局。  
**验证方式**：前端 contract test + 浏览器交互截图。  
**回退方式**：保留页面骨架与状态表，不接入真实 API。

### Phase 3：安全状态与浏览器验收

**目标**：补齐 empty/loading/error/degraded/permission_denied、Evidence raw 泄露断言、adapter proof 文案、桌面/移动 UI 验证。  
**产物**：测试、截图证据、执行日志。  
**验证方式**：`npm test/build`、Playwright 或 browser gate、Python 回归、ruff、AI-SDLC close-check。  
**回退方式**：修复 P0/P1 阻断后重新跑同一门禁。

### Phase 3a：跨平台工程门禁

**目标**：参考 Ai_AutoSDLC 的跨平台 release-gate 思路，为 AgentOps 建立 Windows/Linux/macOS 工程验证与云端分别打包矩阵。  
**产物**：`.github/workflows/agentops-cross-platform.yml`、`docs/engineering/cross-platform-compatibility.md`、workflow contract tests。  
**验证方式**：静态 workflow contract test + 本地 Python/Node 验证；目标平台测试和包产物证明以 GitHub Actions 运行结果为准。  
**回退方式**：保留本地验证命令，但不得宣称三端兼容或云端包可用。

### Phase 4：对抗评审与 close

**目标**：两个常驻对抗 agent 完成 UX 与 AI-Native/SDLC 审查，全部 P0/P1 清零后归档。  
**产物**：`development-summary.md`、更新 `task-execution-log.md`、Git 提交。  
**验证方式**：UX review、AI-Native review、自动测试与 AI-SDLC close。  
**回退方式**：进入对应 Phase 修复，不带阻断意见 close。

## 工作流计划

### 工作流 A：管理员总览到风险定位

**范围**：Overview -> Risk Triage -> Evidence/Policy/Approval deep link。  
**影响范围**：ConsoleSummary、RiskQueueItem、导航状态。  
**验证方式**：AO3-CT-001、AO3-CT-004。  
**回退方式**：展示 summary 和风险列表，不执行真实写操作。

### 工作流 B：审批处理

**范围**：Approval Center 状态筛选、详情、SLA、Grant 摘要。  
**影响范围**：ApprovalWorkItem、CapabilityGrant 摘要。  
**验证方式**：AO3-CT-005。  
**回退方式**：只展示只读审批动作和 next action。

### 工作流 C：Evidence 安全查看

**范围**：Evidence Explorer 脱敏摘要、raw_access_state、redaction_failed、permission_denied。  
**影响范围**：EvidencePanelState、安全文案、raw_payload 泄露断言。  
**验证方式**：AO3-CT-003。  
**回退方式**：只展示 hash 和安全空摘要。

### 工作流 D：AI-SDLC 接入证明

**范围**：Ai_AutoSDLC Runs、adapter status、dry-run、verified_loaded proof。  
**影响范围**：SdlcAdapterProof、ConnectorHealth。  
**验证方式**：AO3-CT-006。  
**回退方式**：materialized/unverified 保持黄色提示，不晋升 verified_loaded。

## 关键路径验证策略

| 关键路径 | 主验证方式 | 次验证方式 |
|---|---|---|
| Console 可打开且可导航 | 浏览器截图与交互 | AO3-CT-001 |
| 企业组件库不全量注册 | provider 静态测试 | 代码审查 |
| Evidence 不泄露 raw_payload | AO3-CT-003 | grep/fixture 断言 |
| unknown/degraded 不显示 healthy/allow | AO3-CT-004 | 页面状态快照 |
| Approval/Grant 状态不误导 | AO3-CT-005 | AO2 回归 |
| dry-run 不等于 verified_loaded | AO3-CT-006 | AGENTS.md 对账 |
| 移动端无遮挡 | Playwright/mobile screenshot | 人工视觉审查 |
| Windows/Linux/macOS 兼容 | GitHub Actions matrix | workflow contract test |
| 三端分别打包 | GitHub Actions package artifacts | artifact upload contract test |

## 开放问题

| 问题 | 状态 | 阻塞阶段 |
|---|---|---|
| SDLC managed-delivery 命令是否可直接识别本项目组件库 | 本期先项目级冻结与本地实现，后续接入 managed delivery | 后续平台化 |
| 企业组件库完整 peer dependency 是否可安装 | 本期以白名单 Provider 与本地 shim 降低风险，真实安装失败不改变治理边界 | Phase 1 |
| Vue2 SFC 编译链与 Node 24 兼容性 | 本期使用 Vue 2 full build + JS template 组件，避免旧 Vue CLI/SFC 插件链成为阻断 | Phase 1 |
| 真实 HTTP API | 本期 mock adapter；HTTP adapter 后续工作项 | 生产联调 |

## 实施顺序建议

1. 完成 Phase 0 文档、tech-stack profile 和前端 contract。
2. 将 Phase 0 产物发送给两个常驻对抗 agent，清理 P0/P1 意见。
3. 创建 `apps/agentops-console` Vue 2 应用和企业组件库白名单 Provider。
4. 实现八个 MVP 页面与 mock data adapter。
5. 增加前端 contract test、浏览器截图验证和现有 Python 回归。
6. 完成合议、执行日志、close-check、正式 close。
