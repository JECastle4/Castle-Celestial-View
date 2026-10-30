"""Runtime regressions for deadlines, disconnect observation and error accounting."""

import asyncio
from contextlib import contextmanager
from http.client import HTTPConnection
import json
import socket
import threading
import time
from types import SimpleNamespace
from unittest.mock import MagicMock

import anyio
import pytest
from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import Response, StreamingResponse
from fastapi.testclient import TestClient
from prometheus_client import REGISTRY

import api.main as main
from api.cache import cache_response, clear_response_cache
from api.middleware.request_lifecycle import BackgroundRequests, disconnected_before_response
from api.models import EclipseContactTimesRequest
from api.routes.helpers import handle_route_errors


@pytest.fixture
def metrics(monkeypatch):
    """Keep process-global metrics out of exact call-count assertions."""
    recorder = MagicMock()
    monkeypatch.setattr(main, "get_metrics", lambda: recorder)
    monkeypatch.setattr("api.middleware.request_lifecycle.get_metrics", lambda: recorder)
    monkeypatch.setattr(main, "record_request_completion", MagicMock())
    return recorder


def wrapped_app():
    """The locale BaseHTTPMiddleware layer matters to sync cancellation shielding."""
    application = FastAPI()

    @application.middleware("http")
    async def passthrough(request, call_next):
        return await call_next(request)

    application.add_middleware(main.TimeoutMiddleware)
    application.add_middleware(main.MetricsMiddleware)
    return application


def test_sync_deadline_returns_before_work_finishes_and_caches(monkeypatch, metrics):
    """The old wait_for returned only AFTER the shielded worker finished."""
    monkeypatch.setattr(main, "calculate_adaptive_timeout", lambda _: 0.1)
    application = wrapped_app()
    started = threading.Event()
    release = threading.Event()
    finished = threading.Event()
    calls = []

    @application.post("/contact")
    @cache_response()
    @handle_route_errors()
    def contact(request: Request, contact_times_request: EclipseContactTimesRequest):
        del request, contact_times_request
        calls.append(True)
        started.set()
        assert release.wait(5)
        finished.set()
        return {"result": "cached"}

    clear_response_cache()
    try:
        with TestClient(application) as client:
            response = client.post(
                "/contact", json={"event_date": "2025-03-14 06:58:43", "is_lunar": True}
            )
            assert response.status_code == 503
            assert started.is_set()
            assert not finished.is_set()
            metrics.record_timeout_exceeded.assert_called_once()
            metrics.abandoned_work_in_progress.labels.return_value.inc.assert_called_once()
            release.set()
            assert finished.wait(2)
            # The cache write occurs just after the route returns.
            deadline = time.monotonic() + 2
            while not metrics.record_abandoned_work.called and time.monotonic() < deadline:
                time.sleep(0.01)
            response = client.post(
                "/contact", json={"event_date": "2025-03-14 06:58:43", "is_lunar": True}
            )
            assert response.status_code == 200
            assert response.json() == {"result": "cached"}
            assert len(calls) == 1
            assert metrics.record_abandoned_work.call_count == 1
            assert metrics.record_abandoned_work.call_args.args[1] == "timeout"
            metrics.abandoned_work_in_progress.labels.return_value.dec.assert_called_once()
    finally:
        release.set()
        clear_response_cache()


@pytest.mark.parametrize(
    ("status", "category"),
    [(200, None), (400, "invalid_input"), (404, None), (405, None),
     (413, "payload_too_large"), (422, "request_validation"),
     (429, "rate_limited"), (503, "server_error"), (500, "server_error")],
)
def test_error_categories(status, category, metrics):
    application = FastAPI()

    @application.get("/result")
    def result():
        return Response(status_code=status)

    application.add_middleware(main.MetricsMiddleware)
    with TestClient(application) as client:
        assert client.get("/result").status_code == status
    if category:
        metrics.record_error.assert_called_once_with("/result", category, status)
    else:
        metrics.record_error.assert_not_called()
    metrics.record_request_end.assert_called_once()


def test_real_validation_and_handled_failure(metrics):
    application = FastAPI()

    @application.get("/number")
    def number(value: int):
        raise HTTPException(400, detail=str(value))

    application.add_middleware(main.MetricsMiddleware)
    with TestClient(application) as client:
        assert client.get("/number?value=bad").status_code == 422
        assert client.get("/number?value=1").status_code == 400
    assert [call.args[1] for call in metrics.record_error.call_args_list] == [
        "request_validation", "invalid_input"
    ]


def test_unhandled_failure_records_http_500_once(metrics):
    application = wrapped_app()

    @application.get("/broken")
    def broken():
        raise RuntimeError("private details")

    with TestClient(application, raise_server_exceptions=False) as client:
        assert client.get("/broken").status_code == 500
    metrics.record_error.assert_called_once_with("/broken", "unhandled_exception", 500)
    metrics.record_request.assert_called_once()
    assert metrics.record_request.call_args.args[:3] == ("/broken", "GET", 500)
    metrics.record_request_end.assert_called_once()


