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
from agentops.api.operations import (
    get_quality_center_external_intake_portfolio,
    ingest_quality_scorer_external_execution,
)
from agentops.api.runtime import (
    get_sdlc_findings,
    get_sdlc_run_health_summary,
    get_sdlc_trends,
    get_runtime_evidence_summary,
    get_runtime_health_summary,
    get_runtime_run_detail,
    get_runtime_trace_timeline,
    ingest_runtime_events,
)
from agentops.api.store_summary import get_agent_store_summary_for_run
from agentops.core.errors import AgentOpsError
from agentops.storage.audit import AuditRecord, JsonlAuditLog
from agentops.storage.factory import repository_from_env
from agentops.storage.repository import InMemoryRepository

DEFAULT_ALLOWED_ORIGINS = {
    "http://127.0.0.1:5173",
    "http://127.0.0.1:5174",
    "http://127.0.0.1:4173",
    "http://localhost:5173",
    "http://localhost:5174",
    "http://localhost:4173",
}
ALLOWED_ORIGINS_ENV = "AGENTOPS_ALLOWED_ORIGINS"

AUDIT_QUERY_DEFAULT_LIMIT = 50
AUDIT_QUERY_MAX_LIMIT = 200
EXTERNAL_INTAKE_INDEX_DEFAULT_LIMIT = 25
EXTERNAL_INTAKE_INDEX_MAX_LIMIT = 100
EXTERNAL_INTAKE_SUMMARY_DEFAULT_LIMIT = 100
EXTERNAL_INTAKE_SUMMARY_MAX_LIMIT = 250
QUALITY_CENTER_PORTFOLIO_SCOPE_DEFAULT_LIMIT = 25
QUALITY_CENTER_PORTFOLIO_SCOPE_MAX_LIMIT = 25
EXTERNAL_INTAKE_FORBIDDEN_QUERY_MARKERS = (
    "token_secret",
    "credential_secret",
    "device_key",
    "://",
    "/raw",
)
AUDIT_QUERY_CURSOR_VERSION = 1
AUDIT_QUERY_CURSOR_SECRET_ENV = "AGENTOPS_AUDIT_CURSOR_SECRET"
AUDIT_EXPORT_FILTER_NAMES = ("audit_id", "request_id", "action", "outcome")
AUDIT_EXPORT_SELF_ACTIONS = {
    "runtime.audit.export",
    "runtime.audit.export.bundle",
}


