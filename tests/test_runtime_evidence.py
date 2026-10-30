"""Wire-level evidence with real rate limits, production middleware and Prometheus."""

from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
import re
import sys
import time

import pytest

from runtime_support import MetricsSnapshot, eventually, runtime_server


CONTACT = "/api/v1/astronomical-events/contact-times"
STREAM = "/api/v1/astronomical-events-stream"
CONTACT_LABEL = "get_contact_times_route"
PAYLOAD = {"event_date": "2026-08-12 01:45:00.000", "is_lunar": False}
DATE_RANGE = {"start_date": "2026-08-01", "end_date": "2026-08-31"}
STREAM_URL = STREAM + "?start_date=2026-08-01&end_date=2026-08-31"


def scrape(client):
    return MetricsSnapshot.scrape(client)


@pytest.mark.parametrize(
    ("limit", "path", "payload"),
    [
        ("LIMIT_CONTACT_TIMES", CONTACT, PAYLOAD),
        ("LIMIT_EXPENSIVE_EVENTS", "/api/v1/astronomical-events", DATE_RANGE),
        ("LIMIT_CHEAP", "/api/v1/day-of-week", {"date": "2026-08-12"}),
        ("LIMIT_STREAM_EVENTS", STREAM_URL, None),
        ("LIMIT_EXPENSIVE_BATCH", "/api/v1/batch-earth-observations", {
            "start_date": "2026-08-12", "end_date": "2026-08-12",
            "start_time": "00:00:00", "end_time": "00:01:00", "frame_count": 2,
            "latitude": 0, "longitude": 0,
        }),
    ],
)
def test_real_route_limits_and_exact_metrics(tmp_path, limit, path, payload):
    """Real decorators/handler, including cache hits, must reject the third start."""
    with runtime_server(tmp_path, **{limit: "2/minute"}) as (client, _):
        before = scrape(client)
        for _ in range(2):
            response = client.get(path) if payload is None else client.post(path, json=payload)
            assert response.status_code == 200, response.text
        response = client.get(path) if payload is None else client.post(path, json=payload)
        assert response.status_code == 429
        assert response.json()["error"] == "rate_limit_exceeded"
        assert int(response.headers["Retry-After"]) == response.json()["retry_after"] > 0
        endpoint = path.split("?")[0]
        after = scrape(client)
        assert after.delta(before, "rate_limit_exceeded_total", endpoint=endpoint) == 1
        assert after.delta(
            before, "errors_total", endpoint=endpoint, error_type="rate_limited", status="429"
        ) == 1
        assert after.delta(
            before, "http_requests_total", endpoint=endpoint,
            method="GET" if payload is None else "POST", status="429"
        ) == 1
        assert after.delta(
            before, "errors_total", endpoint=endpoint,
            error_type="unhandled_exception", status="500"
        ) == 0


@pytest.mark.parametrize("trusted", [True, False])
def test_forwarded_clients_only_isolated_when_peer_trusted(tmp_path, trusted):
    with runtime_server(
        tmp_path, LIMIT_CONTACT_TIMES="1/minute",
        TRUSTED_PROXIES="127.0.0.1" if trusted else "",
    ) as (client, _):
        def request(forwarded):
            return client.post(CONTACT, json=PAYLOAD, headers={"X-Forwarded-For": forwarded})

        assert request("198.51.100.1, 203.0.113.1").status_code == 200
        # Changing a spoofed leftmost address must never bypass the same real client's limit.
        assert request("198.51.100.2, 203.0.113.1").status_code == 429
        assert request("203.0.113.2").status_code == (200 if trusted else 429)


def test_limits_disabled_in_actual_process(tmp_path):
    with runtime_server(
        tmp_path, RATE_LIMIT_ENABLED="false", LIMIT_CONTACT_TIMES="1/minute"
    ) as (client, _):
        before = scrape(client)
        assert [client.post(CONTACT, json=PAYLOAD).status_code for _ in range(4)] == [200] * 4
        after = scrape(client)
        assert after.delta(before, "rate_limit_exceeded_total", endpoint=CONTACT) == 0
        assert after.delta(
            before, "errors_total", endpoint=CONTACT, error_type="rate_limited", status="429"
        ) == 0


