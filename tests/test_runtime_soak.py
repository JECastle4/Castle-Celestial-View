"""Opt-in ten-minute mixed workload: RUN_RUNTIME_SOAK=true python -m pytest ... ."""

from collections import Counter
import os
from pathlib import Path
import time

import pytest

from runtime_support import MetricsSnapshot, disconnect_held_contact, eventually, runtime_server


pytestmark = pytest.mark.skipif(
    os.environ.get("RUN_RUNTIME_SOAK") != "true", reason="Opt-in ten-minute runtime soak"
)
CONTACT = "/api/v1/astronomical-events/contact-times"


def resources(pid):
    """Linux process measurements, not inferred from response-size cache gauges."""
    status = Path(f"/proc/{pid}/status").read_text()
    fields = dict(line.split(":", 1) for line in status.splitlines() if ":" in line)
    return {"rss_kib": int(fields["VmRSS"].split()[0]), "threads": int(fields["Threads"])}


def test_mixed_load_metrics_and_resource_stability(tmp_path):
    with runtime_server(
        tmp_path, LIMIT_CONTACT_TIMES="10000/minute",
        TEST_RUNTIME_BUDGET="0.5", TEST_RUNTIME_DELAY="0.05",
        TEST_RUNTIME_SLOW_DELAY="1.0",
        TEST_RUNTIME_BLOCK_MARKED_CONTACT="true",
    ) as (client, process):
        before = MetricsSnapshot.scrape(client)
        expected = Counter()
        rounds = 0
        samples = []
        deadline = time.monotonic() + 600
        while time.monotonic() < deadline:
            for index in range(20):
                payload = {
                    "event_date": f"2026-08-{1 + rounds % 28:02d} 01:{index:02d}:00.000",
                    "is_lunar": False,
                }
                if index == 0:
                    response = client.post(CONTACT, json={})
                    assert response.status_code == 422
                    expected[422] += 1
                elif index in (1, 2):
                    payload["event_date"] = (
                        f"2026-08-{1 + rounds % 28:02d} 01:{index:02d}:58.000"
                    )
                    disconnect_held_contact(client, payload)
                    eventually(lambda: MetricsSnapshot.scrape(client).value(
                        "abandoned_work_total", endpoint=CONTACT, reason="client_disconnect"
                    ) == rounds * 2 + index)
                    expected[200] += 1
                else:
                    if index == 3:
                        payload["event_date"] = f"2026-08-{1 + rounds % 28:02d} 02:00:59.000"
                    response = client.post(CONTACT, json=payload)
                    assert response.status_code == (503 if index == 3 else 200)
                    expected[response.status_code] += 1
            time.sleep(0.1)
            eventually(lambda: MetricsSnapshot.scrape(client).value(
                "abandoned_work_in_progress", endpoint=CONTACT
            ) == 0)
            rounds += 1
            samples.append(resources(process.pid))
            # Keep each round cold enough to exercise real disconnects and timeouts.
            client.post("/__test/clear").raise_for_status()
            if rounds % 20 == 0:
                print(f"soak rounds={rounds}, responses={dict(expected)}, resources={samples[-1]}")
        after = MetricsSnapshot.scrape(client)
        for status, count in expected.items():
            assert after.delta(
                before, "http_requests_total", endpoint=CONTACT, method="POST", status=str(status)
            ) == count
        assert after.delta(
            before, "errors_total", endpoint=CONTACT, error_type="request_validation", status="422"
        ) == rounds
        assert after.delta(
            before, "errors_total", endpoint=CONTACT, error_type="timeout", status="503"
        ) == rounds
        assert after.delta(
            before, "abandoned_work_total", endpoint=CONTACT, reason="timeout"
        ) == rounds
        assert after.delta(
            before, "abandoned_work_total", endpoint=CONTACT, reason="client_disconnect"
        ) == rounds * 2
        assert after.value("abandoned_work_in_progress", endpoint=CONTACT) == 0
        assert after.value("http_requests_in_progress", endpoint=CONTACT) == 0
        assert after.value("cache_entry_count", endpoint="get_contact_times_route") == 0
        assert after.value("cache_memory_bytes", endpoint="get_contact_times_route") == 0
        assert after.endpoints("cache_") == {"get_contact_times_route"}
        # Compare after warm-up, allowing allocator variation but not unbounded growth.
        baseline = samples[min(10, len(samples) - 1)]
        assert samples[-1]["rss_kib"] - baseline["rss_kib"] < 20 * 1024
        assert samples[-1]["threads"] - baseline["threads"] <= 4
        print(f"soak complete: rounds={rounds}, responses={dict(expected)}, "
              f"baseline={baseline}, final={samples[-1]}")
