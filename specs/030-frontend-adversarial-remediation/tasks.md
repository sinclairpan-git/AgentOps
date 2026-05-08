# 任务分解：前端对抗评审问题归档与修复

**编号**：`030-frontend-adversarial-remediation` | **日期**：2026-05-08

## Batch 1：问题归档与待办冻结

### T11 归档对抗评审问题

- **状态**：已完成
- **优先级**：P0
- **文件**：`spec.md`、`plan.md`、`tasks.md`
- **验收**：业务小白和 Web 测试专家发现已归档，P0/P1/P2 待办明确。

## Batch 2：P0 功能与布局修复

### T21 修复 Evidence Vault 表格组件错误

- **状态**：待执行
- **优先级**：P0
- **文件**：`apps/agentops-console/src/views/EvidenceExplorerView.js`
- **验收**：证据检索页注册 `DataTable`，浏览器 console 无 `<data-table>` 未注册错误。

### T22 补齐风险处置队列

- **状态**：待执行
- **优先级**：P0
- **文件**：`apps/agentops-console/src/views/RiskTriageView.js`
- **验收**：页面展示风险队列、负责人、严重度、下一步动作、详情入口；空态说明不再断流。

### T23 修复 Ai_AutoSDLC 长文本与表格可读性

- **状态**：待执行
- **优先级**：P0
- **文件**：`apps/agentops-console/src/views/SdlcRunsView.js`、`apps/agentops-console/src/styles.css`
- **验收**：长 ID、缺失条件、回放边界、materialized/unverified 等不重叠、不硬裁切。

## Batch 3：P1 交互与空态修复

### T31 实现全局搜索结果和空结果反馈

- **状态**：待执行
- **优先级**：P1
- **文件**：`apps/agentops-console/src/components/AppShell.js`、`apps/agentops-console/src/styles.css`
- **验收**：输入命中词时显示结果列表；输入无命中词时显示“未找到”；点击结果跳转。

### T32 统一表格空态与页面结论

- **状态**：待执行
- **优先级**：P1
- **文件**：`apps/agentops-console/src/components/DataTable.js`、`apps/agentops-console/src/views/*.js`
- **验收**：运行、审批、质量、Agent Store、凭证、连接器等表格无数据时都有解释和下一步。

### T33 调整顶部标题和 source banner 层级

- **状态**：待执行
- **优先级**：P1
- **文件**：`apps/agentops-console/src/App.js`、`apps/agentops-console/src/components/AppShell.js`、`apps/agentops-console/src/styles.css`
- **验收**：完整 source banner 仅总览显示；功能页顶部标题不硬换行。

## Batch 4：验证与对抗复测

### T41 前端契约和构建验证

- **状态**：待执行
- **优先级**：P0
- **命令**：`npm test`、`npm run build`
- **验收**：全部通过。

### T42 浏览器逐页验证

- **状态**：待执行
- **优先级**：P0
- **验收**：11 个页面可访问，console 无 Vue error，搜索和 CTA 可用。

### T43 双视角对抗复测

- **状态**：待执行
- **优先级**：P1
- **验收**：业务小白与 Web 测试专家复测不再报告 P0；剩余 P1/P2 写入执行日志。