@pytest.mark.asyncio
async def test_disconnect_before_response_counted_once(metrics):
    scope = {
        "type": "http", "method": "POST", "path": "/api/v1/sun-position",
        "headers": [], "route": SimpleNamespace(path="/api/v1/sun-position"),
    }

    async def gone():
        return {"type": "http.disconnect"}

    messages = []

    async def send(message):
        messages.append(message)

    async def application(scope, receive, send):
        await send({"type": "http.response.start", "status": 200,
                    "headers": [(b"content-length", b"2")]})
        await send({"type": "http.response.body", "body": b"{}"})

    await main.MetricsMiddleware(application)(scope, gone, send)
    metrics.record_abandoned_work.assert_called_once()
    assert metrics.record_abandoned_work.call_args.args[:2] == (
        "/api/v1/sun-position", "client_disconnect"
    )
    assert len(messages) == 2


@pytest.mark.asyncio
async def test_disconnect_peek_handles_get_and_never_waits():
    messages = iter([{"type": "http.request", "body": b""}, {"type": "http.disconnect"}])

    async def receive():
        return next(messages)

    assert await disconnected_before_response(receive)

    async def connected():
        await anyio.sleep_forever()

    assert not await disconnected_before_response(connected)


def test_stalled_stream_deadline_and_status_preserved(monkeypatch, metrics):
    monkeypatch.setattr(main, "calculate_adaptive_timeout", lambda _: 0.05)
    application = wrapped_app()

    @application.get("/stream")
    def stream():
        async def chunks():
            yield "data: first\n\n"
            await asyncio.sleep(10)
        return StreamingResponse(chunks(), media_type="text/event-stream")

    with TestClient(application) as client:
        started = time.monotonic()
        response = client.get("/stream")
        assert time.monotonic() - started < 1
        assert response.status_code == 200
        assert '"timeout"' in response.text
    metrics.record_timeout_exceeded.assert_called_once()
    metrics.record_error.assert_called_once_with("/stream", "timeout", 200)
    metrics.record_request.assert_called_once()
    metrics.record_request_end.assert_called_once()
    metrics.record_abandoned_work.assert_not_called()


def test_stream_failure_is_not_a_second_http_response(metrics):
    application = FastAPI()

    @application.get("/stream")
    def stream():
        async def chunks():
            yield b"first"
            raise RuntimeError("broken stream")
        return StreamingResponse(chunks())

    application.add_middleware(main.MetricsMiddleware)
    with TestClient(application, raise_server_exceptions=False) as client:
        assert client.get("/stream").status_code == 200
    metrics.record_error.assert_called_once_with("/stream", "stream_error", 200)
    metrics.record_abandoned_work.assert_not_called()
    metrics.record_request_end.assert_called_once()


@pytest.mark.asyncio
async def test_detached_exception_observed_and_logged(metrics, caplog):
    background = BackgroundRequests()

    async def broken():
        raise RuntimeError("late failure")

    task = asyncio.create_task(broken())
    background.track(task, "/test", time.perf_counter())
    await asyncio.sleep(0)
    await asyncio.sleep(0)
    assert not background.tasks
    assert "late failure" in caplog.text
    metrics.record_abandoned_work.assert_called_once()
    metrics.abandoned_work_in_progress.labels.return_value.dec.assert_called_once()


@pytest.mark.asyncio
async def test_tracking_same_task_twice_does_not_duplicate_metrics(metrics):
    background = BackgroundRequests()
    task = asyncio.create_task(asyncio.sleep(0))
    background.track(task, "/test", time.perf_counter())
    background.track(task, "/test", time.perf_counter())
    await task
    await asyncio.sleep(0)
    metrics.record_abandoned_work.assert_called_once()
    metrics.abandoned_work_in_progress.labels.return_value.inc.assert_called_once()
    metrics.abandoned_work_in_progress.labels.return_value.dec.assert_called_once()


def test_error_metrics_reach_real_prometheus_registry():
    application = FastAPI()

    @application.get("/__lifecycle/invalid")
    def invalid(value: int):
        return value

    application.add_middleware(main.MetricsMiddleware)
    labels = {
        "endpoint": "/__lifecycle/invalid", "error_type": "request_validation", "status": "422"
    }
    before = REGISTRY.get_sample_value("errors_total", labels) or 0
    with TestClient(application) as client:
        assert client.get("/__lifecycle/invalid?value=bad").status_code == 422
    assert REGISTRY.get_sample_value("errors_total", labels) == before + 1


