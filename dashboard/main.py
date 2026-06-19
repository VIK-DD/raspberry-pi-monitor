#!/usr/bin/env python3
"""
dashboard/main.py — Pi Guardian
FastAPI dashboard: live stats over WebSocket, auth, rate limiting,
AdGuard Home / Healthchecks.io integration and remote system actions.
"""
from __future__ import annotations
import os, sys, json, time, asyncio, logging, hashlib, hmac, secrets
from contextlib import asynccontextmanager
from pathlib import Path
from fastapi import FastAPI, WebSocket, WebSocketDisconnect, Request, Cookie, HTTPException
from fastapi.responses import HTMLResponse, JSONResponse, RedirectResponse
import sqlite3
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.gzip import GZipMiddleware
from dotenv import load_dotenv

BASE = Path(__file__).parent.parent
DB_PATH = str(BASE / "events.db")
sys.path.insert(0, str(BASE))
from collector import collect_all, get_cpu_temp, DEMO_MODE

if DEMO_MODE:
    import demo_data

load_dotenv(BASE / ".env")

PORT          = int(os.getenv("DASHBOARD_PORT",   "8080"))
REFRESH       = int(os.getenv("REFRESH_INTERVAL", "5"))
DEVICE_NAME   = os.getenv("DEVICE_NAME", "Pi Guardian")
AGH_HOST      = os.getenv("AGH_HOST", "http://192.168.1.2")
TAILSCALE_IP  = os.getenv("TAILSCALE_IP", "")
AGH_USER      = os.getenv("AGH_USER", "adguard")
AGH_PASS      = os.getenv("AGH_PASS", "")
HC_API_KEY    = os.getenv("HC_API_KEY", "")
HC_UUID       = os.getenv("HC_UUID", "")
GMAIL_USER    = os.getenv("GMAIL_USER", "")
GMAIL_APP_PASS = os.getenv("GMAIL_APP_PASS", "")
SMTP_HOST     = os.getenv("SMTP_HOST", "smtp.gmail.com")
SMTP_PORT     = int(os.getenv("SMTP_PORT", "587"))


def public_base_url() -> str:
    """Base URL used in outgoing e-mail links (Tailscale IP if set, else localhost)."""
    host = TAILSCALE_IP or "localhost"
    return f"http://{host}:{PORT}"


def email_enabled() -> bool:
    return bool(GMAIL_USER and GMAIL_APP_PASS) and not DEMO_MODE


# ── Auth ──────────────────────────────────────────────────────
DASHBOARD_USER = os.getenv("DASHBOARD_USER", "admin")
DASHBOARD_PASS = os.getenv("DASHBOARD_PASS", "")   # no insecure default
SESSION_TTL    = 24 * 3600
PBKDF2_ROUNDS  = 200_000

_sessions: dict = {}


def hash_pass(p: str, salt: str | None = None) -> str:
    """Return a salted PBKDF2-SHA256 hash in the form ``salt$hexdigest``."""
    if salt is None:
        salt = secrets.token_hex(16)
    dk = hashlib.pbkdf2_hmac("sha256", p.encode(), salt.encode(), PBKDF2_ROUNDS)
    return f"{salt}${dk.hex()}"


def verify_pass(p: str, stored: str) -> bool:
    """Constant-time verification against a ``salt$hexdigest`` hash."""
    if not stored or "$" not in stored:
        return False
    salt = stored.split("$", 1)[0]
    return hmac.compare_digest(hash_pass(p, salt), stored)


PASS_HASH = hash_pass(DASHBOARD_PASS) if DASHBOARD_PASS else None


def create_session(username: str = "") -> str:
    token = secrets.token_hex(32)
    _sessions[token] = {"expires": time.time() + SESSION_TTL, "user": username}
    return token


def valid_session(request: Request) -> bool:
    if DEMO_MODE:          # public demo: no authentication wall
        return True
    token = request.cookies.get("pi_session", "")
    if not token or token not in _sessions:
        return False
    if time.time() > _sessions[token]["expires"]:
        del _sessions[token]
        return False
    return True


# ── Rate limiting ─────────────────────────────────────────────
_rl: dict = {}
RULES = {"critical": 60, "service": 10, "api": 2}


def check_rate(request: Request, rule: str = "api") -> bool:
    ip = request.client.host if request.client else "unknown"
    limit = RULES.get(rule, 5)
    now = time.time()
    if ip not in _rl:
        _rl[ip] = {}
    if now - _rl[ip].get(rule, 0) < limit:
        return False
    _rl[ip][rule] = now
    return True


# ── Settings ──────────────────────────────────────────────────
SETTINGS_FILE = BASE / "settings.json"

