"""Minimal standard-library HTTP API for local AgentOps Console integration."""

from __future__ import annotations

import argparse
import json
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from typing import Any

from agentops import __version__
from agentops.api.console_snapshot import build_console_snapshot

ALLOWED_ORIGINS = {
    "http://127.0.0.1:5173",
    "http://127.0.0.1:5174",
    "http://localhost:5173",
    "http://localhost:5174",
}


def create_http_handler() -> type[BaseHTTPRequestHandler]:
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

            if self.path == "/v1/health":
                self._send_json(
                    HTTPStatus.OK,
                    {"service": "agentops-api", "status": "healthy", "version": __version__, "snapshot_provider": "ready"},
                )
                return

            if self.path == "/v1/console/snapshot":
                self._send_json(HTTPStatus.OK, build_console_snapshot())
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

        def _send_json(self, status: HTTPStatus, payload: dict[str, Any]) -> None:
            body = b"" if status == HTTPStatus.NO_CONTENT else json.dumps(payload, ensure_ascii=False).encode("utf-8")
            origin = self.headers.get("Origin")
            self.send_response(status)
            self.send_header("Content-Type", "application/json; charset=utf-8")
            if origin in ALLOWED_ORIGINS:
                self.send_header("Access-Control-Allow-Origin", origin)
            self.send_header("Access-Control-Allow-Methods", "GET, OPTIONS")
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
