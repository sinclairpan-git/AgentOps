---
related_plan: "specs/002-agentops-policy-approval-vault/plan.md"
related_doc:
  - "/Users/sinclairpan/project/AI-Native底座开发文档/AgentOps_项目_PRD.md"
  - "/Users/sinclairpan/project/AI-Native底座开发文档/Agent_Store_AgentOps_AiSDLC_应用底座顶层规划_PRD.md"
  - "/Users/sinclairpan/project/Ai_AutoSDLC/specs/016-frontend-enterprise-vue2-provider-baseline/spec.md"
---
# 任务分解：AgentOps Console MVP 前端界面

**编号**：`003-agentops-console-mvp` | **日期**：2026-05-05  
**来源**：`plan.md` + `spec.md`

---

## 分批策略

```text
Batch 1: frontend formal baseline and provider constraints
Batch 2: Vue2 console scaffold and enterprise provider wrapper
Batch 3: AgentOps core pages and safety states
Batch 4: browser verification, adversarial review, and close
```

---

## Batch 1：frontend formal baseline and provider constraints

### Task 1.1 冻结 AgentOps 前端项目级真值

- **任务编号**：T11
- **优先级**：P0
- **依赖**：`ai-sdlc adapter status`、`ai-sdlc run --dry-run`
- **文件**：`specs/003-agentops-console-mvp/spec.md`、`plan.md`、`tasks.md`、`task-execution-log.md`
- **可并行**：否
- **验收标准**：
  1. 明确 Vue 2、SDLC 企业 Vue2 组件库、Provider 白名单和禁止全量 `Vue.use`
  2. 明确 Console MVP 页面范围、非目标、安全状态和浏览器验收
  3. 明确 dry-run 不等于 `verified_loaded`
- **验证**：文档对账 + 对抗评审

### Task 1.2 更新项目级 tech-stack profile

- **任务编号**：T12
- **优先级**：P0
- **依赖**：T11
- **文件**：`.ai-sdlc/profiles/tech-stack.yml`
- **可并行**：是
- **验收标准**：
  1. frontend stack 记录为 Vue 2
  2. component library 记录为 SDLC enterprise Vue2，source path 指向 `/Users/sinclairpan/project/前端组件库1`
  3. app_dir 记录为 `apps/agentops-console`
- **验证**：`sed -n '1,220p' .ai-sdlc/profiles/tech-stack.yml`

### Task 1.3 冻结 Console 前端契约

- **任务编号**：T13
- **优先级**：P0
- **依赖**：T11
- **文件**：`specs/003-agentops-console-mvp/contracts/frontend-console-contract.md`
- **可并行**：是
- **验收标准**：
  1. AO3-CT-001 到 AO3-CT-007 均有字段、状态和验收命令
  2. Evidence raw payload 禁止项与 adapter proof 口径可测试
  3. 企业组件库白名单与禁用能力可审查
- **验证**：文档对账 + 对抗评审

---

## Batch 2：Vue2 console scaffold and enterprise provider wrapper

### Task 2.1 创建 Vue2 Console 应用骨架

- **任务编号**：T21
- **优先级**：P0
- **依赖**：T11-T13
- **文件**：`apps/agentops-console/package.json`、`index.html`、`src/main.js`、`src/App.js`
- **可并行**：否
- **验收标准**：
  1. 本地开发服务可启动
  2. Console Shell 可显示导航、顶部治理状态和主内容区
  3. 不依赖真实后端即可展示 mock 数据
- **验证**：`npm install`、`npm run dev` 或 `npm run build`

### Task 2.2 实现企业 Vue2 Provider 白名单包装

- **任务编号**：T22
- **优先级**：P0
- **依赖**：T21
- **文件**：`apps/agentops-console/src/provider/enterpriseVue2Provider.js`、`apps/agentops-console/src/components/*`
- **可并行**：否
- **验收标准**：
  1. Provider 暴露白名单组件和能力声明
  2. 代码中不存在默认全量 `Vue.use(ErComponents)` 路径
  3. 企业组件库不可用时，Console 使用本项目安全 shim 保持可运行
- **验证**：前端 contract test + 代码搜索

### Task 2.3 实现 mock data adapter

- **任务编号**：T23
- **优先级**：P0
- **依赖**：T21
- **文件**：`apps/agentops-console/src/data/mockAgentOpsData.js`
- **可并行**：是
- **验收标准**：
  1. mock 字段覆盖 001/002 view model 的核心字段
  2. 包含 degraded、unknown、permission_denied、redaction_failed、approval_required 样例
  3. 不包含可被 UI 展示的 raw_payload
