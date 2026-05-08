"""Minimal standard-library HTTP API for local AgentOps Console integration."""

from __future__ import annotations

import argparse
import base64
import binascii
import hashlib
import hmac
import json
import os
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from typing import Any
from urllib.parse import parse_qs, urlsplit

from agentops import __version__
from agentops.api.auth import parse_upstream_identity, require_scope
from agentops.api.console_snapshot import build_console_snapshot
from agentops.api.credentials import (
    get_credential_status,
    reissue_credentials,
    revoke_credentials,
)
from agentops.api.ingestion import ingest_events_batch
from agentops.api.store_summary import get_agent_store_summary_for_run
from agentops.core.errors import AgentOpsError
from agentops.storage.audit import AuditRecord, JsonlAuditLog
from agentops.storage.repository import InMemoryRepository

ALLOWED_ORIGINS = {
    "http://127.0.0.1:5173",
    "http://127.0.0.1:5174",
    "http://localhost:5173",
    "http://localhost:5174",
}

AUDIT_QUERY_DEFAULT_LIMIT = 50
AUDIT_QUERY_MAX_LIMIT = 200
AUDIT_QUERY_CURSOR_VERSION = 1
AUDIT_QUERY_CURSOR_SECRET_ENV = "AGENTOPS_AUDIT_CURSOR_SECRET"