_settings_defaults = {
    "alert_cpu_temp":   float(os.getenv("ALERT_CPU_TEMP",   "75")),
    "alert_cpu_usage":  float(os.getenv("ALERT_CPU_USAGE",  "90")),
    "alert_ram_usage":  float(os.getenv("ALERT_RAM_USAGE",  "90")),
    "alert_disk_usage": float(os.getenv("ALERT_DISK_USAGE", "85")),
    "report_hours":     int(os.getenv("REPORT_HOURS",       "12")),
    "device_name":      DEVICE_NAME,
    "weather_city":     os.getenv("WEATHER_CITY", "London"),
    "refresh_interval": REFRESH,
}


def load_settings() -> dict:
    s = dict(_settings_defaults)
    try:
        if SETTINGS_FILE.exists():
            saved = json.loads(SETTINGS_FILE.read_text())
            for k, v in saved.items():
                if k in s:
                    s[k] = v
    except Exception as e:
        print(f"Could not load settings.json: {e}")
    return s


def save_settings(s: dict):
    try:
        SETTINGS_FILE.write_text(json.dumps(s, indent=2, ensure_ascii=False))
    except Exception as e:
        print(f"Could not save settings.json: {e}")


_settings = load_settings()

_events: list = []


def add_event(msg: str, level: str = "info", ip: str | None = None):
    evt = {"t": time.time(), "msg": msg, "level": level}
    if ip:
        evt["ip"] = ip
    _events.append(evt)
    if len(_events) > 200:
        _events.pop(0)


_temp_history: list = []
_ping_history: list = []

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
log = logging.getLogger(__name__)


# ── App lifespan ──────────────────────────────────────────────
@asynccontextmanager
async def lifespan(app: FastAPI):
    if DEMO_MODE:
        _events.extend(demo_data.events())
    task = asyncio.create_task(broadcast_loop())
    add_event("🚀 Pi Guardian started", "info")
    log.info(f"{DEVICE_NAME} → http://0.0.0.0:{PORT}  (demo={DEMO_MODE})")
    yield
    task.cancel()


app = FastAPI(title=DEVICE_NAME, lifespan=lifespan)
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"])
app.add_middleware(GZipMiddleware, minimum_size=500)


@app.middleware("http")
async def security_headers(request, call_next):
    response = await call_next(request)
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["X-Frame-Options"] = "DENY"
    response.headers["X-XSS-Protection"] = "1; mode=block"
    response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
    return response


STATIC = Path(__file__).parent / "static"

_cache: dict = {}
_cache_ts: float = 0.0


def get_cached() -> dict:
    global _cache, _cache_ts
    if time.time() - _cache_ts < 8 and _cache:
        return _cache
    _cache = collect_all()
    _cache_ts = time.time()
    return _cache


def serve(f: str) -> HTMLResponse:
    p = STATIC / f
    return HTMLResponse(p.read_text(encoding="utf-8") if p.exists() else f"<h1>{f} not found</h1>")


def guard(request: Request, page: str):
    if not valid_session(request):
        return RedirectResponse(url="/login", status_code=302)
    return serve(page)


# ── API auth middleware ───────────────────────────────────────
@app.middleware("http")
async def auth_check(request: Request, call_next):
    path = request.url.path
    public = ["/login", "/register", "/static/", "/ws", "/api/device", "/api/events", "/api/sysinfo"]
    if any(path.startswith(p) for p in public):
        return await call_next(request)
    if path.startswith("/api/"):
        if not valid_session(request):
            return JSONResponse({"error": "Unauthorized"}, status_code=401)
    return await call_next(request)


def _db_user_password(username: str) -> str | None:
    """Return the stored password hash for a verified user, or None."""
    try:
        conn = sqlite3.connect(DB_PATH)
        row = conn.execute(
            "SELECT password FROM users WHERE username=? AND verified=1", (username,)
        ).fetchone()
        conn.close()
        return row[0] if row else None
    except Exception:
        return None


def _db_user_exists(username: str) -> bool:
    try:
        conn = sqlite3.connect(DB_PATH)
        row = conn.execute("SELECT id FROM users WHERE username=?", (username,)).fetchone()
        conn.close()
        return bool(row)
    except Exception:
        return False


# ── Login / Logout ────────────────────────────────────────────
@app.get("/login", response_class=HTMLResponse)
async def login_get(request: Request):
    if valid_session(request) and not DEMO_MODE:
        return RedirectResponse(url="/", status_code=302)
    return serve("login.html")


@app.post("/login")
async def login_post(request: Request):
    form = await request.form()
    user = form.get("username", "")
    pw   = form.get("password", "")

    def check_login(u, p):
        if PASS_HASH and u == DASHBOARD_USER and verify_pass(p, PASS_HASH):
            return True
        stored = _db_user_password(u)
        return bool(stored and verify_pass(p, stored))

    if check_login(user, pw):
        token = create_session(user)
        add_event(f"✅ Login: {user}", "info")
        resp = RedirectResponse(url="/", status_code=302)
        resp.set_cookie("pi_session", token, max_age=SESSION_TTL, httponly=True, samesite="lax")
        return resp

    user_exists = (user == DASHBOARD_USER) or _db_user_exists(user)
    ip = request.client.host if request.client else "?"
    add_event(f"❌ Login failed — {ip}", "critical")

    login_html = serve("login.html").body.decode()
    login_html = login_html.replace('id="err"', 'id="err" style="display:flex"')
    if not user_exists:
        login_html = login_html.replace(
            "Incorrect username or password", "This account is not registered"
        )
    return HTMLResponse(login_html, status_code=401)