def test_real_fixed_window_resets(tmp_path):
    with runtime_server(tmp_path, LIMIT_CONTACT_TIMES="1/second") as (client, _):
        assert client.post(CONTACT, json=PAYLOAD).status_code == 200
        assert client.post(CONTACT, json=PAYLOAD).status_code == 429
        time.sleep(1.05)
        assert client.post(CONTACT, json=PAYLOAD).status_code == 200


def test_live_deadline_retry_and_background_cache_metrics(tmp_path):
    """Hold the thread until both 503s arrive: no timing proxy for unfinished work."""
    with runtime_server(
        tmp_path, TEST_RUNTIME_BUDGET="0.3", TEST_RUNTIME_BLOCK_CONTACT="true",
    ) as (client, _):
        before = scrape(client)
        for _ in range(2):
            started = time.monotonic()
            response = client.post(CONTACT, json=PAYLOAD)
            elapsed = time.monotonic() - started
            assert response.status_code == 503
            assert response.json()["timeout_seconds"] == 0.3
            assert 0.25 <= elapsed < 1.5
        assert client.get("/__test/state").json()["contact_started"] == 2
        assert client.get("/__test/state").json()["contact_finished"] == 0
        during = scrape(client)
        assert during.value("abandoned_work_in_progress", endpoint=CONTACT) == 2
        assert during.delta(before, "cache_misses_total", endpoint=CONTACT_LABEL) == 2
        assert during.delta(before, "timeout_exceeded_total", endpoint=CONTACT) == 2
        assert during.delta(
            before, "errors_total", endpoint=CONTACT, error_type="timeout", status="503"
        ) == 2
        assert during.delta(
            before, "http_requests_total", endpoint=CONTACT, method="POST", status="503"
        ) == 2
        assert during.delta(
            before, "abandoned_work_total", endpoint=CONTACT, reason="timeout"
        ) == 0
        client.post("/__test/release").raise_for_status()
        eventually(lambda: scrape(client).value("abandoned_work_total", endpoint=CONTACT,
                                               reason="timeout") == 2)
        response = client.post(CONTACT, json=PAYLOAD)
        assert response.status_code == 200
        assert response.json()["contact_times"]["eclipse_begins"] == "2026-08-12 01:15:00.000"
        assert client.get("/__test/state").json()["contact_started"] == 2
        after = scrape(client)
        assert after.value("abandoned_work_in_progress", endpoint=CONTACT) == 0
        assert after.delta(before, "cache_hits_total", endpoint=CONTACT_LABEL) == 1
        assert after.value("cache_entry_count", endpoint=CONTACT_LABEL) == 1
        assert after.value("cache_memory_bytes", endpoint=CONTACT_LABEL) > 0
        assert after.delta(
            before, "abandoned_work_duration_seconds_count", endpoint=CONTACT
        ) == 2
        assert after.delta(
            before, "abandoned_work_duration_seconds_sum", endpoint=CONTACT
        ) >= 0.9
        assert after.delta(
            before, "abandoned_work_total", endpoint=CONTACT, reason="client_disconnect"
        ) == 0
        assert after.value("http_requests_in_progress", endpoint=CONTACT) == 0


def test_stream_deadline_and_disconnect_are_distinct(tmp_path):
    with runtime_server(
        tmp_path, TEST_RUNTIME_BUDGET="0.3", TEST_RUNTIME_BLOCK_STREAM="true"
    ) as (client, _):
        before = scrape(client)
        response = client.get(STREAM_URL)
        assert response.status_code == 200
        assert 'event: error\ndata: {"error": "timeout"}' in response.text
        after = scrape(client)
        assert after.delta(before, "timeout_exceeded_total", endpoint=STREAM) == 1
        assert after.delta(
            before, "errors_total", endpoint=STREAM, error_type="timeout", status="200"
        ) == 1
        assert after.delta(
            before, "http_requests_total", endpoint=STREAM, method="GET", status="200"
        ) == 1
        assert after.value("abandoned_work_in_progress", endpoint=STREAM) == 0
        assert after.value("abandoned_work_total", endpoint=STREAM, reason="timeout") == 0


