"""Real-process HTTP harness and exact Prometheus sample comparisons."""

from contextlib import contextmanager
import os
from pathlib import Path
import signal
import socket
import subprocess
import sys
import time

import httpx
from prometheus_client.parser import text_string_to_metric_families


ROOT = Path(__file__).resolve().parents[1]


class MetricsSnapshot:
    """Preserve label sets so absent series count as zero, never as missing evidence."""

    def __init__(self, text):
        self.samples = {
            (sample.name, tuple(sorted(sample.labels.items()))): sample.value
            for family in text_string_to_metric_families(text)
            for sample in family.samples
        }

    @classmethod
    def scrape(cls, client):
        response = client.get("/api/metrics")
        response.raise_for_status()
        return cls(response.text)

    def value(self, name, **labels):
        return self.samples.get((name, tuple(sorted(labels.items()))), 0)

    def delta(self, before, name, **labels):
        return self.value(name, **labels) - before.value(name, **labels)

    def endpoints(self, prefix):
        return {
            dict(labels)["endpoint"]
            for (name, labels) in self.samples
            if name.startswith(prefix) and "endpoint" in dict(labels)
        }


def eventually(predicate, timeout=5):
    """Bound polling by elapsed time and report the last observed value on failure."""
    deadline = time.monotonic() + timeout
    value = predicate()
    while not value and time.monotonic() < deadline:
        time.sleep(0.02)
        value = predicate()
    assert value, f"Condition not met within {timeout}s (last value: {value!r})"
    return value


@contextmanager
def runtime_server(tmp_path, *, server="uvicorn", **overrides):
    """Use a fresh interpreter so pytest cannot select MockLimiter or mute metrics."""
    with socket.socket() as listener:
        listener.bind(("127.0.0.1", 0))
        port = listener.getsockname()[1]
    env = {
        key: value for key, value in os.environ.items()
        if key != "PYTEST_CURRENT_TEST" and not key.startswith(
            ("LIMIT_", "RATE_LIMIT_", "TEST_RUNTIME_")
        )
    }
    env.update({
        "RATE_LIMIT_ENABLED": "true", "RATE_LIMIT_DEFAULT": "10000/minute",
        "TRUSTED_PROXIES": "", "FORWARDED_ALLOW_IPS": "",
        "MAX_REQUEST_SIZE_MB": "1",
        **{key: str(value) for key, value in overrides.items()},
    })
    if server == "gunicorn":
        command = [
            sys.executable, "-m", "gunicorn", "runtime_app:app", "--pythonpath", "tests",
            "--bind", f"127.0.0.1:{port}", "--workers", "1",
            "--worker-class", "uvicorn.workers.UvicornWorker",
            "--graceful-timeout", "10", "--timeout", "30",
        ]
    else:
        command = [
            sys.executable, "-m", "uvicorn", "runtime_app:app", "--app-dir", "tests",
            "--host", "127.0.0.1", "--port", str(port),
            "--no-proxy-headers", "--log-level", "warning",
        ]
    log_path = tmp_path / f"runtime-{port}.log"
    with log_path.open("w+", encoding="utf-8") as log:
        process = subprocess.Popen(command, cwd=ROOT, env=env, stdout=log, stderr=log)
        with httpx.Client(base_url=f"http://127.0.0.1:{port}", timeout=5, trust_env=False) as client:
            try:
                deadline = time.monotonic() + 15
                while True:
                    if process.poll() is not None:
                        raise AssertionError(f"Server exited:\n{log_path.read_text()}")
                    try:
                        response = client.get("/health")
                    except httpx.ConnectError:
                        if time.monotonic() >= deadline:
                            raise AssertionError("Server startup timed out") from None
                        time.sleep(0.05)
                    else:
                        response.raise_for_status()
                        break
                yield client, process
            finally:
                if process.poll() is None:
                    try:
                        client.post("/__test/release").raise_for_status()
                    finally:
                        process.terminate()
                        try:
                            process.wait(timeout=15)
                        except subprocess.TimeoutExpired:
                            process.kill()
                            process.wait(timeout=5)
                            raise AssertionError("Runtime server failed to shut down") from None
                expected_exit = (0,) if server == "gunicorn" else (0, -signal.SIGTERM)
                assert process.returncode in expected_exit, log_path.read_text()
