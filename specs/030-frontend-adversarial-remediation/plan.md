# 实施计划：前端对抗评审问题归档与修复

**编号**：`030-frontend-adversarial-remediation` | **日期**：2026-05-08 | **规格**：specs/030-frontend-adversarial-remediation/spec.md

## 概述

本阶段将两个对抗评审结果归档为前端修复工作项，并在 `apps/agentops-console` 内依次修复 P0/P1 问题。修复方式保持只读控制台边界，不引入新的后端写操作。

## 技术背景

**语言/版本**：Vue 2.7、Vite 5、标准 JavaScript  
**主要依赖**：本地 vendor enterprise-vue2 包、项目自有 `DataTable` / `StatusBadge` / Shell 组件  
**存储**：后端 snapshot + 前端 normalized view model  
**测试**：`npm test`、`npm run build`、浏览器逐页复测、console error 检查  
**目标平台**：桌面 Chrome，本阶段兼顾移动宽度布局风险  
**约束**：不执行真实审批、凭证、Outbox 或生产写操作；不展示 raw payload。

## 宪章检查

| 宪章门禁 | 计划响应 |
|----------|----------|
| 只读治理边界 | 页面只补展示、空态、搜索和布局，不新增生产写动作 |
| 证据安全 | Evidence Vault 仍只展示摘要、哈希、申请、授权和审计状态 |
| 可验证性 | 每项修复以契约测试、构建、浏览器逐页检查和对抗复测验证 |
| 用户可理解 | 每页增加结论、空态和下一步，降低默认术语密度 |

## 项目结构

```text
apps/agentops-console/src/
├── App.js
├── components/
│   ├── AppShell.js
│   └── DataTable.js
├── data/
│   └── agentOpsApiClient.js
├── styles.css
└── views/
    ├── EvidenceExplorerView.js
    ├── RiskTriageView.js
    ├── SdlcRunsView.js
    └── ...
```

## 阶段计划

### Phase 0：归档与待办冻结

**目标**：把两个对抗评审发现归档到 spec/tasks。  
**产物**：`spec.md`、`plan.md`、`tasks.md`、`task-execution-log.md`。  
**验证方式**：文档对账、`ai-sdlc program truth sync --execute --yes`。  
**回退方式**：保留 030 work item，不改已有 001-029 归档。

### Phase 1：P0 修复

**目标**：修复组件错误、风险页断流、Ai_AutoSDLC 长文本可读性。  
**产物**：前端组件、视图、CSS、契约测试更新。  
**验证方式**：`npm test`、`npm run build`、浏览器 console 检查。  
**回退方式**：撤回对应前端文件变更。

### Phase 2：P1/P2 体验修复

**目标**：补全搜索反馈、空态、页面结论、顶部标题和状态语义。  
**产物**：Shell 搜索结果面板、统一空态、页面结论文案。  
**验证方式**：逐页点击、桌面截图、移动抽查。  
**回退方式**：保留 P0 修复，单独撤回体验增强。

### Phase 3：对抗复测

**目标**：重新用业务小白和 Web 测试专家视角逐页复测。  
**产物**：复测结论写入 `task-execution-log.md`。  
**验证方式**：两个对抗 agent 均不再报告 P0。  
**回退方式**：将剩余问题重新列入待办，不误标完成。

## 关键路径验证策略

| 关键路径 | 主验证方式 | 次验证方式 |
|----------|------------|------------|
| Evidence DataTable | 浏览器 console 无 Vue error | `npm test` |
| 搜索反馈 | 手动输入命中/无命中词 | DOM snapshot |
| 风险处置队列 | 总览 CTA 跳转后可承接 | 业务对抗复测 |
| 长文本布局 | 桌面/移动截图 | CSS overflow 检查 |
| 只读边界 | 前端契约测试 | 文案审查 |

## 开放问题

| 问题 | 状态 | 阻塞阶段 |
|------|------|----------|
| 是否引入真实写操作 | 不引入 | 无 |
| 是否新增后端字段 | 默认不新增 | 无 |