def create_http_handler(
    repository: InMemoryRepository | None = None,
    *,
    require_auth: bool = False,
    audit_log: JsonlAuditLog | None = None,
    audit_cursor_secret: str | bytes | None = None,
) -> type[BaseHTTPRequestHandler]:
    live_repository = repository or repository_from_env(require_auth=require_auth)
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

            if request_path == "/v1/quality/scorers/external-intake/index":
                action = "quality.scorer.external_intake.index"
                auth_error = self._require_scope("quality.scorer.intake.read")
                if auth_error:
                    self._send_auth_error(
                        auth_error,
                        action=action,
                        resource=request_path,
                    )
                    return
                try:
                    response = self._quality_scorer_external_intake_index_response(
                        self._request_query()
                    )
                except AgentOpsError as exc:
                    self._append_audit_record(
                        action=action,
                        outcome="rejected",
                        resource=request_path,
                        error_code=exc.error_code,
                        audit_id=exc.audit_id,
                        request_id=exc.request_id,
                    )
                    self._send_json(
                        self._quality_scorer_external_intake_index_status(exc),
                        exc.to_response(),
                    )
                    return
                self._append_audit_record(
                    action=action,
                    outcome="accepted",
                    resource=request_path,
                    audit_id=response.get("audit_id"),
                )
                self._send_json(HTTPStatus.OK, response)
                return

            if request_path == "/v1/quality/scorers/external-intake/summary":
                action = "quality.scorer.external_intake.summary"
                auth_error = self._require_scope("quality.scorer.intake.read")
                if auth_error:
                    self._send_auth_error(
                        auth_error,
                        action=action,
                        resource=request_path,
                    )
                    return
                try:
                    response = self._quality_scorer_external_intake_summary_response(
                        self._request_query()
                    )
                except AgentOpsError as exc:
                    self._append_audit_record(
                        action=action,
                        outcome="rejected",
                        resource=request_path,
                        error_code=exc.error_code,
                        audit_id=exc.audit_id,
                        request_id=exc.request_id,
                    )
                    self._send_json(
                        self._quality_scorer_external_intake_summary_status(exc),
                        exc.to_response(),
                    )
                    return
                self._append_audit_record(
                    action=action,
                    outcome="accepted",
                    resource=request_path,
                    audit_id=response.get("audit_id"),
                )
                self._send_json(HTTPStatus.OK, response)
                return

            if request_path == "/v1/quality/center/external-intake/portfolio":
                action = "quality.center.external_intake.portfolio"
                auth_error = self._require_scope("quality.scorer.intake.read")
                if auth_error:
                    self._send_auth_error(
                        auth_error,
                        action=action,
                        resource=request_path,
                    )
                    return
                try:
                    response = self._quality_center_external_intake_portfolio_response(
                        self._request_query()
                    )
                except AgentOpsError as exc:
                    self._append_audit_record(
                        action=action,
                        outcome="rejected",
                        resource=request_path,
                        error_code=exc.error_code,
                        audit_id=exc.audit_id,
                        request_id=exc.request_id,
                    )
                    self._send_json(
                        self._quality_center_external_intake_portfolio_status(exc),
                        exc.to_response(),
                    )
                    return
                self._append_audit_record(
                    action=action,
                    outcome="accepted",
                    resource=request_path,
                    audit_id=response.get("audit_id"),
                )
                self._send_json(HTTPStatus.OK, response)
                return

            if request_path == "/v1/quality/scorers/external-intake":
                action = "quality.scorer.external_intake.read"
                auth_error = self._require_scope("quality.scorer.intake.read")
                if auth_error:
                    self._send_auth_error(
                        auth_error,
                        action=action,
                        resource=request_path,
                    )
                    return
                try:
                    response = self._quality_scorer_external_intake_read_response(
                        self._request_query()
                    )
                except AgentOpsError as exc:
                    self._append_audit_record(
                        action=action,
                        outcome="rejected",
                        resource=request_path,
                        error_code=exc.error_code,
                        audit_id=exc.audit_id,
                        request_id=exc.request_id,
                    )
                    self._send_json(
                        self._quality_scorer_external_intake_read_status(exc),
                        exc.to_response(),
                    )
                    return
                self._append_audit_record(
                    action=action,
                    outcome="accepted",
                    resource=request_path,
                    audit_id=response.get("audit_id"),
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

            if request_path == "/v1/audit/runtime/export-manifest":
                auth_error = self._require_scope("runtime.audit.read")
                if auth_error:
                    self._send_auth_error(
                        auth_error,
                        action="runtime.audit.export",
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
                    response = self._runtime_audit_export_manifest_response(query)
                except AgentOpsError as exc:
                    self._append_audit_record(
                        action="runtime.audit.export",
                        outcome="rejected",
                        resource=request_path,
                        error_code=exc.error_code,
                    )
                    self._send_json(
                        HTTPStatus.BAD_REQUEST,
                        {
                            "error_code": exc.error_code,
                            "message": exc.message,
                            "retryable": exc.retryable,
                        },
                    )
                    return
                self._append_audit_record(
                    action="runtime.audit.export",
                    outcome="accepted",
                    resource=request_path,
                )
                self._send_json(HTTPStatus.OK, response)
                return

            sdlc_run_health_prefix = "/v1/runtime/sdlc/runs/"
            sdlc_run_health_suffix = "/health-summary"
            if request_path.startswith(
                sdlc_run_health_prefix
            ) and request_path.endswith(sdlc_run_health_suffix):
                run_id = (
                    request_path.removeprefix(sdlc_run_health_prefix)
                    .removesuffix(sdlc_run_health_suffix)
                    .strip("/")
                )
                if not run_id or "/" in run_id:
                    self._send_json(
                        HTTPStatus.NOT_FOUND,
                        {
                            "error_code": "NOT_FOUND",
                            "message": "未找到请求的 AgentOps API 路径。",
                        },
                    )
                    return
                auth_error = self._require_scope("runtime.health.read")
                if auth_error:
                    self._send_auth_error(
                        auth_error,
                        action="runtime.sdlc.health.read",
                        resource=request_path,
                    )
                    return
                try:
                    response = get_sdlc_run_health_summary(live_repository, run_id)
                except AgentOpsError as exc:
                    self._append_audit_record(
                        action="runtime.sdlc.health.read",
                        outcome="rejected",
                        resource=request_path,
                        error_code=exc.error_code,
                    )
                    self._send_json(HTTPStatus.NOT_FOUND, exc.to_response())
                    return
                self._append_audit_record(
                    action="runtime.sdlc.health.read",
                    outcome="accepted",
                    resource=request_path,
                )
                self._send_json(HTTPStatus.OK, response)
                return

            if request_path == "/v1/runtime/sdlc/findings":
                auth_error = self._require_scope("runtime.health.read")
                if auth_error:
                    self._send_auth_error(
                        auth_error,
                        action="runtime.sdlc.findings.read",
                        resource=request_path,
                    )
                    return
                response = get_sdlc_findings(live_repository)
                self._append_audit_record(
                    action="runtime.sdlc.findings.read",
                    outcome="accepted",
                    resource=request_path,
                )
                self._send_json(HTTPStatus.OK, response)
                return

            if request_path == "/v1/runtime/sdlc/trends":
                auth_error = self._require_scope("runtime.health.read")
                if auth_error:
                    self._send_auth_error(
                        auth_error,
                        action="runtime.sdlc.trends.read",
                        resource=request_path,
                    )
                    return
                response = get_sdlc_trends(live_repository)
                self._append_audit_record(
                    action="runtime.sdlc.trends.read",
                    outcome="accepted",
                    resource=request_path,
                )
                self._send_json(HTTPStatus.OK, response)
                return

            runtime_trace_prefix = "/v1/runtime/runs/"
            if request_path.startswith(runtime_trace_prefix):
                suffix = request_path.removeprefix(runtime_trace_prefix).strip("/")
                if suffix.endswith("/evidence-summary"):
                    run_id = suffix.removesuffix("/evidence-summary").strip("/")
                    if not run_id or "/" in run_id:
                        self._send_json(
                            HTTPStatus.NOT_FOUND,
                            {
                                "error_code": "NOT_FOUND",
                                "message": "未找到请求的 AgentOps API 路径。",
                            },
                        )
                        return
                    auth_error = self._require_scope("runtime.evidence.read")
                    if auth_error:
                        self._send_auth_error(
                            auth_error,
                            action="runtime.evidence.read",
                            resource=request_path,
                        )
                        return
                    try:
                        response = get_runtime_evidence_summary(
                            live_repository,
                            run_id,
                            request_raw=False,
                            raw_access_allowed=False,
                        )
                    except AgentOpsError as exc:
                        self._append_audit_record(
                            action="runtime.evidence.read",
                            outcome="rejected",
                            resource=request_path,
                            error_code=exc.error_code,
                        )
                        self._send_json(
                            HTTPStatus.NOT_FOUND,
                            exc.to_response(),
                        )
                        return
                    self._append_audit_record(
                        action="runtime.evidence.read",
                        outcome="accepted",
                        resource=request_path,
                    )
                    self._send_json(HTTPStatus.OK, response)
                    return

                if suffix.endswith("/trace"):
                    run_id = suffix.removesuffix("/trace").strip("/")
                    if not run_id or "/" in run_id:
                        self._send_json(
                            HTTPStatus.NOT_FOUND,
                            {
                                "error_code": "NOT_FOUND",
                                "message": "未找到请求的 AgentOps API 路径。",
                            },
                        )
                        return
                    auth_error = self._require_scope("runtime.trace.read")
                    if auth_error:
                        self._send_auth_error(
                            auth_error,
                            action="runtime.trace.read",
                            resource=request_path,
                        )
                        return
                    try:
                        response = get_runtime_trace_timeline(
                            live_repository,
                            run_id,
                            request_raw=False,
                            raw_access_allowed=False,
                        )
                    except AgentOpsError as exc:
                        self._append_audit_record(
                            action="runtime.trace.read",
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
                    self._append_audit_record(
                        action="runtime.trace.read",
                        outcome="accepted",
                        resource=request_path,
                    )
                    self._send_json(HTTPStatus.OK, response)
                    return

                run_id = suffix
                if not run_id or "/" in run_id:
                    self._send_json(
                        HTTPStatus.NOT_FOUND,
                        {
                            "error_code": "NOT_FOUND",
                            "message": "未找到请求的 AgentOps API 路径。",
                        },
                    )
                    return
                auth_error = self._require_scope("runtime.run.read")
                if auth_error:
                    self._send_auth_error(
                        auth_error,
                        action="runtime.run.read",
                        resource=request_path,
                    )
                    return
                try:
                    response = get_runtime_run_detail(live_repository, run_id)
                except AgentOpsError as exc:
                    self._append_audit_record(
                        action="runtime.run.read",
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
                self._append_audit_record(
                    action="runtime.run.read",
                    outcome="accepted",
                    resource=request_path,
                )
                self._send_json(HTTPStatus.OK, response)
                return

            runtime_health_prefix = "/v1/runtime/agents/"
            runtime_health_suffix = "/health-summary"
            if request_path.startswith(runtime_health_prefix) and request_path.endswith(
                runtime_health_suffix
            ):
                identity = (
                    request_path.removeprefix(runtime_health_prefix)
                    .removesuffix(runtime_health_suffix)
                    .strip("/")
                )
                parts = identity.split("/")
                if len(parts) != 3 or parts[1] != "versions":
                    self._send_json(
                        HTTPStatus.NOT_FOUND,
                        {
                            "error_code": "NOT_FOUND",
                            "message": "未找到请求的 AgentOps API 路径。",
                        },
                    )
                    return
                agent_id = parts[0]
                version = parts[2]
                auth_error = self._require_scope("runtime.health.read")
                if auth_error:
                    self._send_auth_error(
                        auth_error,
                        action="runtime.health.read",
                        resource=request_path,
                    )
                    return
                response = get_runtime_health_summary(
                    live_repository, agent_id, version
                )
                self._append_audit_record(
                    action="runtime.health.read",
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
            if request_path == "/v1/audit/runtime/export-bundle":
                auth_error = self._require_scope("runtime.audit.export")
                if auth_error:
                    self._send_auth_error(
                        auth_error,
                        action="runtime.audit.export.bundle",
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
                payload = self._read_json()
                if payload is None:
                    self._append_audit_record(
                        action="runtime.audit.export.bundle",
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
                    response = self._runtime_audit_export_bundle_response(payload)
                except AgentOpsError as exc:
                    self._append_audit_record(
                        action="runtime.audit.export.bundle",
                        outcome="rejected",
                        resource=request_path,
                        error_code=exc.error_code,
                    )
                    status = (
                        HTTPStatus.CONFLICT
                        if exc.error_code == "AUDIT_EXPORT_MANIFEST_MISMATCH"
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
                    action="runtime.audit.export.bundle",
                    outcome="accepted",
                    resource=request_path,
                )
                self._send_json(HTTPStatus.OK, response)
                return

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
                    outcome="accepted" if status == HTTPStatus.ACCEPTED else "rejected",
                    resource=request_path,
                    error_code=""
                    if status == HTTPStatus.ACCEPTED
                    else "EVENTS_REJECTED",
                )
                self._send_json(status, outcome)
                return

            if request_path == "/v1/quality/scorers/external-intake":
                action = "quality.scorer.external_intake.ingest"
                auth_error = self._require_scope("quality.scorer.intake.write")
                if auth_error:
                    self._send_auth_error(
                        auth_error,
                        action=action,
                        resource=request_path,
                    )
                    return
                payload = self._read_json()
                if payload is None:
                    self._append_audit_record(
                        action=action,
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
                    response = self._quality_scorer_external_intake_response(payload)
                except AgentOpsError as exc:
                    self._append_audit_record(
                        action=action,
                        outcome="rejected",
                        resource=request_path,
                        error_code=exc.error_code,
                        audit_id=exc.audit_id,
                        request_id=exc.request_id,
                    )
                    self._send_json(
                        self._quality_scorer_external_intake_status(exc),
                        exc.to_response(),
                    )
                    return
                self._append_audit_record(
                    action=action,
                    outcome="accepted",
                    resource=request_path,
                    audit_id=response.get("audit_id"),
                )
                self._send_json(HTTPStatus.ACCEPTED, response)
                return

            if request_path == "/v1/runtime/events":
                auth_error = self._require_scope("event.ingest")
                if auth_error:
                    self._send_auth_error(
                        auth_error,
                        action="runtime.event.ingest",
                        resource=request_path,
                    )
                    return
                payload = self._read_json()
                if payload is None:
                    self._append_audit_record(
                        action="runtime.event.ingest",
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
                    outcome = ingest_runtime_events(payload, live_repository)
                except AgentOpsError as exc:
                    self._append_audit_record(
                        action="runtime.event.ingest",
                        outcome="rejected",
                        resource=request_path,
                        error_code=exc.error_code,
                    )
                    self._send_json(
                        HTTPStatus.BAD_REQUEST,
                        {
                            "error_code": exc.error_code,
                            "message": exc.message,
                            "retryable": exc.retryable,
                        },
                    )
                    return
                status = (
                    HTTPStatus.ACCEPTED
                    if (
                        outcome["accepted_count"]
                        or outcome["deduplicated_count"]
                        or outcome["stale_count"]
                        or outcome["dlq_count"]
                    )
                    else HTTPStatus.BAD_REQUEST
                )
                self._append_audit_record(
                    action="runtime.event.ingest",
                    outcome="accepted" if status == HTTPStatus.ACCEPTED else "rejected",
                    resource=request_path,
                    error_code=""
                    if status == HTTPStatus.ACCEPTED
                    else "EVENTS_REJECTED",
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
            return origin is None or origin in _allowed_origins()

        def _request_path(self) -> str:
            return urlsplit(self.path).path

        def _request_query(self) -> dict[str, list[str]]:
            return parse_qs(urlsplit(self.path).query, keep_blank_values=True)

        def _query_value(self, query: dict[str, list[str]], name: str) -> str:
            values = query.get(name) or []
            return values[0].strip() if values else ""

        def _query_values(self, query: dict[str, list[str]], name: str) -> list[str]:
            return [value.strip() for value in query.get(name, []) if value.strip()]

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
                if any(
                    record_payload.get(name) != value for name, value in filters.items()
                ):
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

        def _runtime_audit_export_manifest_response(
            self, query: dict[str, list[str]]
        ) -> dict[str, Any]:
            export_records = self._runtime_audit_export_records(query)
            return self._runtime_audit_export_manifest_from_records(
                query,
                export_records,
            )

        def _runtime_audit_export_manifest_from_records(
            self,
            query: dict[str, list[str]],
            export_records: list[dict[str, Any]],
        ) -> dict[str, Any]:
            limit = self._audit_query_limit(query)
            filters = self._runtime_audit_export_filters(query)
            content_digest = hashlib.sha256(
                json.dumps(
                    export_records,
                    ensure_ascii=False,
                    separators=(",", ":"),
                    sort_keys=True,
                ).encode("utf-8")
            ).hexdigest()
            manifest_binding_digest = hashlib.sha256(
                json.dumps(
                    {
                        "content_digest": content_digest,
                        "filters": filters,
                        "limit": limit,
                    },
                    ensure_ascii=False,
                    separators=(",", ":"),
                    sort_keys=True,
                ).encode("utf-8")
            ).hexdigest()
            return {
                "schema_version": "agentops.runtime_audit.export_manifest.v1",
                "manifest_id": f"audit_export_{manifest_binding_digest[:16]}",
                "digest_algorithm": "sha256",
                "content_digest": content_digest,
                "record_count": len(export_records),
                "limit": limit,
                "filters": filters,
                "record_audit_ids": [
                    str(record.get("audit_id") or "") for record in export_records
                ],
                "export_available": False,
                "download_url": "",
            }

        def _runtime_audit_export_bundle_response(
            self, payload: dict[str, Any]
        ) -> dict[str, Any]:
            query = self._audit_export_query_from_payload(payload)
            manifest_id = self._audit_export_required_string(payload, "manifest_id")
            content_digest = self._audit_export_required_string(
                payload,
                "content_digest",
            )
            export_records = self._runtime_audit_export_records(query)
            manifest = self._runtime_audit_export_manifest_from_records(
                query,
                export_records,
            )
            if (
                manifest["manifest_id"] != manifest_id
                or manifest["content_digest"] != content_digest
            ):
                raise AgentOpsError(
                    "AUDIT_EXPORT_MANIFEST_MISMATCH",
                    "Runtime audit export manifest does not match current metadata.",
                )

            bundle_digest_input = {
                "manifest_digest": manifest["content_digest"],
                "manifest_id": manifest["manifest_id"],
                "records": export_records,
            }
            bundle_digest = hashlib.sha256(
                json.dumps(
                    bundle_digest_input,
                    ensure_ascii=False,
                    separators=(",", ":"),
                    sort_keys=True,
                ).encode("utf-8")
            ).hexdigest()
            return {
                "schema_version": "agentops.runtime_audit.export_bundle.v1",
                "bundle_id": f"audit_bundle_{bundle_digest[:16]}",
                "bundle_format": "application/vnd.agentops.runtime-audit.metadata+json",
                "digest_algorithm": "sha256",
                "bundle_digest": bundle_digest,
                "manifest_id": manifest["manifest_id"],
                "manifest_digest": manifest["content_digest"],
                "record_count": len(export_records),
                "limit": manifest["limit"],
                "filters": manifest["filters"],
                "records": export_records,
                "download_url": "",
            }

        def _runtime_audit_export_records(
            self, query: dict[str, list[str]]
        ) -> list[dict[str, Any]]:
            limit = self._audit_query_limit(query)
            filters = self._runtime_audit_export_filters(query)
            export_records: list[dict[str, Any]] = []
            for record in audit_log.records() if audit_log is not None else []:
                record_payload = self._audit_export_record_payload(record)
                if any(
                    record_payload.get(name) != value for name, value in filters.items()
                ):
                    continue
                if (
                    "action" not in filters
                    and record_payload.get("action") in AUDIT_EXPORT_SELF_ACTIONS
                ):
                    continue
                export_records.append(record_payload)
                if len(export_records) >= limit:
                    break
            return export_records

        def _runtime_audit_export_filters(
            self, query: dict[str, list[str]]
        ) -> dict[str, str]:
            return {
                name: self._query_value(query, name)
                for name in AUDIT_EXPORT_FILTER_NAMES
                if self._query_value(query, name)
            }

        def _audit_export_record_payload(self, record: AuditRecord) -> dict[str, Any]:
            record_payload = record.to_dict()
            resource = record_payload.get("resource")
            record_payload["resource"] = (
                urlsplit(resource).path if isinstance(resource, str) else ""
            )
            return record_payload

        def _audit_export_query_from_payload(
            self, payload: dict[str, Any]
        ) -> dict[str, list[str]]:
            query: dict[str, list[str]] = {}
            filters = payload.get("filters", {})
            if not isinstance(filters, dict):
                raise AgentOpsError(
                    "AUDIT_EXPORT_FILTERS_INVALID",
                    "Runtime audit export filters are invalid.",
                )
            unknown_filters = set(filters) - set(AUDIT_EXPORT_FILTER_NAMES)
            if unknown_filters:
                raise AgentOpsError(
                    "AUDIT_EXPORT_FILTERS_INVALID",
                    "Runtime audit export filters are invalid.",
                )
            for name in AUDIT_EXPORT_FILTER_NAMES:
                value = filters.get(name)
                if value is None or value == "":
                    continue
                if not isinstance(value, str):
                    raise AgentOpsError(
                        "AUDIT_EXPORT_FILTERS_INVALID",
                        "Runtime audit export filters are invalid.",
                    )
                normalized = value.strip()
                if normalized:
                    query[name] = [normalized]

            limit = payload.get("limit")
            if limit is not None and limit != "":
                if isinstance(limit, bool) or not isinstance(limit, int | str):
                    raise AgentOpsError(
                        "AUDIT_LIMIT_INVALID",
                        "Runtime audit query limit must be a positive integer.",
                    )
                query["limit"] = [str(limit).strip()]
            return query

        def _audit_export_required_string(
            self, payload: dict[str, Any], name: str
        ) -> str:
            value = payload.get(name)
            if not isinstance(value, str) or not value.strip():
                raise AgentOpsError(
                    "AUDIT_EXPORT_MANIFEST_REQUIRED",
                    "Runtime audit export manifest id and digest are required.",
                )
            return value.strip()

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
            expected_signature = (
                hmac.new(
                    signing_secret,
                    serialized_payload,
                    hashlib.sha256,
                )
                .hexdigest()
                .encode("ascii")
            )
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

        def _quality_scorer_external_intake_response(
            self, payload: dict[str, Any]
        ) -> dict[str, Any]:
            agent_id = str(payload.get("agent_id") or "").strip()
            version = str(payload.get("version") or "").strip()
            external_result = payload.get("external_result")
            if not agent_id or not version or not isinstance(external_result, dict):
                raise AgentOpsError(
                    "QUALITY_SCORER_INTAKE_HTTP_REQUEST_INVALID",
                    "Quality scorer external intake HTTP request requires agent_id, version and external_result.",
                    denied_scope="quality_scorer_external_intake_http.request",
                )

            kwargs: dict[str, Any] = {
                "idempotency_key": str(
                    payload.get("idempotency_key")
                    or self.headers.get("Idempotency-Key")
                    or ""
                ),
                "source_trust": str(
                    payload.get("source_trust")
                    or self.headers.get("X-AgentOps-Source-Trust")
                    or "signed"
                ),
                "signature": str(
                    payload.get("signature")
                    or self.headers.get("X-AgentOps-Scorer-Signature")
                    or ""
                ),
                "external_result": external_result,
                "producer": str(payload.get("producer") or "external_scorer_http"),
            }
            if isinstance(payload.get("scorer"), dict):
                kwargs["scorer"] = payload["scorer"]
            if "min_eval_cases" in payload:
                kwargs["min_eval_cases"] = payload["min_eval_cases"]
            if "pass_threshold" in payload:
                kwargs["pass_threshold"] = payload["pass_threshold"]

            return ingest_quality_scorer_external_execution(
                live_repository,
                agent_id,
                version,
                **kwargs,
            )

        def _quality_scorer_external_intake_status(
            self, exc: AgentOpsError
        ) -> HTTPStatus:
            if exc.error_code == "QUALITY_SCORER_INTAKE_SIGNATURE_INVALID":
                return HTTPStatus.UNAUTHORIZED
            if exc.error_code == "QUALITY_SCORER_INTAKE_UNTRUSTED":
                return HTTPStatus.FORBIDDEN
            if exc.error_code == "QUALITY_SCORER_INTAKE_IDEMPOTENCY_CONFLICT":
                return HTTPStatus.CONFLICT
            return HTTPStatus.BAD_REQUEST

        def _quality_scorer_external_intake_read_response(
            self, query: dict[str, list[str]]
        ) -> dict[str, Any]:
            agent_id = self._query_value(query, "agent_id")
            version = self._query_value(query, "version")
            idempotency_key = self._query_value(query, "idempotency_key")
            if not agent_id or not version or not idempotency_key:
                raise AgentOpsError(
                    "QUALITY_SCORER_INTAKE_RECEIPT_QUERY_REQUIRED",
                    "Quality scorer external intake readback requires agent_id, version and idempotency_key.",
                    denied_scope="quality_scorer_external_intake_readback.query",
                )
            receipt = live_repository.quality_scorer_external_receipt_by_idempotency(
                idempotency_key,
                agent_id=agent_id,
                version=version,
            )
            if receipt is None:
                raise AgentOpsError(
                    "QUALITY_SCORER_INTAKE_RECEIPT_NOT_FOUND",
                    "Quality scorer external intake receipt was not found.",
                    denied_scope="quality_scorer_external_intake_readback.receipt",
                    audit_id=(
                        "audit_quality_scorer_external_intake_readback_not_found"
                    ),
                )
            return receipt

        def _quality_scorer_external_intake_read_status(
            self, exc: AgentOpsError
        ) -> HTTPStatus:
            if exc.error_code == "QUALITY_SCORER_INTAKE_RECEIPT_NOT_FOUND":
                return HTTPStatus.NOT_FOUND
            if exc.error_code == "QUALITY_SCORER_INTAKE_IDEMPOTENCY_CONFLICT":
                return HTTPStatus.CONFLICT
            return HTTPStatus.BAD_REQUEST

        def _quality_scorer_external_intake_index_response(
            self, query: dict[str, list[str]]
        ) -> dict[str, Any]:
            agent_id = self._query_value(query, "agent_id")
            version = self._query_value(query, "version")
            if not agent_id or not version:
                raise AgentOpsError(
                    "QUALITY_SCORER_INTAKE_INDEX_QUERY_REQUIRED",
                    "Quality scorer external intake index requires agent_id and version.",
                    denied_scope="quality_scorer_external_intake_index.query",
                )
            limit = self._quality_scorer_external_intake_index_limit(query)
            receipts = live_repository.quality_scorer_external_receipt_records(
                agent_id=agent_id,
                version=version,
                limit=limit,
            )
            audit_hash = hashlib.sha256(
                f"{agent_id}:{version}:{limit}".encode("utf-8")
            ).hexdigest()[:12]
            return {
                "schema_version": "quality_scorer_external_intake_index.v1",
                "route": "/v1/quality/scorers/external-intake/index",
                "method": "GET",
                "agent_id": self._external_intake_safe_query_label(agent_id),
                "version": self._external_intake_safe_query_label(version),
                "limit": limit,
                "returned": len(receipts),
                "receipts": list(receipts),
                "summary": {
                    "summary_only_index": True,
                    "full_scope_required": True,
                    "key_only_lookup_allowed": False,
                    "agentops_scorer_invoked": False,
                    "automatic_rollout_enabled": False,
                    "automatic_template_switch": False,
                    "store_write_performed": False,
                    "notification_sent": False,
                },
                "audit_id": f"audit_quality_scorer_external_intake_index_{audit_hash}",
            }

        def _quality_scorer_external_intake_index_limit(
            self, query: dict[str, list[str]]
        ) -> int:
            raw_limit = self._query_value(query, "limit")
            if not raw_limit:
                return EXTERNAL_INTAKE_INDEX_DEFAULT_LIMIT
            try:
                limit = int(raw_limit)
            except ValueError as exc:
                raise AgentOpsError(
                    "QUALITY_SCORER_INTAKE_INDEX_LIMIT_INVALID",
                    "Quality scorer external intake index limit must be a positive integer.",
                    denied_scope="quality_scorer_external_intake_index.limit",
                ) from exc
            if limit < 1:
                raise AgentOpsError(
                    "QUALITY_SCORER_INTAKE_INDEX_LIMIT_INVALID",
                    "Quality scorer external intake index limit must be a positive integer.",
                    denied_scope="quality_scorer_external_intake_index.limit",
                )
            return min(limit, EXTERNAL_INTAKE_INDEX_MAX_LIMIT)

        def _quality_scorer_external_intake_index_status(
            self, exc: AgentOpsError
        ) -> HTTPStatus:
            return HTTPStatus.BAD_REQUEST

        def _quality_scorer_external_intake_summary_response(
            self, query: dict[str, list[str]]
        ) -> dict[str, Any]:
            agent_id = self._query_value(query, "agent_id")
            version = self._query_value(query, "version")
            if not agent_id or not version:
                raise AgentOpsError(
                    "QUALITY_SCORER_INTAKE_SUMMARY_QUERY_REQUIRED",
                    "Quality scorer external intake summary requires agent_id and version.",
                    denied_scope="quality_scorer_external_intake_summary.query",
                )
            limit = self._quality_scorer_external_intake_summary_limit(query)
            receipts = live_repository.quality_scorer_external_receipt_records(
                agent_id=agent_id,
                version=version,
                limit=limit,
            )
            audit_hash = hashlib.sha256(
                f"{agent_id}:{version}:{limit}".encode("utf-8")
            ).hexdigest()[:12]
            latest_receipt = receipts[0] if receipts else None
            return {
                "schema_version": "quality_scorer_external_intake_summary.v1",
                "route": "/v1/quality/scorers/external-intake/summary",
                "method": "GET",
                "agent_id": self._external_intake_safe_query_label(agent_id),
                "version": self._external_intake_safe_query_label(version),
                "window_limit": limit,
                "receipt_count": len(receipts),
                "health_state": self._quality_scorer_external_intake_health_state(
                    receipts
                ),
                "latest_receipt": latest_receipt or {},
                "latest_received_at": (
                    str(latest_receipt.get("received_at") or "")
                    if latest_receipt
                    else ""
                ),
                "latest_pass_rate": (
                    latest_receipt.get("pass_rate", 0.0) if latest_receipt else 0.0
                ),
                "latest_sample_size": (
                    latest_receipt.get("sample_size", 0) if latest_receipt else 0
                ),
                "intake_state_counts": self._external_intake_counts(
                    receipts,
                    "intake_state",
                ),
                "source_trust_counts": self._external_intake_counts(
                    receipts,
                    "source_trust",
                ),
                "accepted_execution_count": sum(
                    1 for receipt in receipts if receipt.get("accepted_execution_id")
                ),
                "scorer_refs": self._external_intake_scorer_refs(receipts),
                "summary": {
                    "summary_only_intake_summary": True,
                    "full_scope_required": True,
                    "key_only_lookup_allowed": False,
                    "agentops_scorer_invoked": False,
                    "automatic_rollout_enabled": False,
                    "automatic_template_switch": False,
                    "automatic_lifecycle_action": False,
                    "store_write_performed": False,
                    "notification_sent": False,
                },
                "audit_id": (
                    f"audit_quality_scorer_external_intake_summary_{audit_hash}"
                ),
            }

        def _quality_scorer_external_intake_summary_limit(
            self, query: dict[str, list[str]]
        ) -> int:
            raw_limit = self._query_value(query, "limit")
            if not raw_limit:
                return EXTERNAL_INTAKE_SUMMARY_DEFAULT_LIMIT
            try:
                limit = int(raw_limit)
            except ValueError as exc:
                raise AgentOpsError(
                    "QUALITY_SCORER_INTAKE_SUMMARY_LIMIT_INVALID",
                    "Quality scorer external intake summary limit must be a positive integer.",
                    denied_scope="quality_scorer_external_intake_summary.limit",
                ) from exc
            if limit < 1:
                raise AgentOpsError(
                    "QUALITY_SCORER_INTAKE_SUMMARY_LIMIT_INVALID",
                    "Quality scorer external intake summary limit must be a positive integer.",
                    denied_scope="quality_scorer_external_intake_summary.limit",
                )
            return min(limit, EXTERNAL_INTAKE_SUMMARY_MAX_LIMIT)

        def _quality_scorer_external_intake_summary_status(
            self, exc: AgentOpsError
        ) -> HTTPStatus:
            return HTTPStatus.BAD_REQUEST

        def _quality_center_external_intake_portfolio_response(
            self, query: dict[str, list[str]]
        ) -> dict[str, Any]:
            limit = self._quality_center_external_intake_portfolio_limit(query)
            scope_values = self._query_values(query, "scope")
            if not scope_values:
                raise AgentOpsError(
                    "QUALITY_CENTER_INTAKE_PORTFOLIO_SCOPE_REQUIRED",
                    "Quality Center external intake portfolio requires at least one scope=agent_id@version query value.",
                    denied_scope="quality_center_external_intake_portfolio.scope",
                )
            required_scopes = {
                (item["agent_id"], item["version"])
                for item in self._quality_center_external_intake_scope_refs(
                    self._query_values(query, "required_scope"),
                    field_name="required_scope",
                )
            }
            scope_refs = self._quality_center_external_intake_scope_refs(
                scope_values,
                field_name="scope",
            )[:limit]
            agent_refs = [
                {
                    "agent_id": item["agent_id"],
                    "version": item["version"],
                    "external_intake_required": (
                        item["agent_id"],
                        item["version"],
                    )
                    in required_scopes,
                }
                for item in scope_refs
            ]
            report_period = self._query_value(query, "report_period") or "http"
            portfolio = get_quality_center_external_intake_portfolio(
                live_repository,
                report_period=report_period,
                generated_by="quality_center_http",
                agent_refs=agent_refs,
            )
            audit_hash = hashlib.sha256(
                json.dumps(
                    {
                        "scope_hashes": [
                            self._quality_center_external_intake_scope_hash(item)
                            for item in scope_refs
                        ],
                        "required_hashes": [
                            self._quality_center_external_intake_scope_hash(
                                {
                                    "agent_id": agent_id,
                                    "version": version,
                                }
                            )
                            for agent_id, version in sorted(required_scopes)
                        ],
                        "limit": limit,
                    },
                    sort_keys=True,
                ).encode("utf-8")
            ).hexdigest()[:12]
            return {
                "schema_version": "quality_center_external_intake_portfolio_http.v1",
                "route": "/v1/quality/center/external-intake/portfolio",
                "method": "GET",
                "window_limit": limit,
                "requested_scope_count": len(scope_values),
                "returned_scope_count": len(agent_refs),
                "portfolio": portfolio,
                "summary": {
                    "summary_only_portfolio_http": True,
                    "request_body_read": False,
                    "query_payload_recorded": False,
                    "agentops_scorer_invoked": False,
                    "automatic_rollout_enabled": False,
                    "automatic_template_switch": False,
                    "automatic_lifecycle_action": False,
                    "store_write_performed": False,
                    "notification_sent": False,
                },
                "audit_id": (
                    f"audit_quality_center_external_intake_portfolio_{audit_hash}"
                ),
            }

        def _quality_center_external_intake_portfolio_limit(
            self, query: dict[str, list[str]]
        ) -> int:
            raw_limit = self._query_value(query, "limit")
            if not raw_limit:
                return QUALITY_CENTER_PORTFOLIO_SCOPE_DEFAULT_LIMIT
            try:
                limit = int(raw_limit)
            except ValueError as exc:
                raise AgentOpsError(
                    "QUALITY_CENTER_INTAKE_PORTFOLIO_LIMIT_INVALID",
                    "Quality Center external intake portfolio limit must be a positive integer.",
                    denied_scope="quality_center_external_intake_portfolio.limit",
                ) from exc
            if limit < 1:
                raise AgentOpsError(
                    "QUALITY_CENTER_INTAKE_PORTFOLIO_LIMIT_INVALID",
                    "Quality Center external intake portfolio limit must be a positive integer.",
                    denied_scope="quality_center_external_intake_portfolio.limit",
                )
            return min(limit, QUALITY_CENTER_PORTFOLIO_SCOPE_MAX_LIMIT)

        def _quality_center_external_intake_scope_refs(
            self,
            values: list[str],
            *,
            field_name: str,
        ) -> list[dict[str, str]]:
            refs: list[dict[str, str]] = []
            seen: set[tuple[str, str]] = set()
            for raw_value in values:
                agent_id, separator, version = str(raw_value or "").rpartition("@")
                if not separator or not agent_id or not version:
                    raise AgentOpsError(
                        "QUALITY_CENTER_INTAKE_PORTFOLIO_SCOPE_INVALID",
                        "Quality Center external intake portfolio scopes must use agent_id@version.",
                        denied_scope=(
                            f"quality_center_external_intake_portfolio.{field_name}"
                        ),
                    )
                key = (agent_id, version)
                if key in seen:
                    continue
                seen.add(key)
                refs.append({"agent_id": agent_id, "version": version})
            return refs

        def _quality_center_external_intake_scope_hash(
            self,
            scope_ref: dict[str, str],
        ) -> dict[str, str]:
            return {
                "agent_id_hash": hashlib.sha256(
                    f"agent_id\x00{scope_ref['agent_id']}".encode("utf-8")
                ).hexdigest(),
                "version_hash": hashlib.sha256(
                    f"version\x00{scope_ref['version']}".encode("utf-8")
                ).hexdigest(),
            }

        def _quality_center_external_intake_portfolio_status(
            self, exc: AgentOpsError
        ) -> HTTPStatus:
            return HTTPStatus.BAD_REQUEST

        def _quality_scorer_external_intake_health_state(
            self,
            receipts: tuple[dict[str, Any], ...],
        ) -> str:
            if not receipts:
                return "no_receipts"
            latest = receipts[0]
            if str(latest.get("intake_state") or "") == "accepted":
                return "receiving"
            return "needs_review"

        def _external_intake_counts(
            self,
            receipts: tuple[dict[str, Any], ...],
            field_name: str,
        ) -> dict[str, int]:
            counts: dict[str, int] = {}
            for receipt in receipts:
                value = str(receipt.get(field_name) or "unknown")
                counts[value] = counts.get(value, 0) + 1
            return counts

        def _external_intake_scorer_refs(
            self,
            receipts: tuple[dict[str, Any], ...],
        ) -> list[dict[str, str]]:
            refs: list[dict[str, str]] = []
            seen: set[tuple[str, str, str]] = set()
            for receipt in receipts:
                scorer = receipt.get("scorer") if isinstance(receipt, dict) else {}
                if not isinstance(scorer, dict):
                    continue
                ref = (
                    str(scorer.get("scorer_id") or ""),
                    str(scorer.get("scorer_version") or ""),
                    str(scorer.get("score_template_id") or ""),
                )
                if ref in seen:
                    continue
                seen.add(ref)
                refs.append(
                    {
                        "scorer_id": ref[0],
                        "scorer_version": ref[1],
                        "score_template_id": ref[2],
                    }
                )
            return refs

        def _external_intake_query_contains_forbidden(self, *values: str) -> bool:
            for value in values:
                normalized = value.lower()
                if any(
                    marker in normalized
                    for marker in EXTERNAL_INTAKE_FORBIDDEN_QUERY_MARKERS
                ):
                    return True
            return False

        def _external_intake_safe_query_label(self, value: str) -> str:
            if self._external_intake_query_contains_forbidden(value):
                return "[redacted]"
            return value[:80]

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
            if origin in _allowed_origins():
                self.send_header("Access-Control-Allow-Origin", origin)
            self.send_header("Access-Control-Allow-Methods", "GET, POST, OPTIONS")
            allowed_headers = (
                "Content-Type, Idempotency-Key, X-AgentOps-Scorer-Signature, "
                "X-AgentOps-Source-Trust"
            )
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


def _allowed_origins() -> set[str]:
    configured = os.getenv(ALLOWED_ORIGINS_ENV, "")
    if not configured.strip():
        return set(DEFAULT_ALLOWED_ORIGINS)
    origins = {origin.strip() for origin in configured.split(",") if origin.strip()}
    return origins or set(DEFAULT_ALLOWED_ORIGINS)


def run_server(
    host: str = "127.0.0.1", port: int = 8765, *, require_auth: bool = False
) -> None:
    repository = repository_from_env(require_auth=require_auth)
    httpd = ThreadingHTTPServer(
        (host, port), create_http_handler(repository, require_auth=require_auth)
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
