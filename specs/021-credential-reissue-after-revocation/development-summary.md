# 开发摘要：021 Credential Reissue After Revocation

## 交付内容

- 新增 AgentOps credential reissue API 和 HTTP route。
- 状态查询支持 revoked source 的 reissue resolution 回显。
- 替代 credential 使用新的 bootstrap id、nonce、token 和 device key，下一步为 `send_signature_test_event`。
- 替代 credential id 和 token id 绑定新 bootstrap id，避免自定义 reissue bootstrap 复用旧 installation token。
- 签名测试可推进新 credential；旧 token 和随机 token 不得借 reissued identity 接入。
- Console 凭证联调工作台展示 reissued 计数和替代 credential 摘要。
- 补齐 AO21 契约测试和 OpenAPI。

## 边界声明

- AgentOps 是 credential reissue 的事实源。
- Agent Store 只消费展示 `bootstrap_status`、`credential_status`、`next_action`、reissue 摘要和替代 credential id。
- Console 不本地推导 active，不签发 credential，不展示 token 值，不把 reissued/signature_verified 提升为 `verified_loaded` 或 L5。

## 验证

- `uv run pytest tests/contract/test_ao21_ct_credential_reissue_after_revocation.py tests/contract/test_ao20_ct_credential_revocation_propagation.py tests/contract/test_ao17_ct_signed_test_event_activation.py -q`：通过。
- `uv run ruff check src tests`：通过。
- `uv run pytest tests -q`：通过。
- `npm test`：通过。
- `npm run build`：通过。
- `node scripts/agentops-pr-review.mjs --base origin/main --head HEAD`：未发现 P0/P1 阻断问题。
- `uv run ai-sdlc verify constraints`：no BLOCKERs。
- `uv run ai-sdlc program validate`：PASS，保留 `prd_path is empty` 非阻断提示。
- `uv run ai-sdlc run --dry-run`：Stage close PASS。