@app.get("/logout")
@app.post("/logout")
async def logout(request: Request):
    token = request.cookies.get("pi_session", "")
    if token in _sessions:
        del _sessions[token]
    ip = request.client.host if request.client else "?"
    add_event(f"👋 Logout from {ip}", "info")
    resp = RedirectResponse(url="/login", status_code=302)
    resp.delete_cookie("pi_session")
    return resp


# ── Register ──────────────────────────────────────────────────
_pending: dict = {}  # token -> {username, password, email, ts}


@app.get("/register", response_class=HTMLResponse)
async def register_get(request: Request):
    err = request.query_params.get("e")
    succ = request.query_params.get("success")
    html = serve("register.html").body.decode()

    # Strip the query string on load so it does not persist across refreshes.
    clean_script = "<script>if(window.history.replaceState) window.history.replaceState({}, document.title, '/register');</script>"
    if "</body>" in html:
        html = html.replace("</body>", f"{clean_script}\n</body>")
    else:
        html += clean_script

    if succ:
        html = html.replace('id="reg-success"', 'id="reg-success" style="display:flex"')
        return HTMLResponse(html)

    if err:
        msg = "Unknown error."
        if err == "invalid":      msg = "Invalid data. Check the requirements."
        elif err == "reserved":   msg = "This name is reserved."
        elif err == "user_taken": msg = "This username is already taken."
        elif err == "email_taken": msg = "This e-mail is already registered."

        html = html.replace('id="reg-error"', 'id="reg-error" style="display:flex"')
        html = html.replace('USERNAME_ERROR', msg)

    return HTMLResponse(html)