def create_http_handler(
    repository: InMemoryRepository | None = None,
    *,
    require_auth: bool = False,
    audit_log: JsonlAuditLog | None = None,
    audit_cursor_secret: str | bytes | None = None,
) -> type[BaseHTTPRequestHandler]:
    live_repository = repository or InMemoryRepository()
    audit_cursor_secret_bytes = _audit_cursor_secret_bytes(
        audit_cursor_secret,
    )

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
                response = build_console_snapshot(repository=live_repository)
                self._append_audit_record(
                    action="console.snapshot.read",
                    outcome="accepted",
                    resource=request_path,
                )
                self._send_json(HTTPStatus.OK, response)
                return

            if request_path == "/v1/audit/runtime":
                auth_error = self._require_scope("runtime.audit.read")
                if auth_error:
                    self._send_auth_error(
                        auth_error,
                        action="runtime.audit.read",
                        resource=request_path,
                    )
                    return
                if audit_log is None:
                    self._send_json(
                        HTTPStatus.SERVICE_UNAVAILABLE,
                        {
                            "error_code": "AUDIT_LOG_UNAVAILABLE",
                            "message": "Runtime audit log is not configured.",
                            "retryable": True,
                        },
                    )
                    return
                query = self._request_query()
                try:
                    response = self._runtime_audit_query_response(query)
                except AgentOpsError as exc:
                    self._append_audit_record(
                        action="runtime.audit.read",
                        outcome="rejected",
                        resource=request_path,
                        error_code=exc.error_code,
                    )
                    status = (
                        HTTPStatus.SERVICE_UNAVAILABLE
                        if exc.error_code == "AUDIT_CURSOR_SECRET_UNCONFIGURED"
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
                self._append_audit_record(
                    action="runtime.audit.read",
                    outcome="accepted",
                    resource=request_path,
                )
                self._send_json(HTTPStatus.OK, response)
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
                    self._append_audit_record(
                        action="store.summary.read",
                        outcome="rejected",
                        resource=request_path,
                        error_code="STORE_SUMMARY_QUERY_REQUIRED",
                    )
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
                    self._append_audit_record(
                        action="store.summary.read",
                        outcome="accepted",
                        resource=request_path,
                    )
                    self._send_json(HTTPStatus.OK, response)
                except AgentOpsError as exc:
                    status = self._store_summary_status(exc)
                    self._append_audit_record(
                        action="store.summary.read",
                        outcome="rejected",
                        resource=request_path,
                        error_code=exc.error_code,
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

            credential_status_prefix = "/v1/bootstrap/credentials/"
            if request_path.startswith(credential_status_prefix):
                auth_error = self._require_scope("credential.read")
                if auth_error:
                    self._send_auth_error(auth_error)
                    return
                bootstrap_id = request_path.removeprefix(credential_status_prefix)
                try:
                    response = get_credential_status(live_repository, bootstrap_id)
                    self._append_audit_record(
                        action="credential.read",
                        outcome="accepted",
                        resource=request_path,
                    )
                    self._send_json(
                        HTTPStatus.OK,
                        response,
                    )
                except AgentOpsError as exc:
                    self._append_audit_record(
                        action="credential.read",
                        outcome="rejected",
                        resource=request_path,
                        error_code=exc.error_code,
                    )
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
                    self._append_audit_record(
                        action="credential.reissue",
                        outcome="rejected",
                        resource=request_path,
                        error_code="REQUEST_JSON_INVALID",
                    )
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
                    self._append_audit_record(
                        action="credential.reissue",
                        outcome="accepted",
                        resource=request_path,
                    )
                    self._send_json(HTTPStatus.OK, response)
                except AgentOpsError as exc:
                    status = (
                        HTTPStatus.NOT_FOUND
                        if exc.error_code == "CREDENTIAL_REISSUE_NOT_FOUND"
                        else HTTPStatus.BAD_REQUEST
                    )
                    self._append_audit_record(
                        action="credential.reissue",
                        outcome="rejected",
                        resource=request_path,
                        error_code=exc.error_code,
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
                    self._append_audit_record(
                        action="credential.revoke",
                        outcome="rejected",
                        resource=request_path,
                        error_code="REQUEST_JSON_INVALID",
                    )
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
                    self._append_audit_record(
                        action="credential.revoke",
                        outcome="accepted",
                        resource=request_path,
                    )
                    self._send_json(HTTPStatus.OK, response)
                except AgentOpsError as exc:
                    status = (
                        HTTPStatus.NOT_FOUND
                        if exc.error_code == "CREDENTIAL_REVOCATION_NOT_FOUND"
                        else HTTPStatus.BAD_REQUEST
                    )
                    self._append_audit_record(
                        action="credential.revoke",
                        outcome="rejected",
                        resource=request_path,
                        error_code=exc.error_code,
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
                    self._send_auth_error(
                        auth_error, action="event.ingest", resource=request_path
                    )
                    return
                payload = self._read_json()
                if payload is None:
                    self._append_audit_record(
                        action="event.ingest",
                        outcome="rejected",
                        resource=request_path,
                        error_code="REQUEST_JSON_INVALID",
                    )
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
                    self._append_audit_record(
                        action="event.ingest",
                        outcome="rejected",
                        resource=request_path,
                        error_code="EVENTS_REQUIRED",
                    )
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
                self._append_audit_record(
                    action="event.ingest",
                    outcome="accepted"
                    if status == HTTPStatus.ACCEPTED
                    else "rejected",
                    resource=request_path,
                    error_code="" if status == HTTPStatus.ACCEPTED else "EVENTS_REJECTED",
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

        def _runtime_audit_query_response(
            self, query: dict[str, list[str]]
        ) -> dict[str, Any]:
            limit = self._audit_query_limit(query)
            filters = {
                name: self._query_value(query, name)
                for name in ("audit_id", "request_id", "action", "outcome")
                if self._query_value(query, name)
            }
            cursor = self._query_value(query, "cursor")
            cursor_state = self._audit_query_cursor_state(cursor, filters)
            cursor_offset = cursor_state["offset"]
            page_end = cursor_offset + limit
            page_records = []
            matched_count = 0
            for record in audit_log.records() if audit_log is not None else []:
                if (
                    cursor_state["end"] is not None
                    and matched_count >= cursor_state["end"]
                ):
                    break
                record_payload = record.to_dict()
                if any(record_payload.get(name) != value for name, value in filters.items()):
                    continue
                if cursor_offset <= matched_count < page_end:
                    page_records.append(record_payload)
                matched_count += 1
            snapshot_end = cursor_state["end"]
            if snapshot_end is None:
                snapshot_end = matched_count
            snapshot_end = min(snapshot_end, matched_count)
            cursor_offset = min(cursor_offset, snapshot_end)
            next_offset = cursor_offset + len(page_records)
            has_more = next_offset < snapshot_end
            next_cursor = (
                self._encode_audit_query_cursor(
                    end=snapshot_end,
                    offset=next_offset,
                    filters=filters,
                )
                if has_more and audit_cursor_secret_bytes is not None
                else ""
            )
            return {
                "schema_version": "agentops.runtime_audit.query.v1",
                "records": page_records,
                "returned": len(page_records),
                "limit": limit,
                "filters": filters,
                "page_info": {
                    "cursor": cursor,
                    "next_cursor": next_cursor,
                    "has_more": has_more,
                },
            }

        def _audit_query_limit(self, query: dict[str, list[str]]) -> int:
            raw_limit = self._query_value(query, "limit")
            if not raw_limit:
                return AUDIT_QUERY_DEFAULT_LIMIT
            try:
                limit = int(raw_limit)
            except ValueError as exc:
                raise AgentOpsError(
                    "AUDIT_LIMIT_INVALID",
                    "Runtime audit query limit must be a positive integer.",
                ) from exc
            if limit < 1:
                raise AgentOpsError(
                    "AUDIT_LIMIT_INVALID",
                    "Runtime audit query limit must be a positive integer.",
                )
            return min(limit, AUDIT_QUERY_MAX_LIMIT)

        def _audit_query_cursor_state(
            self, cursor: str, filters: dict[str, str]
        ) -> dict[str, int | None]:
            if not cursor:
                return {"end": None, "offset": 0}
            try:
                padded_cursor = cursor + "=" * (-len(cursor) % 4)
                decoded = base64.b64decode(
                    padded_cursor.encode("ascii"),
                    altchars=b"-_",
                    validate=True,
                )
                envelope = json.loads(decoded.decode("utf-8"))
            except (
                binascii.Error,
                UnicodeEncodeError,
                UnicodeDecodeError,
                ValueError,
                json.JSONDecodeError,
            ) as exc:
                raise AgentOpsError(
                    "AUDIT_CURSOR_INVALID",
                    "Runtime audit query cursor is invalid.",
                ) from exc
            if not isinstance(envelope, dict):
                raise AgentOpsError(
                    "AUDIT_CURSOR_INVALID",
                    "Runtime audit query cursor is invalid.",
                )
            payload = envelope.get("payload")
            signature = envelope.get("sig")
            if not isinstance(payload, dict) or not isinstance(signature, str):
                raise AgentOpsError(
                    "AUDIT_CURSOR_INVALID",
                    "Runtime audit query cursor is invalid.",
                )
            try:
                signature_bytes = signature.encode("ascii")
            except UnicodeEncodeError as exc:
                raise AgentOpsError(
                    "AUDIT_CURSOR_INVALID",
                    "Runtime audit query cursor is invalid.",
                ) from exc
            signing_secret = self._audit_query_signing_secret()
            serialized_payload = self._audit_query_cursor_payload_bytes(payload)
            expected_signature = hmac.new(
                signing_secret,
                serialized_payload,
                hashlib.sha256,
            ).hexdigest().encode("ascii")
            if not hmac.compare_digest(signature_bytes, expected_signature):
                raise AgentOpsError(
                    "AUDIT_CURSOR_INVALID",
                    "Runtime audit query cursor is invalid.",
                )
            if payload.get("v") != AUDIT_QUERY_CURSOR_VERSION:
                raise AgentOpsError(
                    "AUDIT_CURSOR_INVALID",
                    "Runtime audit query cursor is invalid.",
                )
            offset = payload.get("offset")
            if not isinstance(offset, int) or isinstance(offset, bool) or offset < 0:
                raise AgentOpsError(
                    "AUDIT_CURSOR_INVALID",
                    "Runtime audit query cursor is invalid.",
                )
            end = payload.get("end")
            if not isinstance(end, int) or isinstance(end, bool) or end < 0:
                raise AgentOpsError(
                    "AUDIT_CURSOR_INVALID",
                    "Runtime audit query cursor is invalid.",
                )
            if payload.get("filters") != filters:
                raise AgentOpsError(
                    "AUDIT_CURSOR_INVALID",
                    "Runtime audit query cursor does not match filters.",
                )
            return {"end": end, "offset": offset}

        def _encode_audit_query_cursor(
            self, *, end: int, offset: int, filters: dict[str, str]
        ) -> str:
            payload = {
                "end": end,
                "filters": filters,
                "offset": offset,
                "v": AUDIT_QUERY_CURSOR_VERSION,
            }
            signing_secret = self._audit_query_signing_secret()
            serialized_payload = self._audit_query_cursor_payload_bytes(payload)
            envelope = {
                "payload": payload,
                "sig": hmac.new(
                    signing_secret,
                    serialized_payload,
                    hashlib.sha256,
                ).hexdigest(),
            }
            serialized_envelope = json.dumps(
                envelope,
                ensure_ascii=False,
                separators=(",", ":"),
                sort_keys=True,
            ).encode("utf-8")
            return (
                base64.urlsafe_b64encode(serialized_envelope)
                .decode("ascii")
                .rstrip("=")
            )

        def _audit_query_cursor_payload_bytes(self, payload: dict[str, Any]) -> bytes:
            return json.dumps(
                payload,
                ensure_ascii=False,
                separators=(",", ":"),
                sort_keys=True,
            ).encode("utf-8")

        def _audit_query_signing_secret(self) -> bytes:
            if audit_cursor_secret_bytes is None:
                raise AgentOpsError(
                    "AUDIT_CURSOR_SECRET_UNCONFIGURED",
                    "Runtime audit query cursor signing secret is not configured.",
                    retryable=True,
                )
            return audit_cursor_secret_bytes

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

        def _send_auth_error(
            self,
            exc: AgentOpsError,
            *,
            action: str | None = None,
            resource: str | None = None,
        ) -> None:
            self._append_audit_record(
                action=action or exc.denied_scope or "authorization.check",
                outcome="denied",
                resource=resource or self._request_path(),
                denied_scope=exc.denied_scope,
                error_code=exc.error_code,
                audit_id=exc.audit_id,
                request_id=exc.request_id,
            )
            status = (
                HTTPStatus.UNAUTHORIZED
                if exc.error_code == "UPSTREAM_IDENTITY_REQUIRED"
                else HTTPStatus.FORBIDDEN
            )
            self._send_json(status, exc.to_response())

        def _append_audit_record(
            self,
            *,
            action: str,
            outcome: str,
            resource: str,
            denied_scope: str | None = None,
            error_code: str = "",
            audit_id: str | None = None,
            request_id: str | None = None,
        ) -> None:
            if audit_log is None:
                return

            identity = parse_upstream_identity(self.headers)
            try:
                audit_log.append(
                    AuditRecord(
                        audit_id=audit_id
                        or (identity.audit_id if identity else "audit_anonymous"),
                        request_id=request_id
                        or (identity.request_id if identity else "req_anonymous"),
                        action=action,
                        outcome=outcome,
                        principal=identity.principal if identity else "anonymous",
                        roles=tuple(sorted(identity.roles)) if identity else (),
                        scopes=tuple(sorted(identity.scopes)) if identity else (),
                        resource=resource,
                        denied_scope=denied_scope or "",
                        error_code=error_code,
                    )
                )
            except OSError:
                return

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


def _audit_cursor_secret_bytes(
    audit_cursor_secret: str | bytes | None,
) -> bytes | None:
    if isinstance(audit_cursor_secret, bytes) and audit_cursor_secret:
        return audit_cursor_secret
    if isinstance(audit_cursor_secret, str) and audit_cursor_secret:
        return audit_cursor_secret.encode("utf-8")

    env_secret = os.environ.get(AUDIT_QUERY_CURSOR_SECRET_ENV, "")
    if env_secret:
        return env_secret.encode("utf-8")

    return None


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
