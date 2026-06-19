"""
collector.py — shared data-collection module.
Imported by monitor.py and dashboard/main.py.

Gathers system metrics (CPU / RAM / disk / temperature) and AdGuard Home
statistics, and evaluates alert thresholds. When DEMO_MODE=1 it returns
realistic synthetic data instead (see demo_data.py).
"""

import os
import sys
import time
import subprocess

import requests as req
from dotenv import load_dotenv

_HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, _HERE)
load_dotenv(os.path.join(_HERE, ".env"))

DEMO_MODE = os.getenv("DEMO_MODE", "0").lower() in ("1", "true", "yes", "on")

AGH_HOST         = os.getenv("AGH_HOST",         "http://192.168.1.50")
AGH_USER         = os.getenv("AGH_USER",         "adguard")
AGH_PASS         = os.getenv("AGH_PASS",         "")
ALERT_CPU_TEMP   = float(os.getenv("ALERT_CPU_TEMP",   "75"))
ALERT_CPU_USAGE  = float(os.getenv("ALERT_CPU_USAGE",  "90"))
ALERT_RAM_USAGE  = float(os.getenv("ALERT_RAM_USAGE",  "90"))
ALERT_DISK_USAGE = float(os.getenv("ALERT_DISK_USAGE", "85"))

if DEMO_MODE:
    import demo_data


# ── CPU temperature ───────────────────────────────────────────

def get_cpu_temp() -> float:
    if DEMO_MODE:
        return demo_data.cpu_temp()
    try:
        out = subprocess.check_output(
            ["vcgencmd", "measure_temp"], stderr=subprocess.DEVNULL).decode()
        return float(out.strip().replace("temp=", "").replace("'C", ""))
    except Exception:
        try:
            return round(int(
                open("/sys/class/thermal/thermal_zone0/temp").read().strip()) / 1000, 1)
        except Exception:
            return 0.0


# ── System (CPU / RAM / disk / uptime) ────────────────────────

def get_system_stats() -> dict:
    if DEMO_MODE:
        return demo_data.system_stats()
    try:
        import psutil
        cpu  = psutil.cpu_percent(interval=0.5)
        ram  = psutil.virtual_memory()
        disk = psutil.disk_usage("/")
        up_s = time.time() - psutil.boot_time()
        d = int(up_s // 86400); h = int((up_s % 86400) // 3600); m = int((up_s % 3600) // 60)
        return {
            "cpu_percent":   round(cpu, 1),
            "cpu_temp":      get_cpu_temp(),
            "ram_percent":   round(ram.percent, 1),
            "ram_used_mb":   round(ram.used   / 1024**2, 1),
            "ram_total_mb":  round(ram.total  / 1024**2, 1),
            "disk_percent":  round(disk.percent, 1),
            "disk_used_gb":  round(disk.used  / 1024**3, 2),
            "disk_total_gb": round(disk.total / 1024**3, 2),
            "uptime":        f"{d}d {h}h {m}m" if d else f"{h}h {m}m",
        }
    except ImportError:
        # Fallback without psutil (reads /proc directly, Linux only).
        try:
            mi = {}
            for line in open("/proc/meminfo"):
                k, v = line.split(":"); mi[k.strip()] = int(v.strip().split()[0])
            total = mi["MemTotal"]; free = mi["MemAvailable"]; used = total - free
            st = os.statvfs("/")
            dt = st.f_blocks * st.f_frsize; df = st.f_bavail * st.f_frsize
            up_s = float(open("/proc/uptime").readline().split()[0])
            d = int(up_s // 86400); h = int((up_s % 86400) // 3600); m = int((up_s % 3600) // 60)
            return {
                "cpu_percent":   0.0,
                "cpu_temp":      get_cpu_temp(),
                "ram_percent":   round(used / total * 100, 1),
                "ram_used_mb":   round(used  / 1024, 1),
                "ram_total_mb":  round(total / 1024, 1),
                "disk_percent":  round((dt - df) / dt * 100, 1),
                "disk_used_gb":  round((dt - df) / 1024**3, 2),
                "disk_total_gb": round(dt / 1024**3, 2),
                "uptime":        f"{d}d {h}h {m}m" if d else f"{h}h {m}m",
            }
        except Exception:
            return {}


# ── AdGuard Home API ──────────────────────────────────────────

def get_adguard_stats() -> dict:
    if DEMO_MODE:
        return demo_data.adguard_stats()
    base = AGH_HOST.rstrip("/")
    auth = (AGH_USER, AGH_PASS) if AGH_PASS else None
    try:
        s = req.get(f"{base}/control/status", auth=auth, timeout=10).json()
        t = req.get(f"{base}/control/stats",  auth=auth, timeout=10).json()
        queries = t.get("num_dns_queries", 0)
        blocked = t.get("num_blocked_filtering", 0)
        return {
            "ok":                 True,
            "running":            s.get("running", False),
            "protection_enabled": s.get("protection_enabled", False),
            "version":            s.get("version", "?"),
            "dns_queries":        queries,
            "blocked":            blocked,
            "blocked_percent":    round(blocked / max(queries, 1) * 100, 1),
            "avg_ms":             round(t.get("avg_processing_time", 0) * 1000, 2),
            "top_blocked":        (t.get("top_blocked_domains") or [])[:5],
            "top_clients":        (t.get("top_clients") or [])[:5],
        }
    except req.exceptions.ConnectionError:
        return {"ok": False, "error": "Cannot connect to AdGuard Home"}
    except Exception as e:
        return {"ok": False, "error": str(e)}


# ── Full collection + alert detection ─────────────────────────

def collect_all() -> dict:
    from datetime import datetime
    if DEMO_MODE:
        return demo_data.collect_all()

    sys_   = get_system_stats()
    agh    = get_adguard_stats()
    alerts = []

    if sys_:
        if sys_.get("cpu_temp",    0) >= ALERT_CPU_TEMP:
            alerts.append(f"Critical temperature: {sys_['cpu_temp']}°C (threshold {ALERT_CPU_TEMP}°C)")
        if sys_.get("cpu_percent", 0) >= ALERT_CPU_USAGE:
            alerts.append(f"CPU overloaded: {sys_['cpu_percent']}% (threshold {ALERT_CPU_USAGE}%)")
        if sys_.get("ram_percent", 0) >= ALERT_RAM_USAGE:
            alerts.append(f"RAM critical: {sys_['ram_percent']}% (threshold {ALERT_RAM_USAGE}%)")
        if sys_.get("disk_percent", 0) >= ALERT_DISK_USAGE:
            alerts.append(f"Disk almost full: {sys_['disk_percent']}% (threshold {ALERT_DISK_USAGE}%)")
    if not agh.get("ok"):
        alerts.append(f"AdGuard Home offline: {agh.get('error', '?')}")
    elif not agh.get("protection_enabled"):
        alerts.append("DNS protection is disabled!")

    return {
        "timestamp": datetime.now().strftime("%d.%m.%Y %H:%M:%S"),
        "system":    sys_,
        "adguard":   agh,
        "alerts":    alerts,
    }
