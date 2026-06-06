"""Reference API Gateway for AgentOps runtime smoke deployments."""

from __future__ import annotations

import argparse
import json
import os
import socket
import time
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from threading import Lock
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.parse import urljoin
from urllib.request import Request, urlopen
from uuid import uuid4


DEFAULT_UPSTREAM_BASE = "http://127.0.0.1:8765"
TOKEN_ENV = "AGENTOPS_GATEWAY_TOKEN"
UPSTREAM_ENV = "AGENTOPS_UPSTREAM_BASE"
PRINCIPAL_ENV = "AGENTOPS_GATEWAY_PRINCIPAL"
ROLES_ENV = "AGENTOPS_GATEWAY_ROLES"
SCOPES_ENV = "AGENTOPS_GATEWAY_SCOPES"
REVOKED_TOKENS_ENV = "AGENTOPS_GATEWAY_REVOKED_TOKENS"
MAX_BODY_BYTES_ENV = "AGENTOPS_GATEWAY_MAX_BODY_BYTES"
UPSTREAM_TIMEOUT_SECONDS_ENV = "AGENTOPS_GATEWAY_UPSTREAM_TIMEOUT_SECONDS"
RATE_LIMIT_PER_MINUTE_ENV = "AGENTOPS_GATEWAY_RATE_LIMIT_PER_MINUTE"
AUDIT_LOG_ENV = "AGENTOPS_GATEWAY_AUDIT_LOG"

DEFAULT_MAX_BODY_BYTES = 1_048_576
DEFAULT_UPSTREAM_TIMEOUT_SECONDS = 10.0
DEFAULT_RATE_LIMIT_PER_MINUTE = 600