@app.post("/register")
async def register_post(request: Request):
    form     = await request.form()
    username = form.get("username", "").strip()
    password = form.get("password", "")
    email    = form.get("email", "").strip()

    if len(username) < 3 or len(password) < 8:
        return RedirectResponse(url="/register?e=invalid", status_code=303)

    if username.lower() == DASHBOARD_USER.lower():
        return RedirectResponse(url="/register?e=reserved", status_code=303)

    # Reject duplicate username / e-mail.
    try:
        conn = sqlite3.connect(DB_PATH)
        conn.execute("CREATE TABLE IF NOT EXISTS users (id INTEGER PRIMARY KEY, username TEXT UNIQUE, password TEXT, email TEXT, verified INTEGER DEFAULT 1, created REAL)")
        if conn.execute("SELECT 1 FROM users WHERE LOWER(username)=LOWER(?)", (username,)).fetchone():
            conn.close()
            return RedirectResponse(url="/register?e=user_taken", status_code=303)
        if conn.execute("SELECT 1 FROM users WHERE LOWER(email)=LOWER(?)", (email,)).fetchone():
            conn.close()
            return RedirectResponse(url="/register?e=email_taken", status_code=303)
        conn.close()
    except Exception as e:
        log.error(f"Duplicate check error: {e}")

    token = secrets.token_urlsafe(32)
    _pending[token] = {"username": username, "password": hash_pass(password), "email": email, "ts": time.time()}

    # E-mail the admin with approve / reject links.
    if email_enabled():
        try:
            import smtplib
            from email.mime.text import MIMEText
            from email.mime.multipart import MIMEMultipart
            admin_email = os.getenv("EMAIL_TO", GMAIL_USER)
            base_url    = public_base_url()
            approve_url = f"{base_url}/admin/approve/{token}"
            reject_url  = f"{base_url}/admin/reject/{token}"
            ip = request.client.host if request.client else "?"
            msg = MIMEMultipart("alternative")
            msg["Subject"] = f"[Pi Guardian] ⏳ Access request: {username}"
            msg["From"] = GMAIL_USER; msg["To"] = admin_email
            html_body = f"""<!DOCTYPE html>
<html><head><meta charset="UTF-8"></head>
<body style="margin:0;padding:0;background:#07090f;font-family:Arial,sans-serif">
<table width="100%" cellpadding="0" cellspacing="0" style="background:#07090f;padding:40px 20px">
  <tr><td align="center">
    <table width="520" cellpadding="0" cellspacing="0" style="background:#0d1018;border-radius:18px;border:1px solid rgba(255,255,255,.07);overflow:hidden">
      <tr><td style="background:linear-gradient(135deg,#0d1018,#131720);padding:28px 32px;border-bottom:1px solid rgba(255,255,255,.07)">
        <table cellpadding="0" cellspacing="0"><tr>
          <td style="background:linear-gradient(135deg,#4fc3f7,#8b7cf8);border-radius:12px;width:44px;height:44px;text-align:center;vertical-align:middle;font-size:22px">🛡</td>
          <td style="padding-left:14px">
            <div style="color:#eceef5;font-size:18px;font-weight:800;letter-spacing:-.3px">Pi Guardian</div>
            <div style="color:#6b7591;font-size:12px;margin-top:2px">New account request</div>
          </td>
        </tr></table>
      </td></tr>
      <tr><td style="padding:28px 32px">
        <div style="background:rgba(251,191,36,.06);border:1px solid rgba(251,191,36,.2);border-radius:12px;padding:16px 20px;margin-bottom:24px">
          <div style="color:#fbbf24;font-size:11px;font-weight:700;letter-spacing:1.5px;text-transform:uppercase;margin-bottom:10px">⏳ Pending request</div>
          <table cellpadding="0" cellspacing="0" width="100%">
            <tr><td style="color:#6b7591;font-size:12px;padding:5px 0;border-bottom:1px solid rgba(255,255,255,.05)">Username</td><td align="right" style="color:#eceef5;font-size:12px;font-weight:700;padding:5px 0;border-bottom:1px solid rgba(255,255,255,.05)">{username}</td></tr>
            <tr><td style="color:#6b7591;font-size:12px;padding:5px 0;border-bottom:1px solid rgba(255,255,255,.05)">E-mail</td><td align="right" style="color:#eceef5;font-size:12px;font-weight:700;padding:5px 0;border-bottom:1px solid rgba(255,255,255,.05)">{email}</td></tr>
            <tr><td style="color:#6b7591;font-size:12px;padding:5px 0">IP</td><td align="right" style="color:#eceef5;font-size:12px;font-weight:700;padding:5px 0">{ip}</td></tr>
          </table>
        </div>
        <div style="color:#6b7591;font-size:13px;margin-bottom:20px">Approve or reject access to the dashboard.</div>
        <table cellpadding="0" cellspacing="0" width="100%"><tr>
          <td width="48%"><a href="{approve_url}" style="display:block;background:linear-gradient(135deg,#34d399,#059669);color:#fff;padding:14px;border-radius:12px;text-decoration:none;text-align:center;font-weight:700;font-size:14px">✅ Approve account</a></td>
          <td width="4%"></td>
          <td width="48%"><a href="{reject_url}" style="display:block;background:linear-gradient(135deg,#f87171,#dc2626);color:#fff;padding:14px;border-radius:12px;text-decoration:none;text-align:center;font-weight:700;font-size:14px">❌ Reject account</a></td>
        </tr></table>
      </td></tr>
      <tr><td style="padding:16px 32px;border-top:1px solid rgba(255,255,255,.05);text-align:center">
        <div style="color:#6b7591;font-size:11px">Pi Guardian · Raspberry Pi · Admin dashboard</div>
      </td></tr>
    </table>
  </td></tr>
</table>
</body></html>"""
            msg.attach(MIMEText(html_body, "html", "utf-8"))
            with smtplib.SMTP(SMTP_HOST, SMTP_PORT) as s:
                s.ehlo(); s.starttls(); s.login(GMAIL_USER, GMAIL_APP_PASS)
                s.sendmail(GMAIL_USER, admin_email, msg.as_string())
            add_event(f"📧 Registration request: {username}", "info", ip=ip)
        except Exception as e:
            log.error(f"Register email: {e}")

    return RedirectResponse(url="/register?success=1", status_code=303)


@app.get("/admin/approve-success", response_class=HTMLResponse)
async def approve_success(): return serve("approve.html")


@app.get("/admin/reject-success", response_class=HTMLResponse)
async def reject_success(): return serve("reject.html")


@app.get("/admin/approve/{token}", response_class=HTMLResponse)
async def admin_approve(token: str):
    reg = _pending.get(token)
    if not reg:
        return HTMLResponse("<h1>Invalid or expired link.</h1>")
    try:
        conn = sqlite3.connect(DB_PATH)
        conn.execute("CREATE TABLE IF NOT EXISTS users (id INTEGER PRIMARY KEY, username TEXT UNIQUE, password TEXT, email TEXT, verified INTEGER DEFAULT 1, created REAL)")
        conn.execute("INSERT OR IGNORE INTO users (username,password,email,verified,created) VALUES (?,?,?,1,?)",
                     (reg["username"], reg["password"], reg["email"], time.time()))
        conn.commit(); conn.close()
        del _pending[token]
        add_event(f"✅ Account approved: {reg['username']}", "info")
        if email_enabled():
            _send_account_email(reg["email"], reg["username"], approved=True)
        return RedirectResponse(url=f"/admin/approve-success?u={reg['username']}&e={reg['email']}", status_code=302)
    except Exception as e:
        return HTMLResponse(f"<h2 style='font-family:Arial;padding:40px;color:red'>Error: {e}</h2>")


