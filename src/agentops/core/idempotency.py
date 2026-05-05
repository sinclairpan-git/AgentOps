"""Idempotency helpers."""


def idempotency_fingerprint(event: dict) -> str:
    return str(event["idempotency_key"])
