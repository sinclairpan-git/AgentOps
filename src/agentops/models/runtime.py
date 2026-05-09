"""Runtime governance contract models."""

from __future__ import annotations

from dataclasses import dataclass, replace
from typing import Any


@dataclass(frozen=True, slots=True)
class ContractRegistryEntry:
    contract_id: str
    domain_owner: str
    producer: str
    consumers: tuple[str, ...]
    schema_version: str
    required_fields: frozenset[str]
    optional_fields: frozenset[str]
    enum_fields: dict[str, frozenset[str]]
    state_registry_refs: tuple[str, ...]
    error_codes: tuple[str, ...]
    contract_tests: tuple[str, ...]
    compatibility_policy: str

    def with_changes(self, **changes: Any) -> "ContractRegistryEntry":
        return replace(self, **changes)

    def to_stable_dict(self) -> dict[str, Any]:
        return {
            "compatibility_policy": self.compatibility_policy,
            "consumers": sorted(self.consumers),
            "contract_id": self.contract_id,
            "contract_tests": sorted(self.contract_tests),
            "domain_owner": self.domain_owner,
            "enum_fields": {
                key: sorted(values) for key, values in sorted(self.enum_fields.items())
            },
            "error_codes": sorted(self.error_codes),
            "optional_fields": sorted(self.optional_fields),
            "producer": self.producer,
            "required_fields": sorted(self.required_fields),
            "schema_version": self.schema_version,
            "state_registry_refs": sorted(self.state_registry_refs),
        }


@dataclass(frozen=True, slots=True)
class StateRegistryEntry:
    machine_value: str
    display_name: str
    plain_language_explanation: str
    severity: str
    primary_action: str
    secondary_action: str | None
    terminal_state: bool
    allowed_next_states: tuple[str, ...]
    audit_required: bool
    owner: str
    expected_display_name: str | None = None

    def with_changes(self, **changes: Any) -> "StateRegistryEntry":
        return replace(self, **changes)

    def to_stable_dict(self) -> dict[str, Any]:
        return {
            "allowed_next_states": sorted(self.allowed_next_states),
            "audit_required": self.audit_required,
            "display_name": self.display_name,
            "expected_display_name": self.expected_display_name,
            "machine_value": self.machine_value,
            "owner": self.owner,
            "plain_language_explanation": self.plain_language_explanation,
            "primary_action": self.primary_action,
            "secondary_action": self.secondary_action,
            "severity": self.severity,
            "terminal_state": self.terminal_state,
        }


@dataclass(frozen=True, slots=True)
class ErrorCodeDefinition:
    error_code: str
    http_status: int
    retryable: bool
    user_message: str
    developer_message: str
    audit_required: bool

    def to_stable_dict(self) -> dict[str, Any]:
        return {
            "audit_required": self.audit_required,
            "developer_message": self.developer_message,
            "error_code": self.error_code,
            "http_status": self.http_status,
            "retryable": self.retryable,
            "user_message": self.user_message,
        }
