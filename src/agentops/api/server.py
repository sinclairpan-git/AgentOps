"""Minimal standard-library HTTP API for local AgentOps Console integration."""

from __future__ import annotations

import argparse
import json
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from typing import Any
from urllib.parse import parse_qs, urlsplit

from agentops import __version__
from agentops.api.auth import require_scope
from agentops.api.console_snapshot import build_console_snapshot
from agentops.api.credentials import (
    get_credential_status,
    reissue_credentials,
    revoke_credentials,
)
from agentops.api.ingestion import ingest_events_batch
from agentops.api.store_summary import get_agent_store_summary_for_run
from agentops.core.errors import AgentOpsError
from agentops.storage.repository import InMemoryRepository

ALLOWED_ORIGINS = {
    "http://127.0.0.1:5173",
    "http://127.0.0.1:5174",
    "http://localhost:5173",
    "http://localhost:5174",
}


def create_http_handler(
    repository: InMemoryRepository | None = None,
    *,
    require_auth: bool = False,
) -> type[BaseHTTPRequestHandler]:
    live_repository = repository or InMemoryRepository()

    class AgentOpsRequestHandler(BaseHTTPRequestHandler):
        server_version = "AgentOpsHTTP/0.1"

        def do_OPTIONS(self) -> None:  # noqa: N802
            if not self._origin_allowed():
                self._send_json(
                    HTTPStatus.FORBIDDEN,
                    {
                        "error_code": "ORIGIN_FORBIDDEN",
                        "message": "请求来源不在本地开发白名单内。",
                    },
                )
                return
            self._send_json(HTTPStatus.NO_CONTENT, {})

        def do_GET(self) -> None:  # noqa: N802
            if not self._origin_allowed():
                self._send_json(
                    HTTPStatus.FORBIDDEN,
                    {
                        "error_code": "ORIGIN_FORBIDDEN",
                        "message": "请求来源不在本地开发白名单内。",
                    },
                )
                return

            request_path = self._request_path()
            if request_path == "/v1/health":
                self._send_json(
                    HTTPStatus.OK,
                    {
                        "service": "agentops-api",
                        "status": "healthy",
                        "version": __version__,
                        "snapshot_provider": "ready",
                    },
                )
                return

            if request_path == "/v1/console/snapshot":
                auth_error = self._require_scope("console.snapshot.read")
                if auth_error:
                    self._send_auth_error(auth_error)
                    return
                self._send_json(
                    HTTPStatus.OK, build_console_snapshot(repository=live_repository)
                )
                return

            store_summary_prefix = "/v1/store-summary/"
            if request_path.startswith(store_summary_prefix):
                auth_error = self._require_scope("store.summary.read")
                if auth_error:
                    self._send_auth_error(auth_error)
                    return
                agent_id = request_path.removeprefix(store_summary_prefix).strip("/")
                if not agent_id or "/" in agent_id:
                    self._send_json(
                        HTTPStatus.NOT_FOUND,
                        {
                            "error_code": "NOT_FOUND",
                            "message": "未找到请求的 AgentOps API 路径。",
                        },
                    )
                    return
                query = self._request_query()
                version = self._query_value(query, "version")
                run_id = self._query_value(query, "run_id")
                schema_version = self._query_value(query, "schema_version") or "1.0"
                if not version or not run_id:
                    self._send_json(
                        HTTPStatus.BAD_REQUEST,
                        {
                            "error_code": "STORE_SUMMARY_QUERY_REQUIRED",
                            "message": "Agent Store summary requires agent_id, version, and run_id.",
                            "retryable": False,
                        },
                    )
                    return
                try:
                    response = get_agent_store_summary_for_run(
                        live_repository,
                        agent_id,
                        version,
                        run_id,
                        consumer_schema_version=schema_version,
                    )
                    self._send_json(HTTPStatus.OK, response)
                except AgentOpsError as exc:
                    status = self._store_summary_status(exc)
                    self._send_json(
                        status,
                        {
                            "error_code": exc.error_code,
                            "message": exc.message,
                            "retryable": exc.retryable,
                        },
                    )
                return

            credential_status_prefix = "/v1/bootstrap/credentials/"
            if request_path.startswith(credential_status_prefix):
                auth_error = self._require_scope("credential.read")
                if auth_error:
                    self._send_auth_error(auth_error)
                    return
                bootstrap_id = request_path.removeprefix(credential_status_prefix)
                try:
                    self._send_json(
                        HTTPStatus.OK,
                        get_credential_status(live_repository, bootstrap_id),
                    )
                except AgentOpsError as exc:
                    self._send_json(
                        HTTPStatus.NOT_FOUND,
                        {
                            "error_code": exc.error_code,
                            "message": exc.message,
                            "retryable": exc.retryable,
                        },
                    )
                return

            self._send_json(
                HTTPStatus.NOT_FOUND,
                {
                    "error_code": "NOT_FOUND",
                    "message": "未找到请求的 AgentOps API 路径。",
                },
            )

        def do_POST(self) -> None:  # noqa: N802
            if not self._origin_allowed():
                self._send_json(
                    HTTPStatus.FORBIDDEN,
                    {
                        "error_code": "ORIGIN_FORBIDDEN",
                        "message": "请求来源不在本地开发白名单内。",
                    },
                )
                return

            request_path = self._request_path()
            credential_prefix = "/v1/bootstrap/credentials/"
            reissue_suffix = "/reissue"
            if request_path.startswith(credential_prefix) and request_path.endswith(
                reissue_suffix
            ):
                auth_error = self._require_scope("credential.write")
                if auth_error:
                    self._send_auth_error(auth_error)
                    return
                bootstrap_id = (
                    request_path.removeprefix(credential_prefix)
                    .removesuffix(reissue_suffix)
                    .strip("/")
                )
                payload = self._read_json()
                if payload is None:
                    self._send_json(
                        HTTPStatus.BAD_REQUEST,
                        {
                            "error_code": "REQUEST_JSON_INVALID",
                            "message": "请求体必须是 JSON。",
                        },
                    )
                    return
                try:
                    response = reissue_credentials(
                        {**payload, "source_bootstrap_id": bootstrap_id},
                        live_repository,
                        headers=dict(self.headers),
                    )
                    self._send_json(HTTPStatus.OK, response)
                except AgentOpsError as exc:
                    status = (
                        HTTPStatus.NOT_FOUND
                        if exc.error_code == "CREDENTIAL_REISSUE_NOT_FOUND"
                        else HTTPStatus.BAD_REQUEST
                    )
                    self._send_json(
                        status,
                        {
                            "error_code": exc.error_code,
                            "message": exc.message,
                            "retryable": exc.retryable,
                        },
                    )
                return

            revoke_prefix = credential_prefix
            revoke_suffix = "/revoke"
            if request_path.startswith(revoke_prefix) and request_path.endswith(
                revoke_suffix
            ):
                auth_error = self._require_scope("credential.write")
                if auth_error:
                    self._send_auth_error(auth_error)
                    return
                bootstrap_id = (
                    request_path.removeprefix(revoke_prefix)
                    .removesuffix(revoke_suffix)
                    .strip("/")
                )
                payload = self._read_json()
                if payload is None:
                    self._send_json(
                        HTTPStatus.BAD_REQUEST,
                        {
                            "error_code": "REQUEST_JSON_INVALID",
                            "message": "请求体必须是 JSON。",
                        },
                    )
                    return
                try:
                    response = revoke_credentials(
                        {**payload, "bootstrap_id": bootstrap_id}, live_repository
                    )
                    self._send_json(HTTPStatus.OK, response)
                except AgentOpsError as exc:
                    status = (
                        HTTPStatus.NOT_FOUND
                        if exc.error_code == "CREDENTIAL_REVOCATION_NOT_FOUND"
                        else HTTPStatus.BAD_REQUEST
                    )
                    self._send_json(
                        status,
                        {
                            "error_code": exc.error_code,
                            "message": exc.message,
                            "retryable": exc.retryable,
                        },
                    )
                return

            if request_path in {"/v1/events", "/v1/events/batch"}:
                auth_error = self._require_scope("event.ingest")
                if auth_error:
                    self._send_auth_error(auth_error)
                    return
                payload = self._read_json()
                if payload is None:
                    self._send_json(
                        HTTPStatus.BAD_REQUEST,
                        {
                            "error_code": "REQUEST_JSON_INVALID",
                            "message": "请求体必须是 JSON。",
                        },
                    )
                    return
                events = payload.get("events") if isinstance(payload, dict) else None
                if not isinstance(events, list):
                    self._send_json(
                        HTTPStatus.BAD_REQUEST,
                        {
                            "error_code": "EVENTS_REQUIRED",
                            "message": "请求体必须包含 events 数组。",
                        },
                    )
                    return
                outcome = ingest_events_batch(events, live_repository)
                status = (
                    HTTPStatus.ACCEPTED
                    if outcome["accepted"] or outcome["deduplicated"]
                    else HTTPStatus.BAD_REQUEST
                )
                self._send_json(status, outcome)
                return

            self._send_json(
                HTTPStatus.NOT_FOUND,
                {
                    "error_code": "NOT_FOUND",
                    "message": "未找到请求的 AgentOps API 路径。",
                },
            )

        def log_message(self, format: str, *args: Any) -> None:
            return

        def _origin_allowed(self) -> bool:
            origin = self.headers.get("Origin")
            return origin is None or origin in ALLOWED_ORIGINS

        def _request_path(self) -> str:
            return urlsplit(self.path).path

        def _request_query(self) -> dict[str, list[str]]:
            return parse_qs(urlsplit(self.path).query, keep_blank_values=True)

        def _query_value(self, query: dict[str, list[str]], name: str) -> str:
            values = query.get(name) or []
            return values[0].strip() if values else ""

        def _store_summary_status(self, exc: AgentOpsError) -> HTTPStatus:
            if exc.error_code == "RUN_NOT_FOUND":
                return HTTPStatus.NOT_FOUND
            if exc.error_code == "SUMMARY_SCHEMA_UNSUPPORTED":
                return HTTPStatus.CONFLICT
            if exc.error_code == "STORE_SUMMARY_RUN_MISMATCH":
                return HTTPStatus.CONFLICT
            return HTTPStatus.BAD_REQUEST

        def _read_json(self) -> dict[str, Any] | None:
            try:
                content_length = int(self.headers.get("Content-Length", "0"))
                body = self.rfile.read(content_length) if content_length else b"{}"
                payload = json.loads(body.decode("utf-8"))
                return payload if isinstance(payload, dict) else None
            except (UnicodeDecodeError, json.JSONDecodeError, ValueError):
                return None

        def _require_scope(self, scope: str) -> AgentOpsError | None:
            try:
                require_scope(self.headers, scope, auth_required=require_auth)
            except AgentOpsError as exc:
                return exc
            return None

        def _send_auth_error(self, exc: AgentOpsError) -> None:
            status = (
                HTTPStatus.UNAUTHORIZED
                if exc.error_code == "UPSTREAM_IDENTITY_REQUIRED"
                else HTTPStatus.FORBIDDEN
            )
            self._send_json(status, exc.to_response())

        def _send_json(self, status: HTTPStatus, payload: dict[str, Any]) -> None:
            body = (
                b""
                if status == HTTPStatus.NO_CONTENT
                else json.dumps(payload, ensure_ascii=False).encode("utf-8")
            )
            origin = self.headers.get("Origin")
            self.send_response(status)
            self.send_header("Content-Type", "application/json; charset=utf-8")
            if origin in ALLOWED_ORIGINS:
                self.send_header("Access-Control-Allow-Origin", origin)
            self.send_header("Access-Control-Allow-Methods", "GET, POST, OPTIONS")
            allowed_headers = "Content-Type, Idempotency-Key"
            if require_auth:
                allowed_headers = (
                    f"{allowed_headers}, X-AgentOps-Principal, X-AgentOps-Roles, "
                    "X-AgentOps-Scopes, X-AgentOps-Scope, X-AgentOps-Request-Id, "
                    "X-AgentOps-Audit-Id"
                )
            self.send_header("Access-Control-Allow-Headers", allowed_headers)
            self.send_header("Cache-Control", "no-store")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            if body:
                self.wfile.write(body)

    return AgentOpsRequestHandler


def run_server(
    host: str = "127.0.0.1", port: int = 8765, *, require_auth: bool = False
) -> None:
    httpd = ThreadingHTTPServer(
        (host, port), create_http_handler(require_auth=require_auth)
    )
    print(f"AgentOps API listening on http://{host}:{port}")  # noqa: T201
    httpd.serve_forever()


def main() -> None:
    parser = argparse.ArgumentParser(description="Start the local AgentOps API server.")
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", default=8765, type=int)
    parser.add_argument(
        "--require-auth",
        action="store_true",
        help="Require upstream IAM/RBAC headers for sensitive and mutating routes.",
    )
    args = parser.parse_args()
    run_server(host=args.host, port=args.port, require_auth=args.require_auth)


if __name__ == "__main__":
    main()
