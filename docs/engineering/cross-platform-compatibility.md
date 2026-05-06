# AgentOps 跨平台工程约束

AgentOps 的跨平台兼容性必须由目标平台证据证明，而不是由当前开发机推断。仓库级 GitHub Actions 是工程实现层配置，不属于 AI-SDLC 框架通用规则。

## 目标平台

- Windows：`windows-latest`
- Linux：`ubuntu-latest`
- macOS：`macos-latest`

## 运行时矩阵

- Python：`3.11` 与 `3.12`
- Node.js：`22` 与 `24`
- 后端验证：`uv sync --locked`、`uv run ruff check src tests`、`uv run pytest tests -q`
- 后端云端打包：在每个 OS/Python runner 上执行 `uv build --sdist --wheel --out-dir dist/python`，上传 `agentops-python-<os>-py<version>` artifact
- 前端验证：在 `apps/agentops-console` 下执行 `npm ci --audit=false`、`npm test`、`npm run build`
- 前端云端打包：在每个 OS/Node runner 上上传 `apps/agentops-console/dist/**` 为 `agentops-console-<os>-node<version>` artifact

## 约束

- 不得用本机 macOS、Windows 或 Linux 成功结果替代其他目标平台证据。
- Python 代码优先使用标准库跨平台 API，例如 `pathlib`，避免硬编码 `/`、`\`、盘符、shell 特有语法。
- 前端依赖必须保持 `package-lock.json` 可重复安装；企业 Vue2 组件库依赖必须继续使用 `vendor/enterprise-vue2/*.tgz` 与 `file:` 引用。
- `node_modules/`、`dist/`、`.venv/`、`.pytest_cache/` 不进入 Git。
- GitHub Actions 不运行外部 `npm audit`，且前端安装使用 `npm ci --audit=false`，避免默认向外部服务提交私有依赖清单；安全审计应在被授权的企业环境内执行。
- `ai-sdlc run --dry-run` 成功只表示安全预演可运行，不构成 `verified_loaded` 治理激活证明。

## 证据边界

`.github/workflows/agentops-cross-platform.yml` 是当前仓库的跨平台工程门禁：

- 后端 job 覆盖 Windows/Linux/macOS 与 Python 3.11/3.12。
- 前端 job 覆盖 Windows/Linux/macOS 与 Node 22/24。
- 每个后端矩阵项必须上传独立 Python package artifact。
- 每个前端矩阵项必须上传独立 Console package artifact。
- `compatibility-result` 汇总矩阵结果，任何目标平台测试或打包失败都不得宣称三端兼容。

本地验证可以发现问题，但不能替代 GitHub Actions 的目标平台证据。
