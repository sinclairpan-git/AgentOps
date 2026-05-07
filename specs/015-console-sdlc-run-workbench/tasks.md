# 015 Tasks

- [x] T15-01 定义 `sdlcRunWorkbench` 契约。
- [x] T15-02 扩展后端 snapshot 工作台聚合。
- [x] T15-03 扩展前端 mock、legacy fallback 与 validator。
- [x] T15-04 升级 Ai_AutoSDLC Runs 中文界面。
- [x] T15-05 补充契约测试和对抗 review 检查。
- [x] T15-06 执行本地验证并准备 PR。

## 验收

- Snapshot 包含 `sdlcRunWorkbench.summary/reporter/outbox/eligibility/guardrails`。
- 前端能拒绝缺字段、危险字段、状态篡改、伪 reporter active、伪 outbox delivered 和伪治理激活。
- 页面中文展示 Reporter、Outbox、L5 条件、adapter 真值、降级原因和只读边界。
- Review 脚本会阻断缺少 AO15 关键实现或测试的 PR。
