# 规格：Console 运营工作台基础层

**功能编号**：`008-console-ops-hub`  
**类型**：new_requirement  
**依赖**：`007-agent-store-console-audit-workbench`

## 目标

在现有 AgentOps Console 上落地阶段 0 体验基线中的统一运营入口：全局搜索、通知中心和待办中心。它们必须消费已有治理摘要，不引入新的事实所有权，也不暴露 raw payload。

## 范围

- Console snapshot 新增 `operationCenter` 数据域。
- `operationCenter` 包含 `notifications`、`todos`、`searchIndex` 三类只读视图模型。
- Vue2 Shell 顶部新增全局搜索、通知入口、待办入口。
- 搜索结果和运营项必须能跳转到已有路由，例如审批中心、证据检索、风险处置、Agent Store 审计。

## 非目标

- 不实现生产消息推送、WebSocket、邮件或 IM 通知。
- 不实现服务端全文搜索引擎。
- 不新增 IAM/租户权限模型。
- 不展示未脱敏原文。

## 验收

- AO8-CT-001：snapshot 包含 `operationCenter` 且不含 `raw_payload`。
- AO8-CT-002：Agent Store 发现会进入待办和搜索索引。
- AO8-CT-003：审批与证据相关项具备可跳转运营入口。
- AO8-CT-004：正常注册运行保留搜索能力，不制造虚假 Agent Store 待办。
