from __future__ import annotations

from agentops.api.console_snapshot import build_console_snapshot
from agentops.storage.repository import InMemoryRepository
from tests.contract.conftest import base_event

REQUIRED_METRICS = {
    "generated_lines",
    "retained_lines",
    "human_modified_lines",
    "deleted_lines",
    "rework_rounds",
    "pr_review_findings",
    "ci_failure_types",
}
REQUIRED_CHAIN_KEYS = {
    "score_template_id",
    "evidence_level",
    "confidence",
    "missing_evidence",
    "explanation",
    "appeal_path",
}


def _repository() -> InMemoryRepository:
    repository = InMemoryRepository()
    repository.write_event(base_event("stage_started", agent_id="agent.quality", agent_version="1.0.0"))
    repository.write_event(base_event("stage_completed", agent_id="agent.quality", agent_version="1.0.0", sequence_no=2))
    return repository


def _contains_url_or_forbidden_key(value: object) -> bool:
    if isinstance(value, str):
        return "http://" in value or "https://" in value
    if isinstance(value, list | tuple):
        return any(_contains_url_or_forbidden_key(item) for item in value)
    if isinstance(value, dict):
        forbidden = {"raw_payload", "download_url", "raw_url", "original_url", "raw_access_url", "diff"}
        return bool(forbidden & set(value)) or any(_contains_url_or_forbidden_key(item) for item in value.values())
    return False


def test_ao11_ct_001_snapshot_contains_adoption_domain():
    adoption = build_console_snapshot(repository=_repository())["consoleData"]["adoption"]

    assert set(adoption) == {"metrics", "explanationChains", "segments", "reviewSignals", "guardrails"}
    assert REQUIRED_METRICS <= set(adoption["metrics"])
    assert adoption["explanationChains"]
    assert adoption["segments"]
    assert adoption["guardrails"]


def test_ao11_ct_002_metrics_are_summary_only_and_safe():
    adoption = build_console_snapshot(repository=_repository())["consoleData"]["adoption"]
    metrics = adoption["metrics"]

    for key in REQUIRED_METRICS - {"ci_failure_types"}:
        assert isinstance(metrics[key], int)
    assert isinstance(metrics["ci_failure_types"], list)
    assert "raw_payload" not in str(adoption)
    assert not _contains_url_or_forbidden_key(adoption)


def test_ao11_ct_003_explanation_chains_have_quality_contract_fields():
    chains = build_console_snapshot(repository=_repository())["consoleData"]["adoption"]["explanationChains"]

    for chain in chains:
        assert REQUIRED_CHAIN_KEYS <= set(chain)
        assert chain["score_template_id"].startswith("quality_summary_")
        assert chain["evidence_level"] in {"L5", "L3", "pending"}
        assert isinstance(chain["confidence"], float)
        assert isinstance(chain["missing_evidence"], list)
        assert "低置信不自动下架" in chain["lifecycle_guardrail"]
        assert "0 分" not in chain["explanation"]


def test_ao11_ct_004_review_signals_do_not_execute_lifecycle_actions():
    adoption = build_console_snapshot(repository=_repository())["consoleData"]["adoption"]
    combined_text = f"{adoption['reviewSignals']} {adoption['guardrails']}"

    assert "执行自动下架" not in combined_text
    assert "执行自动降推荐" not in combined_text
    assert "自动写回" not in combined_text
    assert "低置信不自动下架" in combined_text