def test_stream_disconnect_and_start_limit(tmp_path):
    with runtime_server(
        tmp_path, LIMIT_STREAM_EVENTS="2/minute", TEST_RUNTIME_BLOCK_STREAM="true"
    ) as (client, _):
        before = scrape(client)
        with client.stream("GET", STREAM_URL) as first:
            assert first.status_code == 200
            assert next(first.iter_lines()) == "event: page"
            eventually(lambda: client.get("/__test/state").json()["stream_waiting"] == 1)
            with client.stream("GET", STREAM_URL) as second:
                assert second.status_code == 200
                assert next(second.iter_lines()) == "event: page"
                eventually(lambda: client.get("/__test/state").json()["stream_waiting"] == 2)
                assert client.get(STREAM_URL).status_code == 429
        # Closing active streams does not refund fixed-window start tokens.
        assert client.get(STREAM_URL).status_code == 429
        client.post("/__test/release").raise_for_status()
        eventually(lambda: client.get("/__test/state").json()["stream_finished"] == 2)
        eventually(lambda: scrape(client).value("http_requests_in_progress", endpoint=STREAM) == 0)
        after = scrape(client)
        assert after.delta(
            before, "errors_total", endpoint=STREAM, error_type="stream_error", status="200"
        ) == 0
        assert after.value("abandoned_work_total", endpoint=STREAM, reason="client_disconnect") == 0
        assert after.value("http_requests_in_progress", endpoint=STREAM) == 0


@pytest.mark.parametrize("server", [
    "uvicorn",
    pytest.param("gunicorn", marks=pytest.mark.skipif(
        sys.platform == "win32", reason="gunicorn requires Unix"
    )),
])
def test_disconnect_reaches_real_worker_and_records_once(tmp_path, server):
    with runtime_server(
        tmp_path, server=server, TEST_RUNTIME_BLOCK_CONTACT="true"
    ) as (client, _):
        before = scrape(client)
        # Opening a streaming response still waits for headers, so disconnect the raw socket.
        import socket  # pylint: disable=import-outside-toplevel
        body = b'{"event_date":"2026-08-12 01:45:00.000","is_lunar":false}'
        with socket.create_connection(("127.0.0.1", client.base_url.port), timeout=3) as connection:
            connection.sendall(
                f"POST {CONTACT} HTTP/1.1\r\nHost: localhost\r\n"
                f"Content-Type: application/json\r\nContent-Length: {len(body)}\r\n\r\n".encode()
                + body
            )
            eventually(lambda: client.get("/__test/state").json()["contact_started"] == 1)
            connection.shutdown(socket.SHUT_RDWR)
        time.sleep(0.05)
        client.post("/__test/release").raise_for_status()
        eventually(lambda: scrape(client).value("abandoned_work_total", endpoint=CONTACT,
                                               reason="client_disconnect") == 1)
        after = scrape(client)
        assert after.delta(
            before, "http_requests_total", endpoint=CONTACT, method="POST", status="200"
        ) == 1
        assert not after.endpoints("errors_total")
        assert after.value("abandoned_work_in_progress", endpoint=CONTACT) == 0


def test_real_errors_and_unknown_paths_have_bounded_labels(tmp_path):
    with runtime_server(tmp_path) as (client, _):
        before = scrape(client)
        for status in (400, 413, 422, 429, 500, 503, 401, 403, 404, 405, 409):
            assert client.get(f"/__test/status/{status}").status_code == status
        # ASGI servers close connections after unhandled exceptions.
        assert client.get("/__test/broken", headers={"Connection": "close"}).status_code == 500
        assert client.post(CONTACT, json={}).status_code == 422
        assert client.post(CONTACT, content=b"x" * (1024 * 1024 + 1)).status_code == 413
        assert client.get(CONTACT).status_code == 405
        for index in range(200):
            assert client.get(f"/api/v1/nonce-{index}?private={index}").status_code == 404
        after = scrape(client)
        expected = {
            (400, "invalid_input"), (413, "payload_too_large"),
            (422, "request_validation"), (429, "rate_limited"),
            (500, "server_error"), (503, "server_error"),
        }
        for status, category in expected:
            assert after.delta(
                before, "errors_total", endpoint="/__test/status/{status}",
                error_type=category, status=str(status),
            ) == 1
        errors = {
            (dict(labels)["endpoint"], dict(labels)["error_type"], dict(labels)["status"]): value
            for (name, labels), value in after.samples.items() if name == "errors_total"
        }
        assert len(errors) == len(expected) + 3
        assert errors[("/__test/broken", "unhandled_exception", "500")] == 1
        assert errors[(CONTACT, "request_validation", "422")] == 1
        # Request-size rejection occurs before routing, so its label is "unknown".
        assert errors[("unknown", "payload_too_large", "413")] == 1
        assert after.delta(
            before, "http_requests_total", endpoint="unknown", method="GET", status="404"
        ) == 200
        assert after.endpoints("http_requests_") <= {
            "/health", "/api/metrics", "/__test/status/{status}",
            "/__test/broken", CONTACT, "unknown",
        }