@app.get("/admin/reject/{token}", response_class=HTMLResponse)
async def admin_reject(token: str):
    reg = _pending.get(token)
    if not reg:
        return HTMLResponse("<h1>Invalid or already-processed link.</h1>")
    username = reg["username"]
    user_email = reg.get("email", "")
    del _pending[token]
    add_event(f"❌ Account rejected: {username}", "warning")
    if email_enabled():
        _send_account_email(user_email, username, approved=False)
    return RedirectResponse(url=f"/admin/reject-success?u={username}", status_code=302)


def _send_account_email(to_email: str, username: str, approved: bool):
    """Notify a user that their account request was approved or rejected."""
    try:
        import smtplib
        from email.mime.text import MIMEText
        from email.mime.multipart import MIMEMultipart
        color   = "#34d399" if approved else "#f87171"
        bg      = "rgba(52,211,153" if approved else "rgba(248,113,113"
        icon    = "✅" if approved else "❌"
        title   = "Your account has been approved!" if approved else "Your request was rejected"
        status  = "✅ Approved" if approved else "❌ Rejected"
        if approved:
            sub  = "Welcome to Pi Guardian! You can now sign in to the dashboard."
            cta  = f'<a href="{public_base_url()}/login" style="display:block;background:linear-gradient(135deg,#4fc3f7,#8b7cf8);color:#fff;padding:14px;border-radius:12px;text-decoration:none;text-align:center;font-weight:700;font-size:14px">→ Open the dashboard</a>'
        else:
            sub  = "Sorry, your access request to Pi Guardian was rejected by the administrator."
            cta  = ""
        umsg = MIMEMultipart("alternative")
        umsg["Subject"] = f"[Pi Guardian] {icon} {title}"
        umsg["From"] = GMAIL_USER; umsg["To"] = to_email
        body = f"""<!DOCTYPE html>
<html><head><meta charset="UTF-8"></head>
<body style="margin:0;padding:0;background:#07090f;font-family:Arial,sans-serif">
<table width="100%" cellpadding="0" cellspacing="0" style="background:#07090f;padding:40px 20px"><tr><td align="center">
  <table width="520" cellpadding="0" cellspacing="0" style="background:#0d1018;border-radius:18px;border:1px solid rgba(255,255,255,.07);overflow:hidden">
    <tr><td style="padding:32px;text-align:center">
      <div style="width:64px;height:64px;background:{bg},.1);border:1px solid {bg},.25);border-radius:18px;display:inline-flex;align-items:center;justify-content:center;font-size:30px;margin-bottom:16px">{icon}</div>
      <div style="color:#eceef5;font-size:20px;font-weight:800;margin-bottom:8px">{title}</div>
      <div style="color:#6b7591;font-size:13px;line-height:1.6;margin-bottom:20px">{sub}</div>
      <div style="background:{bg},.06);border:1px solid {bg},.2);border-radius:12px;padding:14px 18px;margin-bottom:20px;text-align:left">
        <table cellpadding="0" cellspacing="0" width="100%">
          <tr><td style="color:#6b7591;font-size:12px;padding:4px 0">Username</td><td align="right" style="color:{color};font-size:12px;font-weight:700;padding:4px 0">{username}</td></tr>
          <tr><td style="color:#6b7591;font-size:12px;padding:4px 0">Status</td><td align="right" style="color:{color};font-size:12px;font-weight:700;padding:4px 0">{status}</td></tr>
        </table>
      </div>
      {cta}
    </td></tr>
    <tr><td style="padding:16px 32px;border-top:1px solid rgba(255,255,255,.05);text-align:center">
      <div style="color:#6b7591;font-size:11px">Pi Guardian · Raspberry Pi</div>
    </td></tr>
  </table>
</td></tr></table>
</body></html>"""
        umsg.attach(MIMEText(body, "html", "utf-8"))
        with smtplib.SMTP(SMTP_HOST, SMTP_PORT) as s:
            s.ehlo(); s.starttls(); s.login(GMAIL_USER, GMAIL_APP_PASS)
            s.sendmail(GMAIL_USER, to_email, umsg.as_string())
    except Exception as e:
        log.error(f"Account notification email: {e}")


# ── Pages ─────────────────────────────────────────────────────
@app.get("/",             response_class=HTMLResponse)
async def pg_home(r: Request):     return guard(r, "index.html")

@app.get("/adguard",      response_class=HTMLResponse)
async def pg_adguard(r: Request):  return guard(r, "adguard.html")

@app.get("/healthchecks", response_class=HTMLResponse)
async def pg_hc(r: Request):       return guard(r, "healthchecks.html")

@app.get("/network",      response_class=HTMLResponse)
async def pg_net(r: Request):      return guard(r, "network.html")

@app.get("/alerts",       response_class=HTMLResponse)
async def pg_alerts(r: Request):   return guard(r, "alerts.html")

@app.get("/system",       response_class=HTMLResponse)
async def pg_system(r: Request):   return guard(r, "system.html")

