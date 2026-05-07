# 计划：019 Console Credential Handoff Workbench

## 实施路径

1. 扩展后端 Console snapshot：新增 `credentialHandoff` summary、sessions 和 guardrails。
2. 扩展前端路由与页面：新增“凭证联调”视图，展示状态、下一步、允许/禁止动作和只读边界。
3. 扩展前端 snapshot validator：校验工作台形状、计数一致性、`not_asserted` 边界和敏感字段禁入。
4. 补充契约测试与云端对抗 review 规则。
5. 跑本地 Python/Node 契约测试、ruff、AI-SDLC truth/constraints/program/dry-run。

## 技术约束

- 继续使用 Python 3.11+ 标准库后端与 Vue2 企业组件库前端。
- 控制台文案面向中国大陆用户，除固定名词和契约字段外使用中文。
- 只读展示，不引入生产写操作。
