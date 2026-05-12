# AI-SDLC（Codex / OpenAI Codex CLI 提示）

本工程使用 **AI-SDLC** 自动化流水线。

- 宪章：`.ai-sdlc/memory/constitution.md`
- **终端约定**：引导用户在已配置好的终端（venv 已激活、`ai-sdlc` 在 PATH）中执行；Codex 对话环境未必继承该 PATH。若裸命令不可用，使用 `python -m ai_sdlc ...`。
- 分阶段清单：`ai-sdlc stage show <阶段名>`
- 先检查接入真值：`ai-sdlc adapter status`
- 启动入口（先执行）：`ai-sdlc run --dry-run` 或 `python -m ai_sdlc run --dry-run`（安全预演；不证明治理激活）
- 全流程执行：`ai-sdlc run`

当前 Codex adapter 以 `AGENTS.md` 作为 canonical path。治理侧以 `materialized / verified_loaded / degraded / unsupported` 为准；只有存在 machine-verifiable 证据时，才可视为 `verified_loaded`。

当用户在聊天中输入任何需求/任务描述时，优先引导并先执行上述启动入口（两种写法择一，以用户终端能成功为准）。`run --dry-run` 通过后只表示 CLI 预演成功，再进入细化、分解与实现；它本身不构成治理激活证明。

请在修改 `specs/` 与 `.ai-sdlc/` 下文档时遵守上述入口。

## GitHub PR 收口固定规则

当一个功能分支已经提交并创建 GitHub PR 后，默认执行以下收口流程，无需用户每次重复说明：

1. 在 PR 中触发 `@codex review`。
2. 等待 GitHub checks 全部完成，且必须包含 `Compatibility Gate Result` 通过。
3. 若 Codex review 反馈具体问题，回到当前分支修复、提交、推送，并重新触发 `@codex review`。
4. 若 Codex review 配额不足、无法触发、长时间不可用或没有返回可执行结论，则每次创建 PR 后都必须启动一个单独的云端 review 任务作为 fallback。该任务必须保持独立、客观、严谨，使用与 Codex review 相同的 review 规则和阻断标准，对 PR diff、测试、治理证据、兼容门和安全边界进行 review，并将具体问题评论到 PR。
5. 云端 fallback review 若反馈具体问题，回到当前分支修复、提交、推送，并再次触发云端 fallback review；若 Codex review 配额恢复，也同时重新触发 `@codex review`。
6. 只有 Codex review 或云端 fallback review 明确“未发现问题”或等价通过，且所有 GitHub checks 均通过、`Compatibility Gate Result` 通过、`mergeStateStatus=CLEAN`，才可合入 `main` 并同步本地 `main`。
7. PR 创建并触发 `@codex review` 或云端 fallback review 后，Codex 必须主动创建或确认存在 5 分钟轮询 heartbeat，不等待用户再次要求。heartbeat 任务需检查 Codex review 或云端 fallback review、GitHub checks、`Compatibility Gate Result` 和 `mergeStateStatus`。
8. 若 review 或 checks 未完成，继续维持 5 分钟轮询；轮询发现问题则修复、提交、推送并重新触发对应 review；发现满足合入条件则合入主线并同步本地 `main`。

该规则适用于 AgentOps 项目的常规功能 PR；若用户明确要求暂停、仅观察、不得自动合入或改用其他分支策略，则以用户最新指令为准。

（自动安装；不覆盖已有同名自定义文件。）

<!-- AI-SDLC managed shell guidance -->
Project preferred shell: zsh.
Use zsh POSIX shell syntax for commands and environment variables. Do not start with PowerShell or cmd.exe syntax.
