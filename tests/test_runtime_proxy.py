"""Opt-in real-nginx checks: RUN_NGINX_TESTS=true python -m pytest ... --no-cov.

Requires Docker and the nginx:stable-alpine image. Runs the repository's exact
API location block, without production TLS certificates or static-site paths.
"""

from contextlib import contextmanager
import os
from pathlib import Path
import socket
import subprocess
import time

import httpx
import pytest

from runtime_support import MetricsSnapshot, eventually, runtime_server


pytestmark = pytest.mark.skipif(
    os.environ.get("RUN_NGINX_TESTS") != "true", reason="Requires opt-in Docker/nginx runtime"
)
ROOT = Path(__file__).resolve().parents[1]
CONTACT = "/api/v1/astronomical-events/contact-times"
PAYLOAD = {"event_date": "2026-08-12 01:45:00.000", "is_lunar": False}


@contextmanager
def proxy(tmp_path, upstream_port, config_path):
    """Keep the supplied location's directives; change only the upstream address."""
    location = (ROOT / config_path).read_text(encoding="utf-8").split(
        "location /api/ {", 1
    )[1].split("}", 1)[0].replace("127.0.0.1:8000", f"127.0.0.1:{upstream_port}")
    # The client must not share the trusted upstream proxy's loopback address.
    # Otherwise every hop is trusted and removing that chain cannot identify a client.
    host = subprocess.check_output(
        ["docker", "network", "inspect", "bridge", "--format",
         "{{range .IPAM.Config}}{{.Gateway}}{{end}}"], text=True,
    ).strip()
    with socket.socket() as listener:
        listener.bind((host, 0))
        port = listener.getsockname()[1]
    config = tmp_path / "nginx.conf"
    config.write_text(
        "events {}\nhttp { access_log off; server {\n"
        f"listen {host}:{port};\nlocation /api/ {{ {location} }}\n"
        "} }\n", encoding="utf-8",
    )
    name = f"castle-runtime-test-{port}"
    command = [
        "docker", "run", "--rm", "--network", "host", "--name", name,
        "--mount", f"type=bind,src={config},dst=/etc/nginx/nginx.conf,readonly",
        "nginx:stable-alpine", "nginx", "-g", "daemon off;",
    ]
    with (tmp_path / "nginx.log").open("w+", encoding="utf-8") as log:
        process = subprocess.Popen(command, stdout=log, stderr=log)
        try:
            deadline = time.monotonic() + 10
            with httpx.Client(base_url=f"http://{host}:{port}", trust_env=False) as client:
                while True:
                    assert process.poll() is None, (tmp_path / "nginx.log").read_text()
                    try:
                        response = client.get("/api/metrics")
                    except httpx.ConnectError:
                        assert time.monotonic() < deadline, "nginx startup timed out"
                        time.sleep(0.05)
                    else:
                        response.raise_for_status()
                        break
                yield client
        finally:
            removed = subprocess.run(
                ["docker", "rm", "--force", name], capture_output=True, text=True, check=False
            )
            process.wait(timeout=10)
            assert removed.returncode == 0, removed.stderr


@pytest.mark.parametrize("config", [
    "scripts/castle-celestial.nginx.conf", "frontend/tests/Hosting/celestial-view",
])
def test_proxy_timeout_and_unspoofable_client_ip(tmp_path, config):
    with runtime_server(
        tmp_path, LIMIT_CONTACT_TIMES="1/minute", TRUSTED_PROXIES="127.0.0.1",
        TEST_RUNTIME_BUDGET="0.3", TEST_RUNTIME_BLOCK_CONTACT="true",
    ) as (backend, _):
        with proxy(tmp_path, backend.base_url.port, config) as frontend:
            before = MetricsSnapshot.scrape(backend)
            response = frontend.post(CONTACT, json=PAYLOAD)
            assert response.status_code == 503, response.text
            assert response.json()["timeout_seconds"] == 0.3
            assert frontend.post(CONTACT, json=PAYLOAD).status_code == 429
            assert frontend.post(
                CONTACT, json=PAYLOAD, headers={"X-Forwarded-For": "203.0.113.99"}
            ).status_code == 429
            backend.post("/__test/release").raise_for_status()
            eventually(lambda: MetricsSnapshot.scrape(backend).value(
                "abandoned_work_in_progress", endpoint=CONTACT
            ) == 0)
            after = MetricsSnapshot.scrape(backend)
            assert after.delta(
                before, "abandoned_work_total", endpoint=CONTACT, reason="timeout"
            ) == 1
            assert after.delta(before, "rate_limit_exceeded_total", endpoint=CONTACT) == 2


@pytest.mark.parametrize("config", [
    "scripts/castle-celestial.nginx.conf", "frontend/tests/Hosting/celestial-view",
])
def test_proxy_propagates_disconnect(tmp_path, config):
    with runtime_server(
        tmp_path, TRUSTED_PROXIES="127.0.0.1", TEST_RUNTIME_BLOCK_CONTACT="true",
    ) as (backend, _):
        with proxy(tmp_path, backend.base_url.port, config) as frontend:
            before = MetricsSnapshot.scrape(backend)
            connection = socket.socket()
            try:
                connection.connect((frontend.base_url.host, frontend.base_url.port))
                body = b'{"event_date":"2026-08-12 01:45:00.000","is_lunar":false}'
                connection.sendall(
                    f"POST {CONTACT} HTTP/1.1\r\nHost: localhost\r\n"
                    f"Content-Type: application/json\r\nContent-Length: {len(body)}\r\n\r\n".encode()
                    + body
                )
                eventually(lambda: backend.get("/__test/state").json()["contact_started"] == 1)
                connection.shutdown(socket.SHUT_RDWR)
            finally:
                connection.close()
            # Let nginx propagate the close upstream before releasing computation.
            time.sleep(0.05)
            backend.post("/__test/release").raise_for_status()
            eventually(lambda: MetricsSnapshot.scrape(backend).value(
                "abandoned_work_total", endpoint=CONTACT, reason="client_disconnect"
            ) == 1)
            eventually(lambda: MetricsSnapshot.scrape(backend).value(
                "abandoned_work_in_progress", endpoint=CONTACT
            ) == 0)
            after = MetricsSnapshot.scrape(backend)
            assert after.delta(
                before, "abandoned_work_total", endpoint=CONTACT, reason="timeout"
            ) == 0
            assert not after.endpoints("errors_total")


@pytest.mark.skipif(
    os.environ.get("RUN_LONG_NGINX_TESTS") != "true", reason="Opt-in 130-second request"
)
def test_proxy_allows_request_longer_than_old_timeout(tmp_path):
    with runtime_server(
        tmp_path, TEST_RUNTIME_BUDGET="150", TEST_RUNTIME_DELAY="130"
    ) as (backend, _):
        with proxy(
            tmp_path, backend.base_url.port, "scripts/castle-celestial.nginx.conf"
        ) as frontend:
            started = time.monotonic()
            response = frontend.post(CONTACT, json=PAYLOAD, timeout=145)
            assert response.status_code == 200, response.text
            assert 129 <= time.monotonic() - started < 145
            assert response.json()["contact_times"]
