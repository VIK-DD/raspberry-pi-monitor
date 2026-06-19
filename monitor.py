#!/usr/bin/env python3
"""
monitor.py — periodic reports and alerts.
Runs via cron. Reads data from collector.py.

Usage:
  python3 monitor.py report   — full report (e-mail + Telegram + healthcheck)
  python3 monitor.py alert    — send only if there are active alerts
  python3 monitor.py test     — print data to the terminal, no notifications
"""

import os, sys, json, smtplib, logging
import requests
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from dotenv import load_dotenv

BASE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, BASE)
from collector import collect_all

load_dotenv(os.path.join(BASE, ".env"))

GMAIL_USER       = os.getenv("GMAIL_USER",       "")
GMAIL_APP_PASS   = os.getenv("GMAIL_APP_PASS",   "")
EMAIL_TO         = os.getenv("EMAIL_TO",          GMAIL_USER)
TG_BOT_TOKEN     = os.getenv("TG_BOT_TOKEN",      "")
TG_CHAT_ID       = os.getenv("TG_CHAT_ID",        "")
UPTIME_KUMA_PUSH = os.getenv("UPTIME_KUMA_PUSH_URL", "")
HC_PING_URL      = os.getenv("HC_PING_URL",       "")
DEVICE_NAME      = os.getenv("DEVICE_NAME",       "Pi Guardian")
ALERT_CPU_TEMP   = float(os.getenv("ALERT_CPU_TEMP",   "75"))
ALERT_CPU_USAGE  = float(os.getenv("ALERT_CPU_USAGE",  "90"))
ALERT_RAM_USAGE  = float(os.getenv("ALERT_RAM_USAGE",  "90"))
ALERT_DISK_USAGE = float(os.getenv("ALERT_DISK_USAGE", "85"))

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[
        logging.FileHandler(os.path.join(BASE, "monitor.log")),
        logging.StreamHandler(sys.stdout),
    ],
)
log = logging.getLogger(__name__)


# ── Telegram ──────────────────────────────────────────────────

def send_telegram(msg: str) -> bool:
    if not TG_BOT_TOKEN:
        log.warning("Telegram: token not configured, skipping")
        return False
    try:
        r = requests.post(
            f"https://api.telegram.org/bot{TG_BOT_TOKEN}/sendMessage",
            json={"chat_id": TG_CHAT_ID, "text": msg, "parse_mode": "HTML"},
            timeout=12)
        if r.status_code == 200:
            log.info("Telegram: sent OK")
            return True
        log.error(f"Telegram: {r.status_code} — {r.text}")
        return False
    except Exception as e:
        log.error(f"Telegram exception: {e}")
        return False


# ── Gmail e-mail ──────────────────────────────────────────────

def send_email(subject: str, html: str) -> bool:
    if not GMAIL_APP_PASS:
        log.warning("Gmail: app password not configured, skipping")
        return False
    try:
        msg = MIMEMultipart("alternative")
        msg["Subject"] = subject
        msg["From"]    = GMAIL_USER
        msg["To"]      = EMAIL_TO
        msg.attach(MIMEText(html, "html", "utf-8"))

        smtp_host = os.getenv("SMTP_HOST", "smtp.gmail.com")
        smtp_port = int(os.getenv("SMTP_PORT", "587"))

        if smtp_port == 465:
            with smtplib.SMTP_SSL(smtp_host, smtp_port) as s:
                s.login(GMAIL_USER, GMAIL_APP_PASS)
                s.sendmail(GMAIL_USER, EMAIL_TO, msg.as_string())
        else:
            with smtplib.SMTP(smtp_host, smtp_port) as s:
                s.ehlo(); s.starttls(); s.ehlo()
                s.login(GMAIL_USER, GMAIL_APP_PASS)
                s.sendmail(GMAIL_USER, EMAIL_TO, msg.as_string())

        log.info(f"E-mail sent → {EMAIL_TO}")
        return True
    except Exception as e:
        log.error(f"E-mail exception: {e}")
        return False


# ── Uptime Kuma / Healthchecks.io heartbeat ───────────────────

def ping_healthcheck(status: str = "up", msg: str = "OK"):
    # Uptime Kuma push
    if UPTIME_KUMA_PUSH:
        try:
            url = UPTIME_KUMA_PUSH.rstrip("/")
            requests.get(f"{url}?status={status}&msg={requests.utils.quote(msg)}&ping=", timeout=10)
            log.info(f"Uptime Kuma ping → {status}")
        except Exception as e:
            log.error(f"Uptime Kuma exception: {e}")
    # Healthchecks.io ping
    if HC_PING_URL:
        try:
            if status == "down":
                requests.get(f"{HC_PING_URL}/fail", timeout=10)
                log.info("Healthchecks.io ping → FAIL")
            else:
                requests.get(HC_PING_URL, timeout=10)
                log.info("Healthchecks.io ping → OK")
        except Exception as e:
            log.error(f"Healthchecks.io exception: {e}")


