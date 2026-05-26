"""Reference API Gateway for AgentOps runtime smoke deployments."""

from __future__ import annotations

import argparse
import json
import os
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
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


def create_gateway_handler(
    *,
    upstream_base: str = DEFAULT_UPSTREAM_BASE,
    token: str | None = None,
    principal: str = "producer.ai-sdlc.gateway",
    roles: str = "agentops-ingestor",
    scopes: str = "event.ingest",
) -> type[BaseHTTPRequestHandler]:
    expected_token = token or ""
    normalized_upstream = upstream_base.rstrip("/") + "/"

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
            if not expected_token:
                self._send_json(
                    HTTPStatus.SERVICE_UNAVAILABLE,
                    {
                        "error_code": "GATEWAY_TOKEN_NOT_CONFIGURED",
                        "message": "Gateway Bearer token is not configured.",
                    },
                )
                return
            if self._bearer_token() != expected_token:
                self._send_json(
                    HTTPStatus.UNAUTHORIZED,
                    {
                        "error_code": "GATEWAY_TOKEN_INVALID",
                        "message": "Gateway Bearer token is invalid.",
                    },
                )
                return
            raw_body = self.rfile.read(_content_length(self.headers))
            self._forward_agentops_request(
                method="POST",
                upstream_path="v1/runtime/events",
                raw_body=raw_body,
                roles=roles,
                scopes=scopes,
            )

        def _forward_agentops_request(
            self,
            *,
            method: str,
            upstream_path: str,
            raw_body: bytes | None,
            roles: str,
            scopes: str,
        ) -> None:
            request_id = self.headers.get("X-Request-Id") or f"req_gateway_{uuid4().hex}"
            audit_id = f"audit_gateway_{uuid4().hex}"
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
                with urlopen(request, timeout=10) as response:
                    body = response.read()
                    self._send_raw(response.status, response.headers.get("Content-Type"), body)
            except HTTPError as exc:
                self._send_raw(exc.code, exc.headers.get("Content-Type"), exc.read())
            except URLError:
                self._send_json(
                    HTTPStatus.BAD_GATEWAY,
                    {
                        "error_code": "AGENTOPS_UPSTREAM_UNAVAILABLE",
                        "message": "AgentOps upstream is unavailable.",
                    },
                )

        def _bearer_token(self) -> str:
            value = self.headers.get("Authorization", "")
            prefix = "Bearer "
            if not value.startswith(prefix):
                return ""
            return value[len(prefix) :].strip()

        def _send_json(self, status: HTTPStatus, payload: dict[str, Any]) -> None:
            self._send_raw(
                int(status),
                "application/json; charset=utf-8",
                json.dumps(payload, ensure_ascii=False, sort_keys=True).encode("utf-8"),
            )

        def _send_raw(
            self, status: int, content_type: str | None, body: bytes
        ) -> None:
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


def run_gateway(host: str, port: int) -> None:
    token = os.getenv(TOKEN_ENV, "")
    upstream_base = os.getenv(UPSTREAM_ENV, DEFAULT_UPSTREAM_BASE)
    principal = os.getenv(PRINCIPAL_ENV, "producer.ai-sdlc.gateway")
    roles = os.getenv(ROLES_ENV, "agentops-ingestor")
    scopes = os.getenv(SCOPES_ENV, "event.ingest")
    server = ThreadingHTTPServer(
        (host, port),
        create_gateway_handler(
            upstream_base=upstream_base,
            token=token,
            principal=principal,
            roles=roles,
            scopes=scopes,
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
