from __future__ import annotations

import json
import threading
import time
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, HTTPServer
from typing import Any, ClassVar

import structlog

logger = structlog.get_logger()

# Module-level boot timestamp — set once when the server starts.
_boot_time: float = 0.0


class _HealthHandler(BaseHTTPRequestHandler):
    """Minimal HTTP handler that responds to ``GET /healthz``."""

    # Suppress default request logging (structlog handles it).
    def log_message(self, format: str, *args: Any) -> None:  # noqa: A002
        return

    # ---------- routes ----------

    _routes: ClassVar[dict[str, str]] = {
        "/healthz": "_handle_healthz",
        "/readyz": "_handle_readyz",
    }

    def do_GET(self) -> None:  # noqa: N802
        handler_name = self._routes.get(self.path)
        if handler_name is not None:
            getattr(self, handler_name)()
        else:
            self._respond(HTTPStatus.NOT_FOUND, {"error": "not found"})

    # ---------- health / ready ----------

    def _handle_healthz(self) -> None:
        """Liveness probe — always OK if the process is running."""
        uptime = time.time() - _boot_time
        self._respond(HTTPStatus.OK, {"status": "ok", "uptime_seconds": round(uptime, 1)})

    def _handle_readyz(self) -> None:
        """Readiness probe — confirms the app can serve traffic."""
        self._respond(HTTPStatus.OK, {"status": "ready"})

    # ---------- helpers ----------

    def _respond(self, status: HTTPStatus, body: dict[str, Any]) -> None:

        payload = json.dumps(body).encode()
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(payload)))
        self.end_headers()
        self.wfile.write(payload)


def start_healthcheck_server(port: int = 8080) -> HTTPServer:
    """Start a background HTTP server for ECS / ALB health checks.

    Returns the ``HTTPServer`` instance so callers can shut it down if needed.

    Args:
        port: TCP port to bind on (default ``8080``).
    """
    global _boot_time  # noqa: PLW0603
    _boot_time = time.time()

    server = HTTPServer(("", port), _HealthHandler)
    thread = threading.Thread(target=server.serve_forever, daemon=True, name="healthcheck")
    thread.start()
    logger.info("healthcheck_server_started", port=port)
    return server