@pytest.mark.asyncio
async def test_deadline_during_final_send_cancels_send_and_closes_response(monkeypatch, metrics):
    monkeypatch.setattr(main, "calculate_adaptive_timeout", lambda _: 0.02)
    sent = []
    blocked_send_cancelled = asyncio.Event()

    async def application(scope, receive, send):
        await send({"type": "http.response.start", "status": 200,
                    "headers": [(b"content-length", b"4")]})
        await send({"type": "http.response.body", "body": b"slow"})

    async def send(message):
        if message.get("body") == b"slow":
            try:
                await asyncio.sleep(10)
            finally:
                blocked_send_cancelled.set()
        else:
            sent.append(message)

    async def receive():
        await asyncio.sleep(10)

    scope = {"type": "http", "method": "GET", "path": "/slow-send", "headers": []}
    middleware = main.TimeoutMiddleware(application)
    await middleware(scope, receive, send)
    assert blocked_send_cancelled.is_set()
    assert len(sent) == 2
    assert sent[0]["status"] == 200
    assert sent[-1] == {"type": "http.response.body", "body": b"", "more_body": False}
    assert scope["_timeout_middleware_generated"]
    await asyncio.sleep(0)


@contextmanager
def serve(application, http):
    """Use a real TCP server: in-process ASGI transports synthesize disconnects."""
    import uvicorn  # pylint: disable=import-outside-toplevel
    listener = socket.socket()
    listener.bind(("127.0.0.1", 0))
    listener.listen()
    port = listener.getsockname()[1]
    server = uvicorn.Server(uvicorn.Config(
        application, host="127.0.0.1", port=port, http=http, log_level="error",
        lifespan="on", timeout_graceful_shutdown=2,
    ))
    thread = threading.Thread(target=server.run, kwargs={"sockets": [listener]})
    thread.start()
    try:
        deadline = time.monotonic() + 5
        while not server.started and time.monotonic() < deadline:
            time.sleep(0.01)
        assert server.started
        yield port
    finally:
        server.should_exit = True
        thread.join(timeout=8)
        listener.close()
        assert not thread.is_alive()


@pytest.mark.parametrize("http", ["h11", "httptools"])
def test_real_tcp_disconnect_observation(http, monkeypatch, metrics):
    monkeypatch.setattr(main, "calculate_adaptive_timeout", lambda _: 5)
    application = wrapped_app()
    running = threading.Event()
    release = threading.Event()

    @application.post("/work")
    def work(payload: EclipseContactTimesRequest):
        del payload
        running.set()
        assert release.wait(5)
        return {"ok": True}

    with serve(application, http) as port:
        connection = socket.create_connection(("127.0.0.1", port), timeout=3)
        try:
            body = json.dumps({"event_date": "2025-03-14 06:58:43", "is_lunar": True}).encode()
            connection.sendall(
                b"POST /work HTTP/1.1\r\nHost: localhost\r\nContent-Type: application/json\r\n"
                + f"Content-Length: {len(body)}\r\n\r\n".encode() + body
            )
            assert running.wait(2)
            connection.shutdown(socket.SHUT_RDWR)
            connection.close()
            # Ensure the server has received FIN before the handler returns.
            time.sleep(0.05)
            release.set()
            deadline = time.monotonic() + 2
            while not metrics.record_abandoned_work.called and time.monotonic() < deadline:
                time.sleep(0.01)
            metrics.record_abandoned_work.assert_called_once()
            assert metrics.record_abandoned_work.call_args.args[:2] == (
                "/work", "client_disconnect"
            )
            metrics.record_error.assert_not_called()
        finally:
            release.set()
            connection.close()


@pytest.mark.parametrize("http", ["h11", "httptools"])
def test_real_tcp_timeout_late_send_and_keepalive(http, monkeypatch, metrics):
    monkeypatch.setattr(main, "calculate_adaptive_timeout", lambda _: 0.1)
    application = wrapped_app()
    running = threading.Event()
    release = threading.Event()

    @application.get("/work")
    def work():
        running.set()
        assert release.wait(5)
        return {"late": True}

    @application.get("/ready")
    def ready():
        return {"ready": True}

    with serve(application, http) as port:
        client = HTTPConnection("127.0.0.1", port, timeout=2)
        try:
            client.request("GET", "/work")
            response = client.getresponse()
            assert response.status == 503
            response.read()
            assert running.is_set()
            assert not release.is_set()
            client.request("GET", "/ready")
            response = client.getresponse()
            assert response.status == 200
            assert json.loads(response.read()) == {"ready": True}
            release.set()
            deadline = time.monotonic() + 2
            while not metrics.record_abandoned_work.called and time.monotonic() < deadline:
                time.sleep(0.01)
            metrics.record_abandoned_work.assert_called_once()
            assert metrics.record_abandoned_work.call_args.args[1] == "timeout"
            client.request("GET", "/ready")
            response = client.getresponse()
            assert json.loads(response.read()) == {"ready": True}
        finally:
            release.set()
            client.close()
