# 功能规格：Agent Store 发现与运行审计控制台

**功能编号**：`007-agent-store-console-audit-workbench`  
**分类**：`new_requirement`  
**上游依赖**：`006-agent-store-discovery-audit`

## 目标

本阶段把 006 已完成的 Agent Store metadata 消费、未注册发现、Run Audit 和 Store 回显摘要，落地为前端可操作的 AgentOps 控制台工作台。

完成后必须能够证明：

1. 管理员可以在控制台查看 Agent Store 未注册 Agent/Skill 发现队列。
2. 管理员可以查看每个运行的审计摘要、注册状态、事件数量、deep links 和关联 Agent 版本。
3. 管理员可以查看 Store 回显摘要中的 evidence、risk、approval、policy_requirement 和 run audit 摘要。
4. 前端和快照契约不得暴露 raw payload，不得把 AgentOps 显示为 Agent/Skill 注册事实源。
5. 空状态、降级状态和未知状态必须使用中文解释，不得误导为已治理激活。

## 非目标

- 不实现 Agent Store 注册、上架、编辑或详情主流程。
- 不写入 Agent/Skill 注册事实。
- 不接真实 Agent Store HTTP 服务。
- 不实现完整质量评分、Git/PR/CI/Test Connector 或生产数据库。

## 功能需求

- **FR-001**：Console snapshot 必须包含 `agentStore` 工作台数据，覆盖 discovery gaps、run audits、Store summaries 和 registry map。
- **FR-002**：Agent Store 工作台路由必须出现在控制台导航中，中文标签为“Agent Store 审计”。
- **FR-003**：未注册 Agent/Skill 必须展示 gap_id、类型、状态、严重级别、Owner 提示、主要动作和 affected_runs。
- **FR-004**：Run Audit 必须展示 audit_id、run_id、agent_id、version、registration_state、event_count、discovery_gap_ids、related_agent_versions 和 deep links。
- **FR-005**：Store Summary 必须展示 metadata_state、risk_state、evidence_level、confidence、policy_requirement、discovery_gap_ids 和有效期。
- **FR-006**：前端契约必须拒绝缺少 `agentStore` 的 snapshot，并拒绝包含 `raw_payload` 的 snapshot。
- **FR-007**：所有用户可见文案面向中国大陆用户，除 Agent Store、AgentOps、Policy、L5、API、run_id 等固定名词外不得使用英文。

## 契约测试

| 测试 | 验收 |
|---|---|
| AO7-CT-001 | Console snapshot 包含 Agent Store 工作台路由和数据集合 |
| AO7-CT-002 | 未注册 Agent/Skill 在工作台中可见，且不包含 raw_payload |
| AO7-CT-003 | Run Audit 工作台保留 deep links、关联版本和 discovery gap |
| AO7-CT-004 | Store Summary 工作台展示 policy_requirement、risk_state 和有效期 |
| AO7-CT-005 | 前端 validateSnapshot 缺少 agentStore 时失败 |
| AO7-CT-006 | 前端页面和 mock 数据包含中文 Agent Store 审计工作台 |

## 成功标准

- `uv run pytest tests/contract/test_ao7_ct_agent_store_console_audit_workbench.py -q` 通过。
- `uv run pytest tests -q` 通过。
- `uv run ruff check src tests` 通过。
- `npm test` 和 `npm run build` 通过。
- `uv run ai-sdlc verify constraints` 通过。
