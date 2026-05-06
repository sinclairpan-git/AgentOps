# 实施计划：AgentOps Console 运行事实数据源

**功能编号**：`005-agentops-live-console-source`  
**输入**：001/002 可执行内核、004 Console API Snapshot、AgentOps PRD 事件接入工作流

## 技术决策

1. **继续使用标准库 HTTP**：本阶段只验证本地开发闭环，不引入重型 Web 运行时。
2. **Repository-backed snapshot**：`build_console_snapshot(repository=...)` 从 `InMemoryRepository` 聚合运行事实；无 repository 参数时保留 004 样例兼容。
3. **安全摘要优先**：Console 只展示事件数量、event_type、hash、L5 结果和缺失证据，不展示 payload 原文。
4. **adapter truth 不升级**：仓库事实可用只证明数据源接通，不证明治理宿主已 verified_loaded。

## 阶段计划

### Phase 0：规格与契约冻结

冻结 005 范围、非目标、AO5-CT-001 到 AO5-CT-005。

### Phase 1：后端 live source

扩展 `console_snapshot.py`，从仓库事件构建 runs、evidence、quality、risks、connectors、sdlcRuns。

### Phase 2：HTTP 事件入口

扩展 `server.py`，新增 `POST /v1/events`，复用 ingestion contract。

### Phase 3：前端状态表达

前端识别 `source_detail.mode=repository_backed`，展示“后端事实快照已连接”，并支持 `empty` 状态。

### Phase 4：验证与 close

执行前后端 contract tests、Python 全量测试、ruff、build 与 AI-SDLC dry-run。

## 风险与控制

| 风险 | 控制 |
|---|---|
| live snapshot 被误认为生产数据源 | 文案使用“本地/事件仓库事实”，不声明生产 IAM 或数据库 |
| payload 泄露 | contract test 递归检查 `raw_payload`，builder 不读取 payload 原文正文 |
| 空状态破坏前端 | 前端 validator 明确接受 `empty`，StatusBadge 有中文标签 |
| repository 可用被误报为 verified_loaded | adapter status 保持 materialized，sdlcRuns 保持 unverified |

