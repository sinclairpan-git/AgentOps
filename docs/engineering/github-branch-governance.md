# AgentOps GitHub 分支治理

AgentOps 的 GitHub 分支治理参考 Ai_AutoSDLC 的主干保护方式，目标是让所有进入主线的变更都经过可复现的跨平台门禁，而不是依赖本地开发机结果。

## 仓库入口

- 仓库可见性：public
- 默认分支：`main`
- 工作分支：`feature/**`
- 主线合入方式：通过 Pull Request 合入 `main`

## 主干规则

GitHub repository ruleset 名称为 `main-compatibility-gate`，作用范围为默认分支：

- 禁止删除默认分支。
- 禁止 non-fast-forward 更新，避免 force push 改写主线历史。
- 要求 Pull Request 合入。
- 要求状态检查 `Compatibility Gate Result` 通过。

## 必需检查

`.github/workflows/agentops-cross-platform.yml` 提供 `Compatibility Gate Result` 聚合检查：

- 后端矩阵覆盖 Windows、Linux、macOS 与 Python 3.11/3.12。
- 前端矩阵覆盖 Windows、Linux、macOS 与 Node.js 22/24。
- 任一平台测试、构建或打包失败时，`Compatibility Gate Result` 必须失败。

## 操作约束

- 不直接向 `main` 推送功能变更。
- 不绕过 `Compatibility Gate Result` 宣称主线可合入。
- 若 ruleset、必需检查名或默认分支发生变化，必须同步更新本文档与相关契约测试。
