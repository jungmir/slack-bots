from __future__ import annotations

import json
import urllib.request

from src.healthcheck import start_healthcheck_server


def test_healthz_returns_ok() -> None:
    """GET /healthz should return 200 with status ok."""
    server = start_healthcheck_server(port=0)  # OS picks a free port
    try:
        port = server.server_address[1]
        with urllib.request.urlopen(f"http://127.0.0.1:{port}/healthz") as resp:
            assert resp.status == 200
            data = json.loads(resp.read())
            assert data["status"] == "ok"
            assert "uptime_seconds" in data
    finally:
        server.shutdown()


def test_readyz_returns_ready() -> None:
    """GET /readyz should return 200 with status ready."""
    server = start_healthcheck_server(port=0)
    try:
        port = server.server_address[1]
        with urllib.request.urlopen(f"http://127.0.0.1:{port}/readyz") as resp:
            assert resp.status == 200
            data = json.loads(resp.read())
            assert data["status"] == "ready"
    finally:
        server.shutdown()


def test_unknown_path_returns_404() -> None:
    """GET on an unknown path should return 404."""
    server = start_healthcheck_server(port=0)
    try:
        port = server.server_address[1]
        try:
            urllib.request.urlopen(f"http://127.0.0.1:{port}/unknown")
        except urllib.error.HTTPError as exc:
            assert exc.code == 404
            data = json.loads(exc.read())
            assert data["error"] == "not found"
    finally:
        server.shutdown()