@app.get("/settings",     response_class=HTMLResponse)
async def pg_settings(r: Request): return guard(r, "settings.html")


# ── API ───────────────────────────────────────────────────────
@app.get("/api/stats")
async def api_stats(): return get_cached()


@app.get("/api/device")
async def api_device(request: Request):
    token = request.cookies.get("pi_session", "")
    s = _sessions.get(token)
    username = s.get("user") if s else None
    return {"name": _settings["device_name"], "username": username}


@app.get("/api/sysinfo")
async def api_sysinfo():
    if DEMO_MODE:
        return demo_data.sysinfo()
    import platform
    try:
        import subprocess
        os_info = subprocess.check_output(["uname", "-r"], stderr=subprocess.DEVNULL).decode().strip()
    except Exception:
        os_info = platform.release()
    return {
        "python": sys.version.split()[0],
        "os": platform.system(),
        "kernel": os_info,
        "arch": platform.machine(),
        "hostname": platform.node(),
    }


@app.delete("/api/users/{username}")
async def api_delete_user(username: str, request: Request):
    if not valid_session(request):
        raise HTTPException(status_code=401, detail="Unauthorized")
    try:
        conn = sqlite3.connect(DB_PATH)
        conn.execute("DELETE FROM users WHERE username=?", (username,))
        conn.commit(); conn.close()
        add_event(f"🗑 Account deleted: {username}", "warning")
        return {"ok": True}
    except Exception as e:
        return {"ok": False, "error": str(e)}


@app.get("/api/users")
async def api_users(pi_session: str = Cookie(default=None)):
    if DEMO_MODE:
        return demo_data.users()
    if not pi_session or pi_session not in _sessions:
        raise HTTPException(status_code=401, detail="Unauthorized")
    try:
        conn = sqlite3.connect(DB_PATH)
        rows = conn.execute(
            "SELECT id, username, email, verified, created FROM users ORDER BY created DESC"
        ).fetchall()
        conn.close()
        return {"users": [{"id": r[0], "username": r[1], "email": r[2],
                           "verified": bool(r[3]),
                           "created": time.strftime("%d.%m.%Y %H:%M", time.localtime(r[4]))} for r in rows]}
    except Exception as e:
        return {"users": [], "error": str(e)}


@app.get("/api/settings")
async def api_settings_get(): return _settings


@app.post("/api/settings")
async def api_settings_post(request: Request):
    global _settings
    data = await request.json()
    for k, v in data.items():
        if k in _settings:
            _settings[k] = v
    save_settings(_settings)
    add_event("⚙️ Settings updated", "info")
    return {"ok": True, "settings": _settings}


@app.get("/api/adguard/history")
async def api_agh_history():
    if DEMO_MODE:
        return demo_data.adguard_history()
    import requests as rq
    auth = (AGH_USER, AGH_PASS) if AGH_PASS else None
    try:
        d = rq.get(f"{AGH_HOST.rstrip('/')}/control/stats", auth=auth, timeout=6).json()
        return {"dns": d.get("dns_queries", []), "blocked": d.get("blocked_filtering", [])}
    except Exception as e:
        return {"dns": [], "blocked": [], "error": str(e)}


@app.post("/api/adguard/restart")
async def api_agh_restart(request: Request):
    if not check_rate(request, "service"):
        return JSONResponse({"ok": False, "error": "Too many requests. Wait 10s."}, status_code=429)
    if DEMO_MODE:
        add_event("🛡 AdGuard restarted (demo)", "warning")
        return {"ok": True}
    import requests as rq
    auth = (AGH_USER, AGH_PASS) if AGH_PASS else None
    try:
        rq.post(f"{AGH_HOST.rstrip('/')}/control/protection", auth=auth, json={"enabled": False}, timeout=5)
        await asyncio.sleep(1)
        rq.post(f"{AGH_HOST.rstrip('/')}/control/protection", auth=auth, json={"enabled": True}, timeout=5)
        add_event("🛡 AdGuard restarted", "warning")
        return {"ok": True}
    except Exception as e:
        return {"ok": False, "error": str(e)}


def _run_action(cmd: list, event_msg: str, level: str = "warning") -> dict:
    """Run a privileged system command (no-op in demo mode)."""
    add_event(event_msg, level)
    if DEMO_MODE:
        return {"ok": True, "demo": True}
    import subprocess
    try:
        subprocess.Popen(cmd)
        return {"ok": True}
    except Exception as e:
        return {"ok": False, "error": str(e)}


@app.post("/api/actions/reboot")
async def action_reboot(request: Request):
    if not check_rate(request, "critical"):
        return JSONResponse({"ok": False, "error": "Wait 60s between reboots."}, status_code=429)
    res = _run_action(["sudo", "reboot"], "⚡ Reboot triggered", "critical")
    if res.get("ok"):
        res["msg"] = "Rebooting..."
    return res


