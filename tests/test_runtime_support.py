"""Platform-specific teardown must not hide runtime process failures."""

import subprocess
from types import SimpleNamespace
from unittest.mock import MagicMock

import pytest

import runtime_support


@pytest.mark.parametrize(
    ("platform", "server", "running", "returncode", "accepted"),
    [
        ("win32", "uvicorn", True, 1, True),
        ("win32", "uvicorn", False, 1, False),
        ("win32", "uvicorn", True, 2, False),
        ("linux", "uvicorn", True, 1, False),
        ("linux", "uvicorn", True, -15, True),
        ("linux", "uvicorn", True, 0, True),
        ("linux", "gunicorn", True, 0, True),
        ("linux", "gunicorn", True, 1, False),
    ],
)
def test_runtime_teardown_exit_status(
    tmp_path, monkeypatch, platform, server, running, returncode, accepted
):
    process = MagicMock()
    process.poll.side_effect = [None, None if running else returncode]
    process.returncode = returncode
    client = MagicMock()
    client.get.return_value.status_code = 200
    monkeypatch.setattr(runtime_support, "sys", SimpleNamespace(
        platform=platform, executable="python"
    ))
    monkeypatch.setattr(runtime_support.subprocess, "Popen", lambda *args, **kwargs: process)
    monkeypatch.setattr(runtime_support.httpx, "Client", MagicMock(
        return_value=MagicMock(__enter__=MagicMock(return_value=client))
    ))

    def run():
        with runtime_support.runtime_server(tmp_path, server=server):
            pass

    if accepted:
        run()
    else:
        with pytest.raises(AssertionError):
            run()
    assert process.terminate.call_count == int(running)
    process.kill.assert_not_called()


def test_runtime_teardown_forced_kill_still_fails(tmp_path, monkeypatch):
    process = MagicMock()
    process.poll.return_value = None
    process.wait.side_effect = [subprocess.TimeoutExpired("uvicorn", 15), 1]
    process.returncode = 1
    client = MagicMock()
    client.get.return_value.status_code = 200
    monkeypatch.setattr(runtime_support, "sys", SimpleNamespace(
        platform="win32", executable="python"
    ))
    monkeypatch.setattr(runtime_support.subprocess, "Popen", lambda *args, **kwargs: process)
    monkeypatch.setattr(runtime_support.httpx, "Client", MagicMock(
        return_value=MagicMock(__enter__=MagicMock(return_value=client))
    ))
    with pytest.raises(AssertionError, match="failed to shut down"):
        with runtime_support.runtime_server(tmp_path):
            pass
    process.kill.assert_called_once()
