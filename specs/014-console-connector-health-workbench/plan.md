# 014 Plan

1. 后端在 `build_console_snapshot` 工作台聚合层新增 `connectorWorkbench`，从 `connectors[]` 派生健康、DLQ 和同步轨迹摘要。
2. 前端 mock 与 API fallback 同步实现 `connectorWorkbench`，旧版 v1 快照缺域时仍安全展示只读摘要。
3. 前端 validator 严格校验连接器行与原始 `connectors[]` 的状态绑定，拒绝危险字段、状态篡改和伪 `verified_loaded`。
4. `ConnectorStatusView` 升级为中文连接器健康工作台，覆盖健康、限流、DLQ、Outbox Replay、同步轨迹和处置红线。
5. 补充 AO14 后端契约测试、前端契约测试、云端对抗 review 规则和工程约束测试。
