# 规格：人工审批与 Grant 处置工作台

**功能编号**：`013-approval-grant-workbench`

**依赖**：`012-console-evidence-vault-workbench`

## 目标

承接 AgentOps PRD 中“高风险动作必须经过人工审批、Grant 必须可追溯、撤销与过期必须影响后续策略判断”的要求，把审批中心从基础列表增强为只读处置工作台。用户必须能同时看到审批队列、补充材料、SLA 风险、Grant 影响和审批审计轨迹，但不能在控制台直接执行批准、拒绝、撤销或生产写操作。

## 范围

- Console snapshot 新增 `approvalWorkbench` 只读数据域。
- `approvalWorkbench` 必须包含 `queues`、`grants`、`auditTrail` 和 `guardrails`。
- Approval Center 展示审批队列、Grant 影响、审批审计轨迹和处置红线。
- 前端 validator 必须兼容旧版 v1 快照缺失 `approvalWorkbench` 的情况，并由审批基础列表安全补全只读摘要。
- 所有文案面向中国大陆用户；固定名词 AgentOps、Grant、SLA、IAM、Policy Check 可保留。

## 非目标

- 不实现真实审批提交、拒绝、撤销或 Grant 签发写接口。
- 不连接生产 IAM、多租户权限、消息通知或工单系统。
- 不展示审批申请原文、PR 正文、下载链接或 raw access URL。
- 不把 `pending`、`escalated`、`revoked` 等状态篡改成已授权态。

## 验收标准

- AO13-CT-001：snapshot 必须包含 `approvalWorkbench.queues`、`approvalWorkbench.grants`、`approvalWorkbench.auditTrail` 和 `approvalWorkbench.guardrails`。
- AO13-CT-002：每条审批队列、Grant 影响和审计节点必须具备契约字段，并能关联 `approval_id` 和 `audit_id`。
- AO13-CT-003：`approvalWorkbench` 不得包含原文、下载链接、raw access URL、URL 或 PR 原文类字段。
- AO13-CT-004：`pending`、`escalated`、`approved`、`revoked` 必须映射到安全的主动作、Grant 状态、授权时限和撤销说明。
- AO13-CT-005：空仓库必须返回安全空工作台，并保留审批队列只读和申请人不得自批的红线。
