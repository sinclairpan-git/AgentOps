"""Minimal standard-library HTTP API for local AgentOps Console integration."""

from __future__ import annotations

import argparse
import json
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from typing import Any
from urllib.parse import urlsplit

from agentops import __version__
from agentops.api.ingestion import ingest_events_batch
from agentops.api.console_snapshot import build_console_snapshot
from agentops.storage.repository import InMemoryRepository

ALLOWED_ORIGINS = {
    "http://127.0.0.1:5173",
    "http://127.0.0.1:5174",
    "http://localhost:5173",
    "http://localhost:5174",
}


def create_http_handler(repository: InMemoryRepository | None = None) -> type[BaseHTTPRequestHandler]:
    live_repository = repository or InMemoryRepository()

    class AgentOpsRequestHandler(BaseHTTPRequestHandler):
        server_version = "AgentOpsHTTP/0.1"

        def do_OPTIONS(self) -> None:  # noqa: N802
            if not self._origin_allowed():
                self._send_json(
                    HTTPStatus.FORBIDDEN,
                    {"error_code": "ORIGIN_FORBIDDEN", "message": "请求来源不在本地开发白名单内。"},
                )
                return
            self._send_json(HTTPStatus.NO_CONTENT, {})

        def do_GET(self) -> None:  # noqa: N802
            if not self._origin_allowed():
                self._send_json(
                    HTTPStatus.FORBIDDEN,
                    {"error_code": "ORIGIN_FORBIDDEN", "message": "请求来源不在本地开发白名单内。"},
                )
                return

            request_path = self._request_path()
            if request_path == "/v1/health":
                self._send_json(
                    HTTPStatus.OK,
                    {"service": "agentops-api", "status": "healthy", "version": __version__, "snapshot_provider": "ready"},
                )
                return

            if request_path == "/v1/console/snapshot":
                self._send_json(HTTPStatus.OK, build_console_snapshot(repository=live_repository))
                return

            self._send_json(
                HTTPStatus.NOT_FOUND,
                {"error_code": "NOT_FOUND", "message": "未找到请求的 AgentOps API 路径。"},
            )

        def do_POST(self) -> None:  # noqa: N802
            if not self._origin_allowed():
                self._send_json(
                    HTTPStatus.FORBIDDEN,
                    {"error_code": "ORIGIN_FORBIDDEN", "message": "请求来源不在本地开发白名单内。"},
                )
                return

            request_path = self._request_path()
            if request_path in {"/v1/events", "/v1/events/batch"}:
                payload = self._read_json()
                if payload is None:
                    self._send_json(
                        HTTPStatus.BAD_REQUEST,
                        {"error_code": "REQUEST_JSON_INVALID", "message": "请求体必须是 JSON。"},
                    )
                    return
                events = payload.get("events") if isinstance(payload, dict) else None
                if not isinstance(events, list):
                    self._send_json(
                        HTTPStatus.BAD_REQUEST,
                        {"error_code": "EVENTS_REQUIRED", "message": "请求体必须包含 events 数组。"},
                    )
                    return
                outcome = ingest_events_batch(events, live_repository)
                status = HTTPStatus.ACCEPTED if outcome["accepted"] or outcome["deduplicated"] else HTTPStatus.BAD_REQUEST
                self._send_json(status, outcome)
                return

            self._send_json(
                HTTPStatus.NOT_FOUND,
                {"error_code": "NOT_FOUND", "message": "未找到请求的 AgentOps API 路径。"},
            )

        def log_message(self, format: str, *args: Any) -> None:
            return

        def _origin_allowed(self) -> bool:
            origin = self.headers.get("Origin")
            return origin is None or origin in ALLOWED_ORIGINS

        def _request_path(self) -> str:
            return urlsplit(self.path).path

        def _read_json(self) -> dict[str, Any] | None:
            try:
                content_length = int(self.headers.get("Content-Length", "0"))
                body = self.rfile.read(content_length) if content_length else b"{}"
                payload = json.loads(body.decode("utf-8"))
                return payload if isinstance(payload, dict) else None
            except (UnicodeDecodeError, json.JSONDecodeError, ValueError):
                return None

        def _send_json(self, status: HTTPStatus, payload: dict[str, Any]) -> None:
            body = b"" if status == HTTPStatus.NO_CONTENT else json.dumps(payload, ensure_ascii=False).encode("utf-8")
            origin = self.headers.get("Origin")
            self.send_response(status)
            self.send_header("Content-Type", "application/json; charset=utf-8")
            if origin in ALLOWED_ORIGINS:
                self.send_header("Access-Control-Allow-Origin", origin)
            self.send_header("Access-Control-Allow-Methods", "GET, POST, OPTIONS")
            self.send_header("Access-Control-Allow-Headers", "Content-Type")
            self.send_header("Cache-Control", "no-store")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            if body:
                self.wfile.write(body)

    return AgentOpsRequestHandler


def run_server(host: str = "127.0.0.1", port: int = 8765) -> None:
    httpd = ThreadingHTTPServer((host, port), create_http_handler())
    print(f"AgentOps API listening on http://{host}:{port}")  # noqa: T201
    httpd.serve_forever()


def main() -> None:
    parser = argparse.ArgumentParser(description="Start the local AgentOps API server.")
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", default=8765, type=int)
    args = parser.parse_args()
    run_server(host=args.host, port=args.port)


if __name__ == "__main__":
    main()