def create_gateway_handler(
    *,
    upstream_base: str = DEFAULT_UPSTREAM_BASE,
    token: str | None = None,
    principal: str = "producer.ai-sdlc.gateway",
    roles: str = "agentops-ingestor",
    scopes: str = "event.ingest",
    revoked_tokens: set[str] | None = None,
    max_body_bytes: int = DEFAULT_MAX_BODY_BYTES,
    upstream_timeout_seconds: float = DEFAULT_UPSTREAM_TIMEOUT_SECONDS,
    rate_limit_per_minute: int = DEFAULT_RATE_LIMIT_PER_MINUTE,
    audit_log_path: str | None = None,
) -> type[BaseHTTPRequestHandler]:
    expected_token = token or ""
    normalized_upstream = upstream_base.rstrip("/") + "/"
    blocked_tokens = revoked_tokens or set()
    rate_limit_lock = Lock()
    audit_lock = Lock()
    rate_windows: dict[str, tuple[float, int]] = {}
    audit_path = Path(audit_log_path) if audit_log_path else None

    class AgentOpsGatewayHandler(BaseHTTPRequestHandler):
        server_version = "AgentOpsGateway/0.1"

        def do_GET(self) -> None:  # noqa: N802
            if self.path == "/v1/health":
                self._send_json(
                    HTTPStatus.OK,
                    {
                        "service": "agentops-runtime-gateway",
                        "status": "healthy",
                        "upstream_base": normalized_upstream.rstrip("/"),
                    },
                )
                return
            if self.path == "/v1/console/snapshot":
                self._forward_agentops_request(
                    method="GET",
                    upstream_path="v1/console/snapshot",
                    raw_body=None,
                    roles="agentops-operator",
                    scopes="console.snapshot.read,runtime.run.read,runtime.trace.read",
                )
                return
            self._send_json(
                HTTPStatus.NOT_FOUND,
                {"error_code": "GATEWAY_ROUTE_NOT_FOUND", "message": "Unknown route."},
            )

        def do_POST(self) -> None:  # noqa: N802
            if self.path != "/v1/runtime/events":
                self._send_json(
                    HTTPStatus.NOT_FOUND,
                    {
                        "error_code": "GATEWAY_ROUTE_NOT_FOUND",
                        "message": "Unknown route.",
                    },
                )
                return
            request_id = (
                self.headers.get("X-Request-Id") or f"req_gateway_{uuid4().hex}"
            )
            audit_id = f"audit_gateway_{uuid4().hex}"
            if not expected_token:
                self._audit(
                    request_id=request_id,
                    audit_id=audit_id,
                    outcome="rejected",
                    error_code="GATEWAY_TOKEN_NOT_CONFIGURED",
                    status_code=int(HTTPStatus.SERVICE_UNAVAILABLE),
                )
                self._send_json(
                    HTTPStatus.SERVICE_UNAVAILABLE,
                    {
                        "error_code": "GATEWAY_TOKEN_NOT_CONFIGURED",
                        "message": "Gateway Bearer token is not configured.",
                    },
                )
                return
            bearer_token = self._bearer_token()
            if bearer_token in blocked_tokens:
                self._audit(
                    request_id=request_id,
                    audit_id=audit_id,
                    outcome="denied",
                    error_code="GATEWAY_TOKEN_REVOKED",
                    status_code=int(HTTPStatus.UNAUTHORIZED),
                )
                self._send_json(
                    HTTPStatus.UNAUTHORIZED,
                    {
                        "error_code": "GATEWAY_TOKEN_REVOKED",
                        "message": "Gateway Bearer token has been revoked.",
                    },
                )
                return
            if bearer_token != expected_token:
                self._audit(
                    request_id=request_id,
                    audit_id=audit_id,
                    outcome="denied",
                    error_code="GATEWAY_TOKEN_INVALID",
                    status_code=int(HTTPStatus.UNAUTHORIZED),
                )
                self._send_json(
                    HTTPStatus.UNAUTHORIZED,
                    {
                        "error_code": "GATEWAY_TOKEN_INVALID",
                        "message": "Gateway Bearer token is invalid.",
                    },
                )
                return
            allowed, retry_after = self._rate_limit_allowed(bearer_token)
            if not allowed:
                self._audit(
                    request_id=request_id,
                    audit_id=audit_id,
                    outcome="denied",
                    error_code="GATEWAY_RATE_LIMITED",
                    status_code=int(HTTPStatus.TOO_MANY_REQUESTS),
                )
                self._send_json(
                    HTTPStatus.TOO_MANY_REQUESTS,
                    {
                        "error_code": "GATEWAY_RATE_LIMITED",
                        "message": "Gateway producer rate limit exceeded.",
                        "retry_after_seconds": retry_after,
                    },
                )
                return
            content_length = _content_length(self.headers)
            if content_length > max_body_bytes:
                self._audit(
                    request_id=request_id,
                    audit_id=audit_id,
                    outcome="rejected",
                    error_code="GATEWAY_REQUEST_TOO_LARGE",
                    status_code=int(HTTPStatus.REQUEST_ENTITY_TOO_LARGE),
                    content_length=content_length,
                )
                self._send_json(
                    HTTPStatus.REQUEST_ENTITY_TOO_LARGE,
                    {
                        "error_code": "GATEWAY_REQUEST_TOO_LARGE",
                        "message": "Gateway request body exceeds the configured limit.",
                        "max_body_bytes": max_body_bytes,
                    },
                )
                return
            raw_body = self.rfile.read(content_length)
            self._forward_agentops_request(
                method="POST",
                upstream_path="v1/runtime/events",
                raw_body=raw_body,
                roles=roles,
                scopes=scopes,
                request_id=request_id,
                audit_id=audit_id,
            )

        def _forward_agentops_request(
            self,
            *,
            method: str,
            upstream_path: str,
            raw_body: bytes | None,
            roles: str,
            scopes: str,
            request_id: str | None = None,
            audit_id: str | None = None,
        ) -> None:
            request_id = (
                request_id
                or self.headers.get("X-Request-Id")
                or f"req_gateway_{uuid4().hex}"
            )
            audit_id = audit_id or f"audit_gateway_{uuid4().hex}"
            headers = {
                "Content-Type": self.headers.get("Content-Type", "application/json"),
                "X-AgentOps-Principal": principal,
                "X-AgentOps-Roles": roles,
                "X-AgentOps-Scopes": scopes,
                "X-AgentOps-Request-Id": request_id,
                "X-AgentOps-Audit-Id": audit_id,
            }
            request = Request(
                urljoin(normalized_upstream, upstream_path),
                data=raw_body,
                headers=headers,
                method=method,
            )
            try:
                with urlopen(request, timeout=upstream_timeout_seconds) as response:
                    body = response.read()
                    self._audit(
                        request_id=request_id,
                        audit_id=audit_id,
                        outcome="accepted",
                        status_code=response.status,
                    )
                    self._send_raw(
                        response.status, response.headers.get("Content-Type"), body
                    )
            except HTTPError as exc:
                body = exc.read()
                self._audit(
                    request_id=request_id,
                    audit_id=audit_id,
                    outcome="rejected" if exc.code >= 400 else "accepted",
                    status_code=exc.code,
                )
                self._send_raw(exc.code, exc.headers.get("Content-Type"), body)
            except (URLError, TimeoutError, socket.timeout):
                self._audit(
                    request_id=request_id,
                    audit_id=audit_id,
                    outcome="rejected",
                    error_code="AGENTOPS_UPSTREAM_UNAVAILABLE",
                    status_code=int(HTTPStatus.BAD_GATEWAY),
                )
                self._send_json(
                    HTTPStatus.BAD_GATEWAY,
                    {
                        "error_code": "AGENTOPS_UPSTREAM_UNAVAILABLE",
                        "message": "AgentOps upstream is unavailable.",
                    },
                )

        def _rate_limit_allowed(self, bearer_token: str) -> tuple[bool, int]:
            if rate_limit_per_minute <= 0:
                return True, 0
            now = time.monotonic()
            window_seconds = 60.0
            with rate_limit_lock:
                window_start, count = rate_windows.get(bearer_token, (now, 0))
                if now - window_start >= window_seconds:
                    rate_windows[bearer_token] = (now, 1)
                    return True, 0
                if count >= rate_limit_per_minute:
                    retry_after = max(1, int(window_seconds - (now - window_start)))
                    return False, retry_after
                rate_windows[bearer_token] = (window_start, count + 1)
                return True, 0

        def _bearer_token(self) -> str:
            value = self.headers.get("Authorization", "")
            prefix = "Bearer "
            if not value.startswith(prefix):
                return ""
            return value[len(prefix) :].strip()

        def _audit(
            self,
            *,
            request_id: str,
            audit_id: str,
            outcome: str,
            status_code: int,
            error_code: str | None = None,
            content_length: int | None = None,
        ) -> None:
            if audit_path is None:
                return
            record = {
                "schema_version": "agentops_gateway_audit.v1",
                "timestamp": _utc_timestamp(),
                "request_id": request_id,
                "audit_id": audit_id,
                "method": self.command,
                "route": self.path.split("?", 1)[0],
                "producer_principal": principal,
                "outcome": outcome,
                "status_code": status_code,
                "error_code": error_code or "",
                "inbound_identity_stripped": _has_agentops_identity_headers(
                    self.headers
                ),
                "content_length": content_length
                if content_length is not None
                else _content_length(self.headers),
            }
            audit_path.parent.mkdir(parents=True, exist_ok=True)
            with audit_lock:
                with audit_path.open("a", encoding="utf-8") as handle:
                    handle.write(json.dumps(record, ensure_ascii=False, sort_keys=True))
                    handle.write("\n")

        def _send_json(self, status: HTTPStatus, payload: dict[str, Any]) -> None:
            self._send_raw(
                int(status),
                "application/json; charset=utf-8",
                json.dumps(payload, ensure_ascii=False, sort_keys=True).encode("utf-8"),
            )

        def _send_raw(self, status: int, content_type: str | None, body: bytes) -> None:
            self.send_response(status)
            self.send_header("Content-Type", content_type or "application/json")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)

        def log_message(self, format: str, *args: Any) -> None:  # noqa: A002
            return

    return AgentOpsGatewayHandler


