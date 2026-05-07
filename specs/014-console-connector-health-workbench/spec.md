# 014 Console Connector Health Workbench

## 背景

AgentOps 不能只展示后台连接器是否存在。连接器状态会直接影响 L5 证据等级、Policy 判定、Evidence Vault 访问、审批 Grant 和 Agent Store 回显，因此 Console 必须把 Git、PR、CI、测试、IAM、证据、策略和 SDLC 连接器的新鲜度、限流、DLQ、回放边界与降级影响放到一个只读工作台。

## 范围

- Console snapshot 新增 `connectorWorkbench` 只读数据域。
- `connectorWorkbench` 必须包含 `health`、`dlq`、`syncTrail` 和 `guardrails`。
- 每个工作台行必须绑定原始 `connectors[]` 的 `connector_id`、状态、心跳和 `request_id`。
- 前端 validator 必须兼容旧版 v1 快照缺失 `connectorWorkbench` 的情况，并由基础连接器列表安全补全只读摘要。
- 中文界面必须明确展示 15 分钟新鲜度 SLO、超过 20 分钟告警、限流状态、DLQ/Outbox Replay、证据等级影响和只读红线。

## 非目标

- 不接入真实生产 Git/PR/CI/Test/IAM 凭据。
- 不在控制台执行连接器重试、Outbox Replay、权限变更或生产写操作。
- 不把 `materialized/unverified` 当作 `verified_loaded` 治理激活证明。
- 不展示 raw payload、下载链接、外部 URL、PR 原文、diff 或代码片段。

## 契约测试

- AO14-CT-001：snapshot 必须包含 `connectorWorkbench.health`、`connectorWorkbench.dlq`、`connectorWorkbench.syncTrail` 和 `connectorWorkbench.guardrails`。
- AO14-CT-002：健康、DLQ 和同步轨迹行必须具备完整契约字段。
- AO14-CT-003：工作台不得包含 raw、download、URL 或 PR 原文字段。
- AO14-CT-004：`conn_sdlc` 为 `materialized` 时不得宣称治理激活，只能提示补齐 `verified_loaded` 机器证明。
- AO14-CT-005：降级连接器必须降低证据等级，并进入人工审批后的回放边界。
- AO14-CT-006：仓库快照必须展示 Git、PR、CI、测试、IAM 连接器边界。
