"""Serve the Prediction Control Room locally over a deliberately read-only HTTP surface.

Input: a repository root and local bind address.
Output: static dashboard assets plus safe JSON snapshot/health endpoints.
Non-goals: write APIs, remote deployment, external polling, task execution, or trading.
"""

from __future__ import annotations

import argparse
import json
import mimetypes
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import urlparse

from .model import SNAPSHOT_SCHEMA, build_snapshot

STATIC_ROOT = Path(__file__).with_name("static")


class ControlRoomHandler(BaseHTTPRequestHandler):
    """GET/HEAD-only handler; every mutating HTTP verb is rejected."""

    server_version = "PredictionControlRoom/0"

    def _security_headers(self, content_type: str, length: int, status: int = 200) -> None:
        self.send_response(status)
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(length))
        self.send_header("Cache-Control", "no-store")
        self.send_header("X-Content-Type-Options", "nosniff")
        self.send_header("X-Frame-Options", "DENY")
        self.send_header("Referrer-Policy", "no-referrer")
        self.send_header(
            "Content-Security-Policy",
            "default-src 'self'; script-src 'self'; style-src 'self'; connect-src 'self'; img-src 'self' data:; frame-ancestors 'none'; base-uri 'none'; form-action 'none'",
        )
        self.end_headers()

    def _send_bytes(self, body: bytes, content_type: str, status: int = 200, head_only: bool = False) -> None:
        self._security_headers(content_type, len(body), status=status)
        if not head_only:
            self.wfile.write(body)

    def _send_json(self, payload: dict, status: int = 200, head_only: bool = False) -> None:
        body = json.dumps(payload, ensure_ascii=False, separators=(",", ":")).encode("utf-8")
        self._send_bytes(body, "application/json; charset=utf-8", status=status, head_only=head_only)

    def _dispatch_read(self, head_only: bool = False) -> None:
        parsed = urlparse(self.path)
        if parsed.path == "/api/snapshot":
            self._send_json(build_snapshot(self.server.repo_root), head_only=head_only)  # type: ignore[attr-defined]
            return
        if parsed.path == "/api/health":
            self._send_json(
                {
                    "status": "ok",
                    "schema": SNAPSHOT_SCHEMA,
                    "read_only": True,
                    "outbound_network_calls": False,
                    "mutation_endpoints": False,
                },
                head_only=head_only,
            )
            return

        path = parsed.path
        if path == "/":
            path = "/index.html"
        safe_name = path.lstrip("/")
        if safe_name not in {"index.html", "app.js", "styles.css"}:
            self._send_json({"error": "not_found"}, status=404, head_only=head_only)
            return
        file_path = STATIC_ROOT / safe_name
        try:
            body = file_path.read_bytes()
        except OSError:
            self._send_json({"error": "asset_unavailable"}, status=500, head_only=head_only)
            return
        content_type = mimetypes.guess_type(str(file_path))[0] or "application/octet-stream"
        if content_type.startswith("text/") or content_type == "application/javascript":
            content_type += "; charset=utf-8"
        self._send_bytes(body, content_type, head_only=head_only)

    def do_GET(self) -> None:  # noqa: N802
        self._dispatch_read(False)

    def do_HEAD(self) -> None:  # noqa: N802
        self._dispatch_read(True)

    def _reject_mutation(self) -> None:
        body = json.dumps({"error": "method_not_allowed", "read_only": True}).encode("utf-8")
        self.send_response(405)
        self.send_header("Allow", "GET, HEAD")
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        self.wfile.write(body)

    do_POST = _reject_mutation  # type: ignore[assignment]
    do_PUT = _reject_mutation  # type: ignore[assignment]
    do_PATCH = _reject_mutation  # type: ignore[assignment]
    do_DELETE = _reject_mutation  # type: ignore[assignment]

    def log_message(self, format: str, *args: object) -> None:
        if getattr(self.server, "quiet", False):  # type: ignore[attr-defined]
            return
        super().log_message(format, *args)


class ControlRoomServer(ThreadingHTTPServer):
    """Threaded local server carrying only immutable configuration references."""

    daemon_threads = True

    def __init__(self, address: tuple[str, int], repo_root: Path, quiet: bool = False):
        super().__init__(address, ControlRoomHandler)
        self.repo_root = repo_root.resolve()
        self.quiet = quiet


def make_server(repo_root: str | Path, host: str = "127.0.0.1", port: int = 8765, quiet: bool = False) -> ControlRoomServer:
    """Create but do not start a local read-only dashboard server."""
    return ControlRoomServer((host, port), Path(repo_root), quiet=quiet)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Local read-only Prediction Control Room V0")
    parser.add_argument("--repo-root", default=".", help="Research-OS repository root")
    parser.add_argument("--host", default="127.0.0.1", help="Bind host; default is local-only")
    parser.add_argument("--port", default=8765, type=int, help="TCP port")
    parser.add_argument("--quiet", action="store_true", help="Suppress HTTP access log")
    args = parser.parse_args(argv)

    server = make_server(args.repo_root, args.host, args.port, quiet=args.quiet)
    host, port = server.server_address
    print(f"Prediction Control Room V0: http://{host}:{port}")
    print("READ-ONLY | no external polling | Ctrl+C to stop")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()
    return 0
