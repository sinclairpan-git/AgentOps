# 契约：Console 处置详情与行动面板

## AO9-CT-001 Action Workbench Snapshot

`GET /v1/console/snapshot` 必须返回 `consoleData.actionWorkbench.details`。

- `details[]` 必须是数组。
- 任意层级不得出现 `raw_payload`。

## AO9-CT-002 Operation Center 可打开详情

`operationCenter.notifications/todos/searchIndex` 中存在 `action_id` 的条目，必须能在 `actionWorkbench.details` 中找到同 ID 详情。

## AO9-CT-003 Agent Store 处置详情优先可达

当存在 Agent Store discovery gap 时：

- 必须生成 `action_gap_*` 处置详情。
- 该详情必须可从 Agent Store 待办或搜索条目打开。
- 即使通知、待办或搜索触发展示上限，也必须保留 gap 的入口。

## AO9-CT-004 详情字段

每个处置详情必须包含：

- `id`
- `title`
- `summary`
- `status`
- `route`
- `owner`
- `primary_action`
- `secondary_action`
- `close_condition`
- `audit_ref`
- `safety_note`

`safety_note` 必须说明当前为只读处置预案，不执行生产写操作。

## AO9-CT-005 前端体验

前端必须提供中文处置详情抽屉，至少展示：

- 处置详情
- 负责人
- 建议动作
- 关闭条件
- 审计引用
- 只读处置预案
