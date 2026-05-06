# 契约：Console 运营工作台基础层

## AO8-CT-001 Operation Center Snapshot

`GET /v1/console/snapshot` 必须返回 `consoleData.operationCenter`，包含：

- `notifications[]`
- `todos[]`
- `searchIndex[]`

任意层级不得出现 `raw_payload`。

## AO8-CT-002 Agent Store 发现运营化

当存在 Agent Store discovery gap 时：

- 待办必须包含负责人、状态、目标路由和面向业务的处理期限，不得把运行 ID 或技术引用伪装成到期线。
- 搜索索引必须包含可跳转到 `agent-store-audit` 的条目。

## AO8-CT-003 审批与证据可行动

当存在 pending/escalated 审批或证据异常时：

- 通知中心必须出现对应提醒。
- 待办必须包含 owner、status、route、due；`due` 必须是人可理解的 SLA、复核提示或排期提示。
- 搜索索引必须包含审批或证据摘要。

## AO8-CT-004 不制造虚假待办

当运行已注册、证据链完整且无 Agent Store gap 时：

- 搜索仍能找到运行。
- 不得生成 Agent Store 补注册待办。