# ── Telegram formatting ───────────────────────────────────────

def fmt_telegram_report(data: dict) -> str:
    s = data["system"]; a = data["adguard"]

    def lvl(v, w, c): return "🔴" if v >= c else ("🟡" if v >= w else "🟢")

    lines = [
        f"🛡 <b>{DEVICE_NAME} — Report</b>",
        f"🕐 {data['timestamp']}  |  ⏱ {s.get('uptime','--')}",
        "",
        "<b>📊 System</b>",
        f"{lvl(s.get('cpu_temp',0),    65, ALERT_CPU_TEMP)}  Temperature: <b>{s.get('cpu_temp','--')}°C</b>",
        f"{lvl(s.get('cpu_percent',0), 70, ALERT_CPU_USAGE)}  CPU: <b>{s.get('cpu_percent','--')}%</b>",
        f"{lvl(s.get('ram_percent',0), 75, ALERT_RAM_USAGE)}  RAM: <b>{s.get('ram_used_mb','--')}/{s.get('ram_total_mb','--')} MB</b> ({s.get('ram_percent','--')}%)",
        f"{lvl(s.get('disk_percent',0),75, ALERT_DISK_USAGE)}  Disk: <b>{s.get('disk_used_gb','--')}/{s.get('disk_total_gb','--')} GB</b> ({s.get('disk_percent','--')}%)",
        "",
    ]

    if a.get("ok"):
        prot = "✅ Active" if a.get("protection_enabled") else "❌ DISABLED"
        lines += [
            "<b>🛡 AdGuard Home</b>",
            f"  Protection: {prot}",
            f"  Queries 24h: <b>{a.get('dns_queries',0):,}</b>",
            f"  Blocked: <b>{a.get('blocked',0):,}</b> ({a.get('blocked_percent',0)}%)",
            f"  Avg time: <b>{a.get('avg_ms',0)} ms</b>",
        ]
        tops = a.get("top_blocked", [])
        if tops:
            lines.append("  Top blocked:")
            for item in tops[:3]:
                domain, count = (list(item.items())[0] if isinstance(item, dict) else (item, ""))
                lines.append(f"    · {domain} ({count})")
    else:
        lines.append(f"❌ <b>AdGuard OFFLINE</b>: {a.get('error','?')}")

    if data.get("alerts"):
        lines += ["", "⚠️ <b>ACTIVE ALERTS:</b>"]
        for x in data["alerts"]:
            lines.append(f"  • {x}")

    return "\n".join(lines)


def fmt_telegram_alert(data: dict) -> str:
    s = data["system"]
    lines = [
        f"🚨 <b>ALERT — {DEVICE_NAME}</b>",
        f"🕐 {data['timestamp']}",
        "",
        "<b>Issues detected:</b>",
    ]
    for x in data["alerts"]:
        lines.append(f"  ⚠️ {x}")
    lines += [
        "",
        f"🌡 Temp: {s.get('cpu_temp','--')}°C  |  CPU: {s.get('cpu_percent','--')}%",
        f"💾 RAM: {s.get('ram_percent','--')}%  |  Disk: {s.get('disk_percent','--')}%",
    ]
    return "\n".join(lines)


# ── HTML e-mail formatting ────────────────────────────────────

