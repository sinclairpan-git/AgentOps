# 014 Tasks

- [x] T14-01 定义 connectorWorkbench 契约。
- [x] T14-02 扩展后端 snapshot 工作台聚合。
- [x] T14-03 扩展前端 mock、legacy fallback 与 validator。
- [x] T14-04 升级连接器状态中文界面。
- [x] T14-05 补充契约测试和对抗 review 检查。
- [x] T14-06 执行本地验证并准备 PR。

## 验收

- Snapshot 包含 `connectorWorkbench.health/dlq/syncTrail/guardrails`。
- 前端能拒绝缺字段、危险字段、状态篡改和伪治理激活。
- 页面中文展示连接器新鲜度、限流、DLQ、回放边界和证据影响。
- Review 脚本会阻断缺少 AO14 关键实现或测试的 PR。
