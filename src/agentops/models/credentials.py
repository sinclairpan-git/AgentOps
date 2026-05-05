"""Credential issue models."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class InstallationAssertion:
    issuer: str
    key_id: str
    algorithm: str
    canonicalization: str
    signature: str
    installation_id: str
    agent_id: str
    agent_version: str
    artifact_hash: str
    user_id: str
    device_id: str
    nonce: str
    issued_at: str
    expires_at: str


@dataclass(frozen=True)
class DeviceProof:
    device_id: str
    public_key_hash: str
    key_id: str
    algorithm: str
    nonce: str
    signature: str
    issued_at: str
    expires_at: str
