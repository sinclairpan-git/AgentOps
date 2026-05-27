"""AgentOps access readiness probe for local and managed deployments."""

from __future__ import annotations

import argparse
import json
import sys
from dataclasses import dataclass
from http import HTTPStatus
from pathlib import Path
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.parse import urljoin
from urllib.request import Request, urlopen


DEFAULT_API_BASE = "http://127.0.0.1:8765"
DEFAULT_GATEWAY_BASE = "http://127.0.0.1:8766"
DEFAULT_TOKEN_ENV = "AGENTOPS_INGESTION_TOKEN"
DEFAULT_BAD_TOKEN = "agentops-readiness-invalid-token"
DEFAULT_TIMEOUT_SECONDS = 10.0
READINESS_SCHEMA_VERSION = "agentops_access_readiness.v1"


@dataclass(frozen=True)
class AccessReadinessConfig:
    gateway_base: str = DEFAULT_GATEWAY_BASE
    api_base: str | None = DEFAULT_API_BASE
    token: str = ""
    fixture_path: Path | None = None
    bad_token: str = DEFAULT_BAD_TOKEN
    timeout_seconds: float = DEFAULT_TIMEOUT_SECONDS
    skip_api_readback: bool = False
    skip_negative_raw_api: bool = False
    skip_gateway_route_allowlist: bool = False


@dataclass(frozen=True)
class HttpJsonResponse:
    status_code: int
    payload: dict[str, Any]
    raw_body: str


def default_fixture_path() -> Path:
    return (
        Path(__file__).resolve().parents[3]
        / "contracts"
        / "cross-project"
        / "fixtures"
        / "ai_sdlc_executable_task_runtime_batch.v1.json"
    )


def run_access_readiness(config: AccessReadinessConfig) -> dict[str, Any]:
    checks: list[dict[str, Any]] = []
    fixture_path = config.fixture_path or default_fixture_path()
    fixture = _read_fixture(fixture_path)
    run_id = _fixture_run_id(fixture)

    _append_check(
        checks,
        "fixture.load",
        fixture is not None,
        detail={
            "fixture": str(fixture_path),
            "run_id": run_id,
        },
        error_code="" if fixture is not None else "FIXTURE_UNAVAILABLE",
    )

    gateway_health = _request_json(
        "GET",
        config.gateway_base,
        "/v1/health",
        timeout_seconds=config.timeout_seconds,
    )
    _append_check(
        checks,
        "gateway.health",
        gateway_health.status_code == HTTPStatus.OK
        and gateway_health.payload.get("status") == "healthy",
        status_code=gateway_health.status_code,
        error_code=gateway_health.payload.get("error_code", ""),
        detail={"service": gateway_health.payload.get("service", "")},
    )

    if config.api_base:
        api_health = _request_json(
            "GET",
            config.api_base,
            "/v1/health",
            timeout_seconds=config.timeout_seconds,
        )
        _append_check(
            checks,
            "api.health",
            api_health.status_code == HTTPStatus.OK
            and api_health.payload.get("status") == "healthy",
            status_code=api_health.status_code,
            error_code=api_health.payload.get("error_code", ""),
            detail={"service": api_health.payload.get("service", "")},
        )

    if not config.token:
        _append_check(
            checks,
            "configuration.token",
            False,
            error_code="AGENTOPS_INGESTION_TOKEN_REQUIRED",
        )
        return _readiness_result(config, checks)

    if fixture is None:
        return _readiness_result(config, checks)

    positive_response = _request_json(
        "POST",
        config.gateway_base,
        "/v1/runtime/events",
        headers={
            "Authorization": f"Bearer {config.token}",
            "Content-Type": "application/json",
        },
        payload=fixture,
        timeout_seconds=config.timeout_seconds,
    )
    receipt = positive_response.payload
    receipt_passed = (
        positive_response.status_code == HTTPStatus.ACCEPTED
        and receipt.get("schema_version") == "runtime_outbox_receipt.v1"
        and receipt.get("producer") == "Ai_AutoSDLC"
        and int(receipt.get("accepted_count", 0))
        + int(receipt.get("deduplicated_count", 0))
        > 0
        and int(receipt.get("rejected_count", 0)) == 0
        and int(receipt.get("dlq_count", 0)) == 0
    )
    _append_check(
        checks,
        "gateway.runtime_ingestion",
        receipt_passed,
        status_code=positive_response.status_code,
        error_code=receipt.get("error_code", ""),
        detail={
            "receipt": _receipt_summary(receipt),
        },
    )

    if config.api_base and not config.skip_api_readback and run_id:
        trace = _request_json(
            "GET",
            config.api_base,
            f"/v1/runtime/runs/{run_id}/trace",
            headers=_operator_read_headers(),
            timeout_seconds=config.timeout_seconds,
        )
        span_count = _nested_int(trace.payload, ("aggregate", "span_count"))
        _append_check(
            checks,
            "api.trace_readback",
            trace.status_code == HTTPStatus.OK and span_count > 0,
            status_code=trace.status_code,
            error_code=trace.payload.get("error_code", ""),
            detail={"run_id": run_id, "span_count": span_count},
        )

        evidence = _request_json(
            "GET",
            config.api_base,
            f"/v1/runtime/runs/{run_id}/evidence-summary",
            headers=_operator_read_headers(),
            timeout_seconds=config.timeout_seconds,
        )
        _append_check(
            checks,
            "api.evidence_readback",
            evidence.status_code == HTTPStatus.OK
            and evidence.payload.get("raw_access_state") == "summary_only",
            status_code=evidence.status_code,
            error_code=evidence.payload.get("error_code", ""),
            detail={
                "run_id": run_id,
                "evidence_level": evidence.payload.get("evidence_level", ""),
                "raw_access_state": evidence.payload.get("raw_access_state", ""),
            },
        )

    bad_token = _request_json(
        "POST",
        config.gateway_base,
        "/v1/runtime/events",
        headers={
            "Authorization": f"Bearer {config.bad_token}",
            "Content-Type": "application/json",
        },
        payload=fixture,
        timeout_seconds=config.timeout_seconds,
    )
    _append_check(
        checks,
        "gateway.bad_token_rejected",
        bad_token.status_code == HTTPStatus.UNAUTHORIZED
        and bad_token.payload.get("error_code") == "GATEWAY_TOKEN_INVALID",
        status_code=bad_token.status_code,
        error_code=bad_token.payload.get("error_code", ""),
    )

    if config.api_base and not config.skip_negative_raw_api:
        raw_api = _request_json(
            "POST",
            config.api_base,
            "/v1/runtime/events",
            headers={
                "Authorization": "Bearer agentops-readiness-probe",
                "Content-Type": "application/json",
            },
            payload=fixture,
            timeout_seconds=config.timeout_seconds,
        )
        _append_check(
            checks,
            "api.raw_ingestion_rejected",
            raw_api.status_code == HTTPStatus.UNAUTHORIZED
            and raw_api.payload.get("error_code") == "UPSTREAM_IDENTITY_REQUIRED",
            status_code=raw_api.status_code,
            error_code=raw_api.payload.get("error_code", ""),
        )

    if not config.skip_gateway_route_allowlist:
        route_allowlist = _request_json(
            "POST",
            config.gateway_base,
            "/v1/events",
            headers={
                "Authorization": f"Bearer {config.token}",
                "Content-Type": "application/json",
            },
            payload=fixture,
            timeout_seconds=config.timeout_seconds,
        )
        _append_check(
            checks,
            "gateway.route_allowlist_closed",
            route_allowlist.status_code == HTTPStatus.NOT_FOUND
            and route_allowlist.payload.get("error_code") == "GATEWAY_ROUTE_NOT_FOUND",
            status_code=route_allowlist.status_code,
            error_code=route_allowlist.payload.get("error_code", ""),
        )

    return _readiness_result(config, checks)


