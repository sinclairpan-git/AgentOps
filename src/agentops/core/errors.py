"""Shared API-style errors for contract tests."""

from dataclasses import dataclass


@dataclass(slots=True)
class AgentOpsError(Exception):
    error_code: str
    message: str
    retryable: bool = False
    audit_id: str | None = None
    request_id: str | None = None
    denied_scope: str | None = None

    def to_response(self) -> dict:
        response = {
            "error_code": self.error_code,
            "message": self.message,
            "retryable": self.retryable,
        }
        if self.audit_id:
            response["audit_id"] = self.audit_id
        if self.request_id:
            response["request_id"] = self.request_id
        if self.denied_scope:
            response["denied_scope"] = self.denied_scope
        return response
