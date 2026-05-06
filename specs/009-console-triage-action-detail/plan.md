# 计划：Console 处置详情与行动面板

## 技术路径

- 后端在 `build_console_snapshot` 末尾派生 `actionWorkbench`，与 `operationCenter` 一样只消费现有治理摘要。
- `operationCenter` 条目新增 `action_id`，用于关联 `actionWorkbench.details`。
- 前端 `AppShell` 承载全局处置详情抽屉，业务页面通过事件打开详情。
- `agentOpsApiClient` 将 `actionWorkbench` 纳入 schema 校验、状态校验和 fallback 策略。

## 安全边界

- 处置详情为只读预案，不执行审批、Grant、风险关闭或原文访问。
- 处置详情不得包含 `raw_payload`。
- `verified_loaded` 仍必须遵守已有机器证明约束。

## 验证策略

- Python 契约测试覆盖 AO9-CT-001 到 AO9-CT-004。
- 前端契约测试覆盖中文 UI、schema 校验和安全回退。
- 全量回归覆盖 Python tests、Ruff、前端 test/build、AI-SDLC constraints。
