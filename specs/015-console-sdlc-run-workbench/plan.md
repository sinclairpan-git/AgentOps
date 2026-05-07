# 015 Plan

1. 在后端 snapshot 聚合层新增 `sdlcRunWorkbench`，由 `sdlcRuns[]` 和事件仓库 L5 判定派生 Reporter、Outbox 与 Eligibility 摘要。
2. 前端 mock 与 API legacy fallback 同步实现 `sdlcRunWorkbench`，旧版 v1 快照缺域时仍安全补全只读摘要。
3. 前端 validator 严格校验 workbench 行与 `sdlcRuns[]` 的绑定，拒绝伪 `verified_loaded`、伪 outbox delivered、伪 reporter active 和危险字段。
4. `SdlcRunsView` 升级为中文 Ai_AutoSDLC 运行工作台，覆盖证明摘要、Reporter、Outbox、L5 条件和只读红线。
5. 补充 AO15 后端契约测试、前端契约测试、云端对抗 review 规则和工程约束测试。