def main(argv: list[str] | None = None) -> int:
    args = _parse_args(argv)
    token = args.token or _token_from_env(args.token_env)
    config = AccessReadinessConfig(
        gateway_base=args.gateway_base,
        api_base=None if args.no_api_base else args.api_base,
        token=token,
        fixture_path=Path(args.fixture) if args.fixture else None,
        bad_token=args.bad_token,
        timeout_seconds=args.timeout,
        skip_api_readback=args.skip_api_readback,
        skip_negative_raw_api=args.skip_negative_raw_api,
        skip_gateway_route_allowlist=args.skip_gateway_route_allowlist,
    )
    result = run_access_readiness(config)
    if args.json:
        print(json.dumps(result, ensure_ascii=False, indent=2, sort_keys=True))
    else:
        _print_text_summary(result)
    return 0 if result["overall"] == "pass" else 1


def _parse_args(argv: list[str] | None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Verify AgentOps Gateway/API access readiness for SDLC ingestion."
    )
    parser.add_argument("--gateway-base", default=DEFAULT_GATEWAY_BASE)
    parser.add_argument("--api-base", default=DEFAULT_API_BASE)
    parser.add_argument("--no-api-base", action="store_true")
    parser.add_argument("--token", default="")
    parser.add_argument("--token-env", default=DEFAULT_TOKEN_ENV)
    parser.add_argument("--fixture", default="")
    parser.add_argument("--bad-token", default=DEFAULT_BAD_TOKEN)
    parser.add_argument("--timeout", type=float, default=DEFAULT_TIMEOUT_SECONDS)
    parser.add_argument("--skip-api-readback", action="store_true")
    parser.add_argument("--skip-negative-raw-api", action="store_true")
    parser.add_argument("--skip-gateway-route-allowlist", action="store_true")
    parser.add_argument("--json", action="store_true")
    return parser.parse_args(argv)


