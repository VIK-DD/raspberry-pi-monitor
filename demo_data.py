"""
demo_data.py — synthetic data provider for DEMO_MODE.

When DEMO_MODE=1, the collector and the dashboard serve these realistic
sample payloads instead of reading a real Raspberry Pi, AdGuard Home,
Healthchecks.io, etc. This lets Pi Guardian run on any machine with no
hardware and no external services — perfect for a quick try-out or for
generating documentation screenshots.

Every function mirrors the exact shape returned by its real counterpart
in collector.py / dashboard/main.py, so the rest of the app is unaware
it is being fed demo data.
"""
import math
import time
import random
from datetime import datetime, timezone

_START = time.time()


def _wave(period: float, lo: float, hi: float, phase: float = 0.0) -> float:
    """Smooth sine oscillation between lo and hi over `period` seconds."""
    t = time.time() - _START
    frac = (math.sin(2 * math.pi * (t / period) + phase) + 1) / 2
    return lo + (hi - lo) * frac


# ── System ────────────────────────────────────────────────────

def cpu_temp() -> float:
    return round(_wave(90, 44.0, 52.0) + random.uniform(-0.4, 0.4), 1)


def system_stats() -> dict:
    cpu = max(0.0, round(_wave(40, 9, 34) + random.uniform(-2, 4), 1))
    ram_total = 462.0          # Raspberry Pi Zero 2 W ≈ 512 MB usable
    ram_pct = round(_wave(150, 39, 57), 1)
    disk_total = 29.7
    disk_pct = 41.3
    return {
        "cpu_percent":   cpu,
        "cpu_temp":      cpu_temp(),
        "ram_percent":   ram_pct,
        "ram_used_mb":   round(ram_total * ram_pct / 100, 1),
        "ram_total_mb":  ram_total,
        "disk_percent":  disk_pct,
        "disk_used_gb":  round(disk_total * disk_pct / 100, 2),
        "disk_total_gb": disk_total,
        "uptime":        "12d 6h 41m",
    }


def system_info() -> dict:
    boot = _START - 12 * 86400 - 6 * 3600
    return {
        "ok": True,
        "uptime_str": "12d 6h 41m",
        "boot_time_str": time.strftime("%d.%m.%Y %H:%M", time.localtime(boot)),
        "hostname": "pi-guardian",
    }


def sysinfo() -> dict:
    return {
        "python":   "3.11.2",
        "os":       "Linux",
        "kernel":   "6.1.21-v8+",
        "arch":     "aarch64",
        "hostname": "pi-guardian",
    }


def disk_io() -> dict:
    return {
        "ok": True,
        "read_kb_s":      round(_wave(20, 4, 60), 2),
        "write_kb_s":     round(_wave(15, 2, 45), 2),
        "total_read_mb":  18243.6,
        "total_write_mb": 9881.2,
        "read_count":     1_204_553,
        "write_count":    842_117,
    }


def bandwidth() -> dict:
    return {
        "ok": True,
        "rx_kb_s":     round(_wave(18, 30, 320), 2),
        "tx_kb_s":     round(_wave(22, 12, 140), 2),
        "total_rx_mb": 42118.4,
        "total_tx_mb": 9744.9,
    }


def network() -> dict:
    return {
        "local":     "192.168.1.2",
        "tailscale": "100.64.0.42",
        "docker":    "172.17.0.1",
        "hostname":  "pi-guardian",
        "all_ips":   ["192.168.1.2", "100.64.0.42", "172.17.0.1"],
    }


# ── AdGuard Home ──────────────────────────────────────────────

