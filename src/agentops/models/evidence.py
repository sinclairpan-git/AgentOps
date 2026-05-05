"""Evidence and Store summary models."""

from dataclasses import dataclass


@dataclass(frozen=True)
class DeepLinks:
    agent_id: str
    version: str
    session_id: str
    run_id: str
    installation_id: str
    trace_id: str
    audit_id: str
    return_url: str
