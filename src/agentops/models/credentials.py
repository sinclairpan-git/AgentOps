"""Credential issue models."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class InstallationAssertion:
    assertion_version: str
    issuer: str
    key_id: str
    algorithm: str
    canonicalization: str
    signature: str
    assertion_hash: str
    installation_id: str
    device_id: str
    device_public_key_thumbprint: str
    agent_id: str
    agent_version: str
    artifact_hash: str
    user_id: str
    audience: str
    nonce: str
    replay_window_seconds: int
    issued_at: str
    expires_at: str
    revocation_status: str


@dataclass(frozen=True)
class DeviceProof:
    proof_version: str
    installation_id: str
    device_id: str
    public_key_hash: str
    key_id: str
    algorithm: str
    canonicalization: str
    nonce: str
    assertion_hash: str
    signature: str
    issued_at: str
    expires_at: str
