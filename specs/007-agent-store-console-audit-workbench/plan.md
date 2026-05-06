# 实施计划：Agent Store 发现与运行审计控制台

## 架构决策

| 决策 | 说明 |
|---|---|
| 复用 Console snapshot | 007 是前端工作台，不新增生产 HTTP 依赖；先把 006 的治理事实合入现有快照 |
| `agentStore` 独立数据域 | 避免把 discovery、audit、summary 混散到风险列表，方便前端形成专门工作台 |
| 前端只展示，不写 Store | Agent Store 仍是注册事实源，AgentOps 只消费和回显 |
| Contract-first | 先补 AO7 契约测试，再实现后端和 Vue2 页面 |

## 批次

### Batch 1：规格与契约

- 冻结 007 spec、plan、tasks、contract。
- 定义 `agentStore.discoveryGaps`、`agentStore.runAudits`、`agentStore.storeSummaries`、`agentStore.registryMap`。

### Batch 2：后端快照数据

- 扩展 `build_console_snapshot` 路由和 `consoleData.agentStore`。
- 从 repository 事实生成 discovery、audit、summary 和 registry map。
- 保持 raw payload 禁止泄露。

### Batch 3：前端工作台

- 新增 `AgentStoreAuditView`。
- 导航新增“Agent Store 审计”。
- 更新 mock data、snapshot validation 和中文契约测试。

### Batch 4：验证、评审与合入

- 跑后端契约、全量 pytest、ruff、前端 test/build 和 AI-SDLC 约束校验。
- 推送分支、创建 PR、触发 Codex review，并按固定规则轮询至合入。

## 风险

| 风险 | 处理 |
|---|---|
| 误读为真实 Store 联调 | source boundary 和页面文案说明当前为 AgentOps repository-backed 快照 |
| raw payload 泄露 | 后端契约和前端 validateSnapshot 继续递归拒绝 `raw_payload` |
| 工作台信息过载 | 以发现队列、运行审计、回显摘要三块组织，不做 Store 注册主流程 |