@app.post("/api/actions/shutdown")
async def action_shutdown(request: Request):
    if not check_rate(request, "critical"):
        return JSONResponse({"ok": False, "error": "Wait 60s."}, status_code=429)
    res = _run_action(["sudo", "shutdown", "-h", "now"], "🔴 Shutdown triggered", "critical")
    if res.get("ok"):
        res["msg"] = "Shutting down..."
    return res


@app.post("/api/actions/restart-dashboard")
async def action_restart_dash(request: Request):
    if not check_rate(request, "service"):
        return JSONResponse({"ok": False, "error": "Wait 10s."}, status_code=429)
    return _run_action(["pm2", "restart", "pi-dashboard"], "🔃 Dashboard restarted")


@app.post("/api/actions/restart-uptime-kuma")
async def action_restart_uptime_kuma(request: Request):
    if not check_rate(request, "service"):
        return JSONResponse({"ok": False, "error": "Wait 10s."}, status_code=429)
    return _run_action(["pm2", "restart", "uptime-kuma"], "📡 Uptime Kuma restarted")


@app.post("/api/actions/restart-adguard-service")
async def action_restart_agh_svc(request: Request):
    if not check_rate(request, "service"):
        return JSONResponse({"ok": False, "error": "Wait 10s."}, status_code=429)
    return _run_action(["sudo", "systemctl", "restart", "AdGuardHome"], "🛡 AdGuard service restarted")


