"""Upstream IAM/RBAC boundary for production-mode HTTP routes."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Mapping

from agentops.core.errors import AgentOpsError


ROLE_SCOPES = {
    "agentops-admin": {
        "console.snapshot.read",
        "credential.read",
        "credential.write",
        "event.ingest",
        "runtime.audit.export",
        "runtime.audit.read",
        "store.summary.read",
    },
    "agentops-operator": {
        "console.snapshot.read",
        "credential.read",
        "credential.write",
        "event.ingest",
        "runtime.audit.export",
        "runtime.audit.read",
        "store.summary.read",
    },
    "agentops-viewer": {
        "console.snapshot.read",
        "credential.read",
        "store.summary.read",
    },
    "agentops-ingestor": {
        "event.ingest",
    },
    "agent-store-consumer": {
        "store.summary.read",
    },
}


@dataclass(frozen=True, slots=True)
class UpstreamIdentity:
    principal: str
    roles: frozenset[str]
    scopes: frozenset[str]
    request_id: str
    audit_id: str

    def has_scope(self, required_scope: str) -> bool:
        if required_scope in self.scopes:
            return True
        return any(
            required_scope in ROLE_SCOPES.get(role, set()) for role in self.roles
        )


def parse_upstream_identity(headers: Mapping[str, str]) -> UpstreamIdentity | None:
    principal = _header(headers, "X-AgentOps-Principal").strip()
    if not principal:
        return None

    roles = frozenset(_split_header_values(_header(headers, "X-AgentOps-Roles")))
    scopes = frozenset(
        [
            *_split_header_values(_header(headers, "X-AgentOps-Scopes")),
            *_split_header_values(_header(headers, "X-AgentOps-Scope")),
        ]
    )
    request_id = _header(headers, "X-AgentOps-Request-Id").strip() or "req_upstream"
    audit_id = _header(headers, "X-AgentOps-Audit-Id").strip() or "audit_upstream"
    return UpstreamIdentity(
        principal=principal,
        roles=roles,
        scopes=scopes,
        request_id=request_id,
        audit_id=audit_id,
    )


def require_scope(
    headers: Mapping[str, str],
    required_scope: str,
    *,
    auth_required: bool,
) -> None:
    if not auth_required:
        return

    identity = parse_upstream_identity(headers)
    if identity is None:
        raise AgentOpsError(
            "UPSTREAM_IDENTITY_REQUIRED",
            "生产模式需要上游 IAM/RBAC 身份证明。",
            audit_id=_header(headers, "X-AgentOps-Audit-Id").strip()
            or "audit_missing_identity",
            request_id=_header(headers, "X-AgentOps-Request-Id").strip()
            or "req_missing_identity",
            denied_scope=required_scope,
        )

    if not identity.has_scope(required_scope):
        raise AgentOpsError(
            "AGENTOPS_SCOPE_DENIED",
            "上游身份缺少执行该 AgentOps API 的权限。",
            audit_id=identity.audit_id,
            request_id=identity.request_id,
            denied_scope=required_scope,
        )


def _header(headers: Mapping[str, str], name: str) -> str:
    value = headers.get(name, "")
    if value:
        return str(value)

    expected = name.lower()
    for candidate_name, candidate_value in headers.items():
        if str(candidate_name).lower() == expected:
            return str(candidate_value)
    return ""


def _split_header_values(value: str) -> list[str]:
    unique: list[str] = []
    seen: set[str] = set()
    for item in value.split(","):
        normalized = item.strip()
        if not normalized or normalized in seen:
            continue
        seen.add(normalized)
        unique.append(normalized)
    return unique