- **验证**：前端 contract test

---

## Batch 3：AgentOps core pages and safety states

### Task 3.1 实现 Overview 与 Runs

- **任务编号**：T31
- **优先级**：P0
- **依赖**：T21-T23
- **文件**：`OverviewView.vue`、`RunsView.vue`
- **可并行**：是
- **验收标准**：
  1. Overview 显示治理摘要、SLO、风险、审批、证据、连接器
  2. Runs 显示 run_id、agent、skill、L5 Gate、policy_state、evidence_state、risk_level
  3. unknown/degraded 不显示为 healthy
- **验证**：AO3-CT-001、AO3-CT-004

### Task 3.2 实现 Evidence Explorer 与 Approval Center

- **任务编号**：T32
- **优先级**：P0
- **依赖**：T21-T23
- **文件**：`EvidenceExplorerView.vue`、`ApprovalCenterView.vue`
- **可并行**：是
- **验收标准**：
  1. Evidence Explorer 不展示 raw_payload
  2. redaction_failed 只展示 hash、告警和补救动作
  3. Approval Center 覆盖 pending、needs_more_info、approved、rejected、expired、revoked、escalated
- **验证**：AO3-CT-003、AO3-CT-005

### Task 3.3 实现 Policy Center、Quality Center 与 Risk Triage

- **任务编号**：T33
- **优先级**：P0
- **依赖**：T21-T23
- **文件**：`PolicyCenterView.js`、`QualityCenterView.js`、`RiskTriageView.js`
- **可并行**：是
- **验收标准**：
  1. Policy Center 展示 decision、fallback_action、policy_version、Grant TTL、audit_id
  2. Quality Center 展示 quality_drop、contract test、browser gate、evidence completeness
  3. Risk Triage 展示 policy_block、approval_overdue、evidence_failed、quality_drop
  4. 高风险 unknown 不显示 allow
- **验证**：AO3-CT-004、AO3-CT-006

### Task 3.4 实现 Connector Status 与 Ai_AutoSDLC Runs

- **任务编号**：T34
- **优先级**：P1
- **依赖**：T21-T23
- **文件**：`ConnectorStatusView.js`、`SdlcRunsView.js`
- **可并行**：是
- **验收标准**：
  1. Connector Status 展示 Agent Store、AI-SDLC、Evidence Store、Policy Service、IAM/Security
  2. Ai_AutoSDLC Runs 明确 dry-run、materialized、verified_loaded、degraded、unsupported 区别
  3. materialized/unverified 不得显示为 verified_loaded
- **验证**：AO3-CT-006

---

## Batch 4：browser verification, adversarial review, and close

### Task 4.1 完成前端 contract tests 与构建验证

- **任务编号**：T41
- **优先级**：P0
- **依赖**：T31-T34
- **文件**：`apps/agentops-console/tests/*`、`tests/frontend/*`
- **可并行**：否
- **验收标准**：
  1. AO3-CT-001 到 AO3-CT-007 有自动化断言
  2. `npm run build` 通过
  3. Python 现有 contract tests 不回归
- **验证**：`npm test`、`npm run build`、`uv run pytest tests -q`

### Task 4.2 完成浏览器与视觉验收

- **任务编号**：T42
- **优先级**：P0
- **依赖**：T41
- **文件**：`.ai-sdlc/memory/frontend-browser-gate/*` 或 `specs/003-agentops-console-mvp/evidence/*`
- **可并行**：否
- **验收标准**：
  1. 桌面和移动视口可打开 Console
  2. 主导航可交互
  3. 无关键文本重叠、无空白主画布、关键状态可见
- **验证**：Playwright/browser gate 截图

### Task 4.3 对抗评审、归档与 close

- **任务编号**：T43
- **优先级**：P0
- **依赖**：T41-T42
- **文件**：`task-execution-log.md`、`development-summary.md`
- **可并行**：否
- **验收标准**：
  1. UX 对抗 agent 无 P0/P1 阻断意见
  2. AI-Native/SDLC 对抗 agent 无 P0/P1 阻断意见
  3. AI-SDLC constraints、workitem close-check 和 dry-run/close 流程通过
- **验证**：对抗评审记录 + `uv run ai-sdlc verify constraints` + `ai-sdlc workitem close-check`
