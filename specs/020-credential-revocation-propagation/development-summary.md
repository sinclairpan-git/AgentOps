# 开发摘要：020 Credential Revocation Propagation

## 交付内容

- 新增 AgentOps credential revocation API 和 HTTP route。
- 状态查询支持 revoked 回显和 `reissue_credential` 下一步动作。
- 签名测试事件和已知企业托管事件在 revoked 后被稳定阻断。
- Console 凭证联调工作台展示已撤销数量、撤销原因、撤销范围和重新签发建议。
- 补齐 AO20 契约测试、前端负例测试、OpenAPI 和云端对抗 review guard。

## 边界声明

- AgentOps 是 credential revocation 的事实源。
- Agent Store 只消费展示 `bootstrap_status`、`credential_status`、`next_action` 和撤销摘要。
- Console 不本地推导 active，不签发 credential，不把 revoked/signature_verified 提升为 `verified_loaded` 或 L5。

## 验证

- `uv run pytest tests -q`：通过。
- `uv run ruff check src tests`：通过。
- `npm test`：通过。
- `npm run build`：通过。
- `node scripts/agentops-pr-review.mjs --base origin/main --head HEAD`：未发现 P0/P1 阻断问题。
- `uv run ai-sdlc verify constraints`：no BLOCKERs。
- `uv run ai-sdlc program validate`：PASS，保留 `prd_path is empty` 非阻断提示。
- `uv run ai-sdlc program truth sync --execute --yes`：truth snapshot ready，100/100 mapped。
- `uv run ai-sdlc run --dry-run`：Stage close PASS。
- `uv run ai-sdlc workitem close-check --wi specs/020-credential-revocation-propagation --json`：提交前仅剩 git committed close-out 阻断，提交后复核。
