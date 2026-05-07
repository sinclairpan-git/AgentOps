# 017 Plan

1. 增加 017 spec、tasks、执行日志与 development summary，明确 signed test event 只证明 Reporter 激活，不证明 `verified_loaded`。
2. 扩展 EventEnvelope payload 校验，冻结 `signature_test_event` 的最小 payload 字段。
3. 在 Ingestion 写入前校验 signed test event 与 Repository 中已签发 credential 的绑定。
4. 写入成功后更新 bootstrap session/credential echo 状态为 `signature_verified`。
5. 补充 AO17-CCT-004 合约测试和云端对抗 review 检查信号。
