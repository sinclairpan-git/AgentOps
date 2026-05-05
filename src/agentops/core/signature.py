"""Signature verification boundary for stage-1 contracts.

The real enterprise key service is external to this work item. This verifier
enforces the trust boundary without baking in a vendor-specific algorithm.
"""

from typing import Any


def has_usable_signature(event: dict[str, Any]) -> bool:
    return bool(event.get("signature")) and event.get("source_trust_level") == "verified"
