# 计划：Console 运营工作台基础层

## 实施策略

本阶段沿用 007 的 contract-first 方式，先冻结 `operationCenter` 视图契约，再扩展后端 snapshot、前端校验和 Shell UI。

## 技术方案

- 后端在 `build_console_snapshot` 末尾派生 `operationCenter`，避免各业务模块重复维护运营项。
- 运营项只引用已有 route、状态和摘要字段，不复制 raw payload。
- 前端 `AppShell` 承载全局搜索、通知中心和待办中心，保持现有页面 IA 不变。
- `agentOpsApiClient` 将 `operationCenter` 纳入 snapshot schema 校验。

## 风险控制

- 搜索只在前端对 snapshot 摘要做轻量过滤，不做敏感字段搜索。
- 通知/待办状态必须复用受控状态枚举。
- 移动端保持单列布局，搜索结果不遮挡核心内容。