@app.get("/api/system/info")
async def api_system_info():
    if DEMO_MODE:
        return demo_data.system_info()
    import socket
    try:
        import psutil
        boot = psutil.boot_time()
        up_s = time.time() - boot
        d = int(up_s // 86400); h = int((up_s % 86400) // 3600); m = int((up_s % 3600) // 60)
        return {
            "ok": True,
            "uptime_str": f"{d}d {h}h {m}m" if d else f"{h}h {m}m",
            "boot_time_str": time.strftime("%d.%m.%Y %H:%M", time.localtime(boot)),
            "hostname": socket.gethostname(),
        }
    except Exception as e:
        return {"ok": False, "error": str(e)}


@app.get("/api/events")
async def api_events(limit: int = 100, level: str = "all"):
    evs = list(reversed(_events))
    if level and level != "all":
        evs = [e for e in evs if e.get("level") == level]
    return {"events": evs[:min(limit, 500)]}


@app.post("/api/events")
async def api_add_event(request: Request):
    data = await request.json()
    add_event(data.get("msg", "?"), data.get("level", "info"))
    return {"ok": True}


@app.get("/api/disk-io")
async def api_disk_io():
    if DEMO_MODE:
        return demo_data.disk_io()
    try:
        import psutil
        d1 = psutil.disk_io_counters()
        await asyncio.sleep(1)
        d2 = psutil.disk_io_counters()
        return {
            "ok": True,
            "read_kb_s":      round((d2.read_bytes  - d1.read_bytes)  / 1024, 2),
            "write_kb_s":     round((d2.write_bytes - d1.write_bytes) / 1024, 2),
            "total_read_mb":  round(d2.read_bytes  / 1024**2, 1),
            "total_write_mb": round(d2.write_bytes / 1024**2, 1),
            "read_count":     d2.read_count,
            "write_count":    d2.write_count,
        }
    except Exception as e:
        return {"ok": False, "error": str(e)}


@app.get("/api/ping")
async def api_ping():
    if DEMO_MODE:
        return demo_data.ping()
    import subprocess, re
    targets = [
        {"name": "Router",   "host": "192.168.1.1"},
        {"name": "Google",   "host": "8.8.8.8"},
        {"name": "Internet", "host": "1.1.1.1"},
    ]
    results = []
    for t in targets:
        try:
            param = "-n" if os.name == "nt" else "-c"
            out = subprocess.check_output(
                ["ping", param, "1", "-W", "2", t["host"]],
                stderr=subprocess.DEVNULL, timeout=4).decode()
            m = re.search(r"time[=<]([\d.]+)", out)
            results.append({"name": t["name"], "host": t["host"], "ms": float(m.group(1)) if m else 0, "ok": True})
        except Exception:
            results.append({"name": t["name"], "host": t["host"], "ms": -1, "ok": False})
    _ping_history.append({"t": int(time.time()), "results": results})
    if len(_ping_history) > 720:
        _ping_history.pop(0)
    return {"ok": True, "results": results, "history": _ping_history[-60:]}


@app.get("/api/temp-history")
async def api_temp():
    if DEMO_MODE:
        return demo_data.temp_history()
    temp = get_cpu_temp()
    _temp_history.append({"t": int(time.time()), "v": temp})
    if len(_temp_history) > 1440:
        _temp_history.pop(0)
    return {"ok": True, "history": _temp_history[-720:], "current": temp}


@app.get("/api/bandwidth")
async def api_bandwidth():
    if DEMO_MODE:
        return demo_data.bandwidth()
    try:
        import psutil
        n1 = psutil.net_io_counters()
        await asyncio.sleep(1)
        n2 = psutil.net_io_counters()
        return {
            "ok": True,
            "rx_kb_s":     round((n2.bytes_recv - n1.bytes_recv) / 1024, 2),
            "tx_kb_s":     round((n2.bytes_sent - n1.bytes_sent) / 1024, 2),
            "total_rx_mb": round(n2.bytes_recv / 1024**2, 1),
            "total_tx_mb": round(n2.bytes_sent / 1024**2, 1),
        }
    except Exception as e:
        return {"ok": False, "error": str(e)}


@app.get("/api/healthchecks")
async def api_hc():
    if DEMO_MODE:
        return demo_data.healthchecks()
    import requests as rq
    if not HC_API_KEY or not HC_UUID:
        return {"ok": False, "error": "Healthchecks keys missing from .env"}
    try:
        h = {"X-Api-Key": HC_API_KEY}
        r = rq.get(f"https://healthchecks.io/api/v3/checks/{HC_UUID}", headers=h, timeout=8)
        if r.status_code != 200:
            return {"ok": False, "error": f"HTTP {r.status_code}"}
        c = r.json()
        r2 = rq.get(f"https://healthchecks.io/api/v3/checks/{HC_UUID}/flips/?seconds=172800", headers=h, timeout=8)
        flips = r2.json() if r2.status_code == 200 else []
        period = c.get("period") or c.get("timeout") or 43200
        grace  = c.get("grace") or 3600
        return {"ok": True, "name": c.get("name", "?"), "status": c.get("status", "unknown"),
                "last_ping": c.get("last_ping"), "next_ping": c.get("next_ping"),
                "n_pings": c.get("n_pings", 0), "period": period,
                "grace": grace, "flips": flips[-96:] if isinstance(flips, list) else []}
    except Exception as e:
        return {"ok": False, "error": str(e)}


@app.get("/api/network")
async def api_network():
    if DEMO_MODE:
        return demo_data.network()
    import subprocess, socket
    try:
        out = subprocess.check_output(["hostname", "-I"], stderr=subprocess.DEVNULL).decode().strip()
        parts = out.split()
        return {
            "local":     next((p for p in parts if p.startswith("192.168.")), parts[0] if parts else "?"),
            "tailscale": next((p for p in parts if p.startswith("100.")), None),
            "docker":    next((p for p in parts if p.startswith("172.")), None),
            "hostname":  socket.gethostname(), "all_ips": parts,
        }
    except Exception:
        return {"local": "?", "tailscale": None, "docker": None, "hostname": "?", "all_ips": []}


# ── WebSocket ─────────────────────────────────────────────────
class WsManager:
    def __init__(self): self.active: list[WebSocket] = []
    async def connect(self, ws):
        await ws.accept(); self.active.append(ws)
    def disconnect(self, ws):
        if ws in self.active: self.active.remove(ws)
    async def broadcast(self, data):
        payload = json.dumps(data, ensure_ascii=False)
        dead = []
        for ws in self.active:
            try: await ws.send_text(payload)
            except Exception: dead.append(ws)
        for ws in dead: self.disconnect(ws)


manager = WsManager()


@app.websocket("/ws")
async def ws_ep(ws: WebSocket):
    await manager.connect(ws)
    try:
        while True:
            await ws.receive_text()
    except WebSocketDisconnect:
        manager.disconnect(ws)


async def broadcast_loop():
    while True:
        try:
            if manager.active:
                await manager.broadcast(get_cached())
        except Exception as e:
            log.error(f"broadcast: {e}")
        await asyncio.sleep(REFRESH)


# ── Static files (with cache headers) ─────────────────────────
from starlette.staticfiles import StaticFiles as _SF
from starlette.types import Scope, Receive, Send


class CachedStatic(_SF):
    async def __call__(self, scope: Scope, receive: Receive, send: Send):
        async def cached_send(msg):
            if msg["type"] == "http.response.start":
                hdrs = dict(msg.get("headers", []))
                path = scope.get("path", "")
                hdrs[b"cache-control"] = b"public, max-age=3600" if path.endswith((".js", ".css")) else b"no-cache"
                msg["headers"] = list(hdrs.items())
            await send(msg)
        await super().__call__(scope, receive, cached_send)


if STATIC.exists():
    app.mount("/static", CachedStatic(directory=str(STATIC)), name="static")


if __name__ == "__main__":
    import uvicorn
    cert = os.getenv("SSL_CERT_FILE", "")
    key  = os.getenv("SSL_KEY_FILE", "")
    if cert and key and os.path.exists(cert) and os.path.exists(key):
        uvicorn.run("main:app", host="0.0.0.0", port=PORT, reload=False,
                    ssl_certfile=cert, ssl_keyfile=key)
    else:
        uvicorn.run("main:app", host="0.0.0.0", port=PORT, reload=False)