def _request_json(
    method: str,
    base_url: str,
    path: str,
    *,
    headers: dict[str, str] | None = None,
    payload: dict[str, Any] | None = None,
    timeout_seconds: float = DEFAULT_TIMEOUT_SECONDS,
) -> HttpJsonResponse:
    body = json.dumps(payload).encode("utf-8") if payload is not None else None
    request = Request(
        urljoin(base_url.rstrip("/") + "/", path.lstrip("/")),
        data=body,
        headers=headers or {},
        method=method,
    )
    try:
        with urlopen(request, timeout=timeout_seconds) as response:
            raw_body = response.read().decode("utf-8")
            return HttpJsonResponse(response.status, _json_body(raw_body), raw_body)
    except HTTPError as exc:
        raw_body = exc.read().decode("utf-8")
        return HttpJsonResponse(exc.code, _json_body(raw_body), raw_body)
    except (TimeoutError, URLError) as exc:
        return HttpJsonResponse(
            0,
            {
                "error_code": "TRANSPORT_ERROR",
                "message": str(exc),
            },
            "",
        )


def _read_fixture(fixture_path: Path) -> dict[str, Any] | None:
    try:
        return json.loads(fixture_path.read_text(encoding="utf-8"))
    except (FileNotFoundError, json.JSONDecodeError):
        return None


def _fixture_run_id(fixture: dict[str, Any] | None) -> str:
    if not fixture:
        return ""
    events = fixture.get("events")
    if not isinstance(events, list) or not events:
        return ""
    first = events[0]
    if not isinstance(first, dict):
        return ""
    payload = first.get("payload")
    if isinstance(payload, dict) and isinstance(payload.get("run_id"), str):
        return payload["run_id"]
    return first.get("run_id", "") if isinstance(first.get("run_id"), str) else ""


def _receipt_summary(receipt: dict[str, Any]) -> dict[str, Any]:
    return {
        "schema_version": receipt.get("schema_version", ""),
        "producer": receipt.get("producer", ""),
        "accepted_count": receipt.get("accepted_count", 0),
        "deduplicated_count": receipt.get("deduplicated_count", 0),
        "stale_count": receipt.get("stale_count", 0),
        "rejected_count": receipt.get("rejected_count", 0),
        "dlq_count": receipt.get("dlq_count", 0),
        "audit_id_present": bool(receipt.get("audit_id")),
    }


def _append_check(
    checks: list[dict[str, Any]],
    name: str,
    passed: bool,
    *,
    status_code: int | HTTPStatus | None = None,
    error_code: str = "",
    detail: dict[str, Any] | None = None,
) -> None:
    check: dict[str, Any] = {
        "name": name,
        "passed": passed,
    }
    if status_code is not None:
        check["status_code"] = int(status_code)
    if error_code:
        check["error_code"] = error_code
    if detail:
        check["detail"] = detail
    checks.append(check)


def _readiness_result(
    config: AccessReadinessConfig,
    checks: list[dict[str, Any]],
) -> dict[str, Any]:
    passed = all(check["passed"] for check in checks)
    return {
        "schema_version": READINESS_SCHEMA_VERSION,
        "overall": "pass" if passed else "fail",
        "gateway_base": config.gateway_base,
        "api_base": config.api_base or "",
        "checks": checks,
    }


def _json_body(raw_body: str) -> dict[str, Any]:
    if not raw_body:
        return {}
    try:
        parsed = json.loads(raw_body)
    except json.JSONDecodeError:
        return {"error_code": "RESPONSE_JSON_INVALID", "message": raw_body[:200]}
    return parsed if isinstance(parsed, dict) else {"value": parsed}


def _operator_read_headers() -> dict[str, str]:
    return {
        "X-AgentOps-Principal": "ops.readiness",
        "X-AgentOps-Roles": "agentops-operator",
        "X-AgentOps-Request-Id": "req_agentops_readiness",
        "X-AgentOps-Audit-Id": "audit_agentops_readiness",
    }


def _nested_int(payload: dict[str, Any], path: tuple[str, ...]) -> int:
    current: Any = payload
    for key in path:
        if not isinstance(current, dict):
            return 0
        current = current.get(key)
    return int(current) if isinstance(current, int) else 0


def _token_from_env(token_env: str) -> str:
    import os

    return os.environ.get(token_env, "")


def _print_text_summary(result: dict[str, Any]) -> None:
    print(f"AgentOps access readiness: {result['overall']}")
    print(f"Gateway: {result['gateway_base']}")
    if result.get("api_base"):
        print(f"API: {result['api_base']}")
    for check in result["checks"]:
        marker = "PASS" if check["passed"] else "FAIL"
        suffix = ""
        if check.get("status_code") is not None:
            suffix += f" status={check['status_code']}"
        if check.get("error_code"):
            suffix += f" error={check['error_code']}"
        print(f"- {marker} {check['name']}{suffix}")


if __name__ == "__main__":
    sys.exit(main())
