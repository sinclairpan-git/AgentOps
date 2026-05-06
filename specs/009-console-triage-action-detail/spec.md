# 规格：Console 处置详情与行动面板

**功能编号**：`009-console-triage-action-detail`  
**类型**：new_requirement  
**依赖**：`008-console-ops-hub`

## 目标

承接 008 的通知、待办和搜索入口，把“发现异常”推进到“理解如何处置”。Console 必须为风险、审批、证据和 Agent Store 发现项提供统一的只读处置详情，展示原因、负责人、建议动作、关闭条件、审计引用和安全边界。

## 范围

- Console snapshot 新增 `actionWorkbench.details` 只读视图模型。
- `operationCenter` 的通知、待办和搜索条目必须能关联到对应处置详情。
- 风险处置、审批中心和证据检索页面必须能打开同一套处置详情抽屉。
- 处置详情只展示治理摘要、审计引用、证据引用和关闭条件，不暴露 raw payload。

## 非目标

- 不实现真实审批通过/拒绝、Grant 签发、风险关闭或生产写操作。
- 不实现 IAM、RBAC/ABAC、多租户权限后端。
- 不实现生产消息推送、WebSocket、邮件或 IM 通知。
- 不展示 Evidence Vault 原文。

## 验收

- AO9-CT-001：snapshot 包含 `actionWorkbench.details`，且不包含 `raw_payload`。
- AO9-CT-002：通知、待办、搜索条目的 `action_id` 必须能映射到处置详情。
- AO9-CT-003：Agent Store discovery gap 必须生成处置详情，且在上限场景下仍可从待办/搜索打开。
- AO9-CT-004：处置详情必须包含 owner、primary_action、secondary_action、close_condition、audit_ref 和 safety_note。
- AO9-CT-005：前端必须提供中文处置详情抽屉，并在 schema 异常时安全回退。
