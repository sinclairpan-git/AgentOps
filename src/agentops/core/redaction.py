"""Redaction helpers for evidence and summaries."""

SENSITIVE_KEYS = {"raw_prompt", "raw_diff", "raw_logs", "secret", "token"}


def redact_payload(payload: dict) -> dict:
    return {
        key: ("[redacted]" if key in SENSITIVE_KEYS else value)
        for key, value in payload.items()
    }