def adguard_stats() -> dict:
    queries = 48213 + int((time.time() - _START) * 0.7)
    blocked = int(queries * 0.247)
    return {
        "ok": True,
        "running": True,
        "protection_enabled": True,
        "version": "v0.107.52",
        "dns_queries": queries,
        "blocked": blocked,
        "blocked_percent": 24.7,
        "avg_ms": 12.4,
        "top_blocked": [
            {"name": "app-measurement.com",  "count": 1842},
            {"name": "graph.facebook.com",   "count": 1210},
            {"name": "ads.tiktok.com",       "count":  980},
            {"name": "doubleclick.net",      "count":  774},
            {"name": "analytics.google.com", "count":  661},
        ],
        "top_clients": [
            {"name": "192.168.1.21", "count": 12044},
            {"name": "192.168.1.34", "count":  9821},
            {"name": "192.168.1.10", "count":  6233},
        ],
    }


def collect_all() -> dict:
    return {
        "timestamp": datetime.now().strftime("%d.%m.%Y %H:%M:%S"),
        "system":  system_stats(),
        "adguard": adguard_stats(),
        "alerts":  [],
    }


def adguard_history() -> dict:
    dns = [round(800 + _wave(40, -250, 250, phase=i / 3) + random.uniform(-60, 60)) for i in range(48)]
    blocked = [round(v * 0.247) for v in dns]
    return {"dns": dns, "blocked": blocked}


# ── Integrations ──────────────────────────────────────────────

def healthchecks() -> dict:
    now = int(time.time())
    return {
        "ok": True,
        "name": "pi-guardian-heartbeat",
        "status": "up",
        "last_ping": datetime.fromtimestamp(now - 240, timezone.utc).isoformat(),
        "next_ping": datetime.fromtimestamp(now + 3360, timezone.utc).isoformat(),
        "n_pings": 5123,
        "period": 3600,
        "grace": 900,
        "flips": [],
    }


def ping() -> dict:
    results = [
        {"name": "Router",   "host": "192.168.1.1", "ms": round(_wave(30, 0.6, 2.2), 1), "ok": True},
        {"name": "Google",   "host": "8.8.8.8",     "ms": round(_wave(25, 9, 18), 1),    "ok": True},
        {"name": "Internet", "host": "1.1.1.1",     "ms": round(_wave(35, 7, 14), 1),    "ok": True},
    ]
    history = []
    base = int(time.time()) - 60 * 30
    for i in range(30):
        history.append({
            "t": base + i * 60,
            "results": [
                {"name": "Router",   "host": "192.168.1.1", "ms": round(1.2 + math.sin(i / 3) * 0.6, 1), "ok": True},
                {"name": "Google",   "host": "8.8.8.8",     "ms": round(13 + math.sin(i / 4) * 4, 1),     "ok": True},
                {"name": "Internet", "host": "1.1.1.1",     "ms": round(10 + math.cos(i / 5) * 3, 1),     "ok": True},
            ],
        })
    return {"ok": True, "results": results, "history": history}


def temp_history() -> dict:
    history = []
    base = int(time.time()) - 120 * 120
    for i in range(120):
        history.append({"t": base + i * 120, "v": round(48 + math.sin(i / 8) * 4, 1)})
    return {"ok": True, "history": history, "current": cpu_temp()}


# ── Users & events ────────────────────────────────────────────

def users() -> dict:
    base = time.time()
    return {
        "users": [
            {"id": 1, "username": "alice", "email": "alice@example.com",
             "verified": True, "created": time.strftime("%d.%m.%Y %H:%M", time.localtime(base - 9 * 86400))},
            {"id": 2, "username": "bob", "email": "bob@example.com",
             "verified": True, "created": time.strftime("%d.%m.%Y %H:%M", time.localtime(base - 4 * 86400))},
        ]
    }


def events() -> list:
    now = time.time()
    raw = [
        (-30,    "🚀 Pi Guardian started",            "info"),
        (-120,   "✅ Login: admin",                   "info"),
        (-900,   "⚙️ Settings updated",               "info"),
        (-3600,  "🛡 AdGuard restarted",              "warning"),
        (-7200,  "📧 Registration request: bob",      "info"),
        (-10800, "⚠️ CPU temperature high: 71.2°C",   "warning"),
        (-86400, "✅ Account approved: alice",         "info"),
    ]
    return [{"t": now + off, "msg": msg, "level": lvl} for off, msg, lvl in raw]