def fmt_email(data: dict) -> tuple:
    s = data["system"]; a = data["adguard"]; alerts = data.get("alerts", [])
    ok_str  = f"⚠️ {len(alerts)} ALERT" if alerts else "✅ All OK"
    subject = f"[{DEVICE_NAME}] {ok_str} — {data['timestamp']}"

    ac = "#e53e3e"; gc = "#38a169"; yc = "#d69e2e"
    def tc(v, w, c): return ac if v >= c else (yc if v >= w else gc)
    def row(k, v, col="#2d3748"):
        return (f'<tr><td style="padding:7px 14px;color:#718096;font-size:13px">{k}</td>'
                f'<td style="padding:7px 14px;font-weight:600;color:{col};font-size:13px">{v}</td></tr>')

    # System rows
    sys_rows = ""
    if s:
        sys_rows = (
            row("🌡 Temperature", f"{s.get('cpu_temp','--')}°C",
                tc(s.get('cpu_temp',0), 65, ALERT_CPU_TEMP)) +
            row("⚡ CPU", f"{s.get('cpu_percent','--')}%",
                tc(s.get('cpu_percent',0), 70, ALERT_CPU_USAGE)) +
            row("💾 RAM", f"{s.get('ram_used_mb','--')} / {s.get('ram_total_mb','--')} MB ({s.get('ram_percent','--')}%)",
                tc(s.get('ram_percent',0), 75, ALERT_RAM_USAGE)) +
            row("💿 Disk", f"{s.get('disk_used_gb','--')} / {s.get('disk_total_gb','--')} GB ({s.get('disk_percent','--')}%)",
                tc(s.get('disk_percent',0), 75, ALERT_DISK_USAGE)) +
            row("⏱ Uptime", s.get('uptime','--'))
        )

    # AdGuard section
    agh_html = ""
    if a.get("ok"):
        prot_c = gc if a.get("protection_enabled") else ac
        prot_v = "ACTIVE ✅" if a.get("protection_enabled") else "DISABLED ❌"
        top_rows = ""
        for item in (a.get("top_blocked") or [])[:3]:
            domain, count = (list(item.items())[0] if isinstance(item, dict) else (item, ""))
            top_rows += row(f"&nbsp;&nbsp;· {domain}", str(count))
        agh_html = f"""
        <h3 style="margin:20px 0 8px;color:#2d3748;font-size:15px">🛡 AdGuard Home</h3>
        <table style="width:100%;border-collapse:collapse;background:#f7fafc;border-radius:8px;overflow:hidden">
          {row("DNS protection", prot_v, prot_c)}
          {row("Version", a.get('version','?'))}
          {row("Queries 24h", f"{a.get('dns_queries',0):,}")}
          {row("Blocked", f"{a.get('blocked',0):,} ({a.get('blocked_percent',0)}%)", ac)}
          {row("Avg time", f"{a.get('avg_ms',0)} ms")}
          {top_rows}
        </table>"""
    else:
        agh_html = f'<p style="color:{ac};font-weight:600;margin-top:16px">❌ AdGuard Home OFFLINE: {a.get("error","?")}</p>'

    # Alerts
    alert_html = ""
    if alerts:
        items = "".join(f"<li style='margin:4px 0'>{x}</li>" for x in alerts)
        alert_html = f"""
        <div style="margin:16px 0;padding:14px 16px;background:#fff5f5;border-left:4px solid {ac};border-radius:4px">
          <b style="color:#c53030">⚠️ Active alerts</b>
          <ul style="margin:8px 0 0;padding-left:18px;color:#742a2a;font-size:13px">{items}</ul>
        </div>"""

    badge_bg = ac if alerts else gc
    badge_txt = ok_str

    html = f"""<!DOCTYPE html>
<html><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"></head>
<body style="font-family:Arial,sans-serif;background:#edf2f7;padding:24px;margin:0">
<div style="max-width:540px;margin:0 auto;background:#fff;border-radius:14px;overflow:hidden;box-shadow:0 2px 12px rgba(0,0,0,.1)">

  <div style="background:#1a202c;padding:22px 26px">
    <h2 style="color:#fff;margin:0;font-size:20px">🛡 {DEVICE_NAME}</h2>
    <p style="color:#a0aec0;margin:5px 0 0;font-size:13px">
      {data['timestamp']} &nbsp;·&nbsp; Uptime: {s.get('uptime','--')}
    </p>
  </div>

  <div style="padding:22px 26px">
    <div style="display:inline-block;padding:6px 16px;background:{badge_bg};color:#fff;border-radius:20px;font-size:13px;font-weight:700;margin-bottom:18px">
      {badge_txt}
    </div>

    {alert_html}

    <h3 style="margin:0 0 8px;color:#2d3748;font-size:15px">📊 System</h3>
    <table style="width:100%;border-collapse:collapse;background:#f7fafc;border-radius:8px;overflow:hidden">
      {sys_rows}
    </table>

    {agh_html}
  </div>

  <div style="padding:12px 26px;background:#f7fafc;text-align:center;font-size:11px;color:#a0aec0;border-top:1px solid #e2e8f0">
    {DEVICE_NAME} · Raspberry Pi · Automated report
  </div>
</div>
</body></html>"""

    return subject, html


# ── Run modes ─────────────────────────────────────────────────

def run_report():
    log.info("=== PERIODIC REPORT ===")
    data = collect_all()
    hc_ok = not bool(data.get("alerts"))
    ping_healthcheck("up" if hc_ok else "down",
                     "OK" if hc_ok else "; ".join(data["alerts"]))
    subj, html = fmt_email(data)
    send_email(subj, html)
    send_telegram(fmt_telegram_report(data))
    log.info("Full report sent.")


def run_alert():
    log.info("=== ALERT CHECK ===")
    data = collect_all()
    hc_ok = not bool(data.get("alerts"))
    ping_healthcheck("up" if hc_ok else "down",
                     "OK" if hc_ok else "; ".join(data["alerts"]))
    if data.get("alerts"):
        log.warning(f"Alerts detected: {data['alerts']}")
        send_telegram(fmt_telegram_alert(data))
        subj, html = fmt_email(data)
        send_email(f"🚨 {subj}", html)
    else:
        log.info("No alerts — all OK.")


if __name__ == "__main__":
    mode = sys.argv[1] if len(sys.argv) > 1 else "report"
    if   mode == "report": run_report()
    elif mode == "alert":  run_alert()
    elif mode == "test":
        data = collect_all()
        print(json.dumps(data, indent=2, ensure_ascii=False))
        print("\n--- TELEGRAM PREVIEW ---")
        print(fmt_telegram_report(data))
    else:
        print("Usage: python3 monitor.py [report|alert|test]")
        sys.exit(1)
