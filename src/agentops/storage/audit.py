"""Durable append-only audit log for production runtime boundaries."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import UTC, datetime
import json
from pathlib import Path
from threading import Lock
from typing import Any


@dataclass(frozen=True, slots=True)
class AuditRecord:
    audit_id: str
    request_id: str
    action: str
    outcome: str
    principal: str
    roles: tuple[str, ...] = field(default_factory=tuple)
    scopes: tuple[str, ...] = field(default_factory=tuple)
    resource: str = ""
    denied_scope: str = ""
    error_code: str = ""
    recorded_at: str = field(
        default_factory=lambda: datetime.now(UTC).isoformat().replace("+00:00", "Z")
    )

    def to_dict(self) -> dict[str, Any]:
        return {
            "audit_id": self.audit_id,
            "request_id": self.request_id,
            "action": self.action,
            "outcome": self.outcome,
            "principal": self.principal,
            "roles": list(self.roles),
            "scopes": list(self.scopes),
            "resource": self.resource,
            "denied_scope": self.denied_scope,
            "error_code": self.error_code,
            "recorded_at": self.recorded_at,
        }

    @classmethod
    def from_dict(cls, payload: dict[str, Any]) -> "AuditRecord":
        return cls(
            audit_id=str(payload.get("audit_id") or ""),
            request_id=str(payload.get("request_id") or ""),
            action=str(payload.get("action") or ""),
            outcome=str(payload.get("outcome") or ""),
            principal=str(payload.get("principal") or ""),
            roles=_string_tuple(payload.get("roles")),
            scopes=_string_tuple(payload.get("scopes")),
            resource=str(payload.get("resource") or ""),
            denied_scope=str(payload.get("denied_scope") or ""),
            error_code=str(payload.get("error_code") or ""),
            recorded_at=str(payload.get("recorded_at") or ""),
        )


class JsonlAuditLog:
    """Append-only JSONL audit adapter with stable readback semantics."""

    def __init__(self, path: str | Path) -> None:
        self.path = Path(path)
        self._lock = Lock()

    def append(self, record: AuditRecord) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        line = json.dumps(record.to_dict(), ensure_ascii=False, sort_keys=True)
        with self._lock, self.path.open("a", encoding="utf-8") as handle:
            handle.write(f"{line}\n")

    def records(self) -> list[AuditRecord]:
        if not self.path.exists():
            return []

        records: list[AuditRecord] = []
        with self.path.open(encoding="utf-8") as handle:
            for line in handle:
                stripped = line.strip()
                if not stripped:
                    continue
                payload = json.loads(stripped)
                if not isinstance(payload, dict):
                    continue
                records.append(AuditRecord.from_dict(payload))
        return records


def _string_tuple(value: Any) -> tuple[str, ...]:
    if not isinstance(value, list):
        return ()
    return tuple(str(item) for item in value if str(item))