def test_cache_evictions_concurrency_clear_and_labels_over_http(tmp_path):
    with runtime_server(
        tmp_path, TEST_RUNTIME_CACHE_SIZE="4", LIMIT_CONTACT_TIMES="10000/minute"
    ) as (client, _):
        before = scrape(client)

        def contact(index):
            payload = {**PAYLOAD, "event_date": f"2026-08-12 01:{index % 10:02d}:00.000"}
            response = client.post(CONTACT, json=payload, params={"private": index})
            assert response.status_code == 200, response.text

        with ThreadPoolExecutor(max_workers=10) as executor:
            list(executor.map(contact, range(50)))
        after = scrape(client)
        assert after.endpoints("cache_") == {CONTACT_LABEL}
        assert after.value("cache_entry_count", endpoint=CONTACT_LABEL) == 4
        assert after.value("cache_memory_bytes", endpoint=CONTACT_LABEL) > 0
        assert after.delta(before, "cache_evictions_total", endpoint=CONTACT_LABEL) > 0
        client.post("/__test/clear").raise_for_status()
        cleared = scrape(client)
        assert cleared.value("cache_entry_count", endpoint=CONTACT_LABEL) == 0
        assert cleared.value("cache_memory_bytes", endpoint=CONTACT_LABEL) == 0
        assert cleared.value("http_requests_in_progress", endpoint=CONTACT) == 0


def test_concurrent_deadlines_drain_background_work(tmp_path):
    with runtime_server(
        tmp_path, TEST_RUNTIME_BUDGET="0.3", TEST_RUNTIME_BLOCK_CONTACT="true",
    ) as (client, _):
        before = scrape(client)

        def request(_index):
            started = time.monotonic()
            response = client.post(CONTACT, json=PAYLOAD)
            assert response.status_code == 503
            assert time.monotonic() - started < 1.5

        with ThreadPoolExecutor(max_workers=10) as executor:
            list(executor.map(request, range(10)))
        assert client.get("/__test/state").json()["contact_started"] == 10
        assert scrape(client).value("abandoned_work_in_progress", endpoint=CONTACT) == 10
        client.post("/__test/release").raise_for_status()
        eventually(lambda: scrape(client).value("abandoned_work_in_progress", endpoint=CONTACT) == 0)
        after = scrape(client)
        assert after.delta(
            before, "abandoned_work_total", endpoint=CONTACT, reason="timeout"
        ) == 10
        assert after.delta(before, "timeout_exceeded_total", endpoint=CONTACT) == 10
        assert after.delta(
            before, "errors_total", endpoint=CONTACT, error_type="timeout", status="503"
        ) == 10


@pytest.mark.skipif(sys.platform == "win32", reason="gunicorn requires Unix")
def test_gunicorn_shutdown_waits_for_detached_work(tmp_path):
    with runtime_server(
        tmp_path, server="gunicorn", TEST_RUNTIME_BUDGET="0.1", TEST_RUNTIME_DELAY="1",
    ) as (client, process):
        assert client.post(CONTACT, json=PAYLOAD).status_code == 503
        assert client.get("/__test/state").json()["contact_finished"] == 0
        started = time.monotonic()
        process.terminate()
        assert process.wait(timeout=8) == 0
        assert 0.3 < time.monotonic() - started < 8
        log = next(tmp_path.glob("runtime-*.log")).read_text()
        assert "Application shutdown complete" in log
        assert "unfinished background requests" not in log
        assert "Traceback" not in log


def test_nginx_api_timeouts_remain_aligned():
    root = Path(__file__).resolve().parents[1]
    for path in ("scripts/castle-celestial.nginx.conf", "frontend/tests/Hosting/celestial-view"):
        config = (root / path).read_text(encoding="utf-8")
        block = config.split("location /api/ {", 1)[1].split("}", 1)[0]
        for directive in ("proxy_send_timeout", "proxy_read_timeout"):
            assert re.findall(rf"\b{directive}\s+(\d+)s;", block) == ["250"]
