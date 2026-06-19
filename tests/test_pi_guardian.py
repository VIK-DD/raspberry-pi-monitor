"""
Basic test suite for Pi Guardian.

Runs entirely in DEMO_MODE so it needs no Raspberry Pi, AdGuard or network.
    pip install pytest && pytest
"""
import os
import sys

os.environ["DEMO_MODE"] = "1"

_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, _ROOT)
sys.path.insert(0, os.path.join(_ROOT, "dashboard"))

import collector          # noqa: E402
import demo_data          # noqa: E402


def test_collector_demo_shape():
    d = collector.collect_all()
    assert {"timestamp", "system", "adguard", "alerts"} <= set(d)
    for k in ("cpu_percent", "cpu_temp", "ram_percent", "disk_percent", "uptime"):
        assert k in d["system"]
    assert d["adguard"]["ok"] is True


def test_demo_endpoints_callable():
    for fn in ("system_stats", "system_info", "sysinfo", "disk_io", "bandwidth",
               "network", "healthchecks", "ping", "temp_history", "users",
               "events", "adguard_history", "adguard_stats", "collect_all"):
        result = getattr(demo_data, fn)()
        assert result is not None


def test_password_hashing_roundtrip():
    import main
    h = main.hash_pass("s3cret-pass")
    assert "$" in h
    assert main.verify_pass("s3cret-pass", h)
    assert not main.verify_pass("wrong-pass", h)
    # a different salt is used on every call
    assert main.hash_pass("same") != main.hash_pass("same")
    # malformed stored hash never verifies
    assert not main.verify_pass("x", "not-a-valid-hash")


def test_no_insecure_default_admin_password():
    import main
    # The hardcoded fallback password must be gone.
    assert main.DASHBOARD_PASS == "" or os.getenv("DASHBOARD_PASS")
    if not main.DASHBOARD_PASS:
        assert main.PASS_HASH is None


def test_api_smoke():
    try:
        from fastapi.testclient import TestClient
    except Exception:
        import pytest
        pytest.skip("starlette TestClient/httpx not installed")
    import main
    with TestClient(main.app) as client:
        r = client.get("/api/stats")          # demo mode: no auth wall
        assert r.status_code == 200
        assert "system" in r.json()
        assert client.get("/login").status_code == 200
        assert client.get("/api/network").json()["local"]