def _content_length(headers: Any) -> int:
    try:
        return max(0, int(headers.get("Content-Length", "0")))
    except ValueError:
        return 0


def _has_agentops_identity_headers(headers: Any) -> bool:
    return any(str(name).lower().startswith("x-agentops-") for name in headers.keys())


def _utc_timestamp() -> str:
    return time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())


def _split_csv(value: str) -> list[str]:
    return [item.strip() for item in value.split(",") if item.strip()]


def _int_env(name: str, default: int) -> int:
    try:
        return int(os.getenv(name, str(default)))
    except ValueError:
        return default


def _float_env(name: str, default: float) -> float:
    try:
        return float(os.getenv(name, str(default)))
    except ValueError:
        return default


def run_gateway(host: str, port: int) -> None:
    token = os.getenv(TOKEN_ENV, "")
    upstream_base = os.getenv(UPSTREAM_ENV, DEFAULT_UPSTREAM_BASE)
    principal = os.getenv(PRINCIPAL_ENV, "producer.ai-sdlc.gateway")
    roles = os.getenv(ROLES_ENV, "agentops-ingestor")
    scopes = os.getenv(SCOPES_ENV, "event.ingest")
    revoked_tokens = _split_csv(os.getenv(REVOKED_TOKENS_ENV, ""))
    max_body_bytes = _int_env(MAX_BODY_BYTES_ENV, DEFAULT_MAX_BODY_BYTES)
    upstream_timeout_seconds = _float_env(
        UPSTREAM_TIMEOUT_SECONDS_ENV, DEFAULT_UPSTREAM_TIMEOUT_SECONDS
    )
    rate_limit_per_minute = _int_env(
        RATE_LIMIT_PER_MINUTE_ENV, DEFAULT_RATE_LIMIT_PER_MINUTE
    )
    audit_log_path = os.getenv(AUDIT_LOG_ENV, "")
    server = ThreadingHTTPServer(
        (host, port),
        create_gateway_handler(
            upstream_base=upstream_base,
            token=token,
            principal=principal,
            roles=roles,
            scopes=scopes,
            revoked_tokens=set(revoked_tokens),
            max_body_bytes=max_body_bytes,
            upstream_timeout_seconds=upstream_timeout_seconds,
            rate_limit_per_minute=rate_limit_per_minute,
            audit_log_path=audit_log_path or None,
        ),
    )
    print(f"AgentOps runtime gateway listening on http://{host}:{port}")  # noqa: T201
    server.serve_forever()


def main() -> None:
    parser = argparse.ArgumentParser(description="Start the AgentOps runtime gateway.")
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=8766)
    args = parser.parse_args()
    run_gateway(host=args.host, port=args.port)


if __name__ == "__main__":
    main()
