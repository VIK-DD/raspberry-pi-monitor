#!/usr/bin/env python3
"""
monthly_report.py - Pi Guardian monthly report
Generates a PDF with all of the previous month's data and e-mails it.

Usage:
  python3 monthly_report.py          -- run for the previous month
  python3 monthly_report.py test     -- test with the current month
"""

import os, sys, sqlite3, smtplib, time, calendar
from datetime import datetime, date
from dateutil.relativedelta import relativedelta
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from email.mime.base import MIMEBase
from email import encoders
from dotenv import load_dotenv

# ReportLab
from reportlab.lib.pagesizes import A4
from reportlab.lib.units import mm
from reportlab.lib.colors import HexColor
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.enums import TA_CENTER, TA_LEFT, TA_RIGHT
from reportlab.platypus import (
    BaseDocTemplate, Frame, PageTemplate,
    Paragraph, Spacer, Table, TableStyle,
    HRFlowable, PageBreak, KeepTogether
)
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont

# ── Setup ──────────────────────────────────────────────────────────────────────
BASE = os.path.dirname(os.path.abspath(__file__))
load_dotenv(os.path.join(BASE, ".env"))

GMAIL_USER   = os.getenv("GMAIL_USER", "")
GMAIL_PASS   = os.getenv("GMAIL_APP_PASS", "")
EMAIL_TO     = os.getenv("EMAIL_TO", GMAIL_USER)
DEVICE_NAME  = os.getenv("DEVICE_NAME", "Pi Guardian")
DB_PATH      = os.path.join(BASE, "events.db")
REPORTS_DIR  = os.path.join(BASE, "reports")
os.makedirs(REPORTS_DIR, exist_ok=True)

# Register fonts
try:
    pdfmetrics.registerFont(TTFont('DVSans',      '/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf'))
    pdfmetrics.registerFont(TTFont('DVSans-Bold', '/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf'))
    pdfmetrics.registerFont(TTFont('DVMono',      '/usr/share/fonts/truetype/dejavu/DejaVuSansMono.ttf'))
    pdfmetrics.registerFont(TTFont('DVMono-Bold', '/usr/share/fonts/truetype/dejavu/DejaVuSansMono-Bold.ttf'))
    FONT  = 'DVSans'
    FONTB = 'DVSans-Bold'
    FONTM = 'DVMono'
except:
    FONT  = 'Helvetica'
    FONTB = 'Helvetica-Bold'
    FONTM = 'Courier'

# ── Colors ─────────────────────────────────────────────────────────────────────
DARK    = HexColor('#07090f')
BG2     = HexColor('#0d1018')
BG3     = HexColor('#131720')
ACCENT  = HexColor('#4fc3f7')
ACCENT2 = HexColor('#8b7cf8')
GREEN   = HexColor('#34d399')
RED     = HexColor('#f87171')
YELLOW  = HexColor('#fbbf24')
MUTED   = HexColor('#6b7591')
TEXT    = HexColor('#eceef5')
LIGHT   = HexColor('#c0c8d8')
WHITE   = HexColor('#ffffff')

# ── Styles ─────────────────────────────────────────────────────────────────────
def S(name, font=None, size=10, color=LIGHT, **kw):
    return ParagraphStyle(name, fontName=font or FONT, fontSize=size, textColor=color, **kw)

S_TITLE  = S('t',  FONTB, 24, WHITE,  alignment=TA_CENTER, spaceAfter=4, leading=30)
S_SUB    = S('s',  FONT,  11, MUTED,  alignment=TA_CENTER, spaceAfter=4)
S_H1     = S('h1', FONTB, 15, ACCENT, spaceBefore=12, spaceAfter=6, leading=19)
S_H2     = S('h2', FONTB, 11, TEXT,   spaceBefore=8,  spaceAfter=4, leading=14)
S_BODY   = S('b',  FONT,  9,  LIGHT,  spaceAfter=4,   leading=13)
S_CODE   = S('c',  FONTM, 8,  ACCENT, spaceAfter=3,   leading=12,
              backColor=BG3, leftIndent=6, rightIndent=6, spaceBefore=3)
S_CENTER = S('cn', FONT,  8,  MUTED,  alignment=TA_CENTER)
S_SMALL  = S('sm', FONT,  8,  MUTED,  spaceAfter=2,   leading=11)

def tk(t): return Paragraph(t, S('_k', FONTB, 9, TEXT))
def tv(t): return Paragraph(t, S('_v', FONT,  9, LIGHT))
def tg(t): return Paragraph(t, S('_g', FONTB, 9, GREEN))
def tr(t): return Paragraph(t, S('_r', FONTB, 9, RED))
def ty(t): return Paragraph(t, S('_y', FONTB, 9, YELLOW))

# ── Document Template ──────────────────────────────────────────────────────────
class DarkDoc(BaseDocTemplate):
    def __init__(self, fn, month_str, **kw):
        super().__init__(fn, **kw)
        self.month_str = month_str
        frame = Frame(self.leftMargin, self.bottomMargin, self.width, self.height, id='n')
        self.addPageTemplates([PageTemplate(id='m', frames=frame, onPage=self.bg)])

    def bg(self, canvas, doc):
        canvas.saveState()
        # Background
        canvas.setFillColor(DARK)
        canvas.rect(0, 0, A4[0], A4[1], fill=1, stroke=0)
        # Top bar
        canvas.setFillColor(BG2)
        canvas.rect(0, A4[1]-11*mm, A4[0], 11*mm, fill=1, stroke=0)
        canvas.setFillColor(ACCENT)
        canvas.rect(0, A4[1]-11*mm, A4[0], 0.5*mm, fill=1, stroke=0)
        # Top bar text
        canvas.setFillColor(MUTED)
        canvas.setFont(FONT, 7.5)
        canvas.drawString(18*mm, A4[1]-7*mm, f'{DEVICE_NAME} — Monthly Report {self.month_str}')
        canvas.setFillColor(ACCENT)
        canvas.drawRightString(A4[0]-18*mm, A4[1]-7*mm, 'Pi Guardian')
        # Bottom bar
        canvas.setFillColor(BG2)
        canvas.rect(0, 0, A4[0], 9*mm, fill=1, stroke=0)
        canvas.setFillColor(HexColor('#1a2030'))
        canvas.rect(0, 9*mm, A4[0], 0.3*mm, fill=1, stroke=0)
        canvas.setFillColor(MUTED)
        canvas.setFont(FONT, 7.5)
        canvas.drawString(18*mm, 3*mm, f'Generated automatically on {datetime.now().strftime("%d.%m.%Y %H:%M")}')
        canvas.drawRightString(A4[0]-18*mm, 3*mm, f'Page {doc.page}')
        canvas.restoreState()

# ── Helpers ────────────────────────────────────────────────────────────────────
def section(title):
    return [
        Spacer(1, 6),
        HRFlowable(width='100%', thickness=0.4, color=HexColor('#1a2030')),
        Spacer(1, 4),
        Paragraph(title, S_H1),
        HRFlowable(width='100%', thickness=1.5, color=ACCENT, spaceAfter=8),
    ]

def info_table(rows, cw=[55*mm, 110*mm]):
    data = [[tk(r[0]), tv(r[1])] for r in rows]
    t = Table(data, colWidths=cw)
    t.setStyle(TableStyle([
        ('ROWBACKGROUNDS', (0,0), (-1,-1), [BG2, BG3]),
        ('GRID', (0,0), (-1,-1), 0.4, HexColor('#1a2030')),
        ('TOPPADDING',    (0,0), (-1,-1), 6),
        ('BOTTOMPADDING', (0,0), (-1,-1), 6),
        ('LEFTPADDING',   (0,0), (-1,-1), 10),
        ('RIGHTPADDING',  (0,0), (-1,-1), 10),
        ('VALIGN',        (0,0), (-1,-1), 'TOP'),
    ]))
    return t

def stat_box(label, value, color=ACCENT, sub=''):
    inner = [
        [Paragraph(label, S('sl', FONT, 8, MUTED, letterSpacing=0.5))],
        [Paragraph(str(value), S('sv', FONTB, 20, color, leading=24))],
    ]
    if sub:
        inner.append([Paragraph(sub, S('ss', FONT, 8, MUTED))])
    t = Table(inner, colWidths=[55*mm])
    t.setStyle(TableStyle([
        ('BACKGROUND',    (0,0), (-1,-1), BG2),
        ('BOX',           (0,0), (-1,-1), 0.5, HexColor('#1a2030')),
        ('TOPPADDING',    (0,0), (-1,-1), 10),
        ('BOTTOMPADDING', (0,0), (-1,-1), 10),
        ('LEFTPADDING',   (0,0), (-1,-1), 12),
        ('ALIGN',         (0,0), (-1,-1), 'LEFT'),
    ]))
    return t

def event_table(events):
    """Table for events list"""
    header = [
        Paragraph('Data', S('eh', FONTB, 8, TEXT)),
        Paragraph('Nivel', S('eh', FONTB, 8, TEXT)),
        Paragraph('Mesaj', S('eh', FONTB, 8, TEXT)),
    ]
    rows = [header]
    for ev in events:
        ts = datetime.fromtimestamp(ev['ts']).strftime('%d.%m %H:%M')
        lvl = ev['level'].upper()
        if ev['level'] == 'critical':
            lvl_p = Paragraph(lvl, S('_', FONTB, 8, RED))
        elif ev['level'] == 'warning':
            lvl_p = Paragraph(lvl, S('_', FONTB, 8, YELLOW))
        else:
            lvl_p = Paragraph(lvl, S('_', FONTB, 8, ACCENT))
        rows.append([
            Paragraph(ts, S('_', FONTM, 8, MUTED)),
            lvl_p,
            Paragraph(ev['msg'][:80], S('_', FONT, 8, LIGHT)),
        ])
    t = Table(rows, colWidths=[28*mm, 20*mm, 117*mm])
    t.setStyle(TableStyle([
        ('BACKGROUND',    (0,0), (-1,0),  ACCENT2),
        ('TEXTCOLOR',     (0,0), (-1,0),  WHITE),
        ('FONTNAME',      (0,0), (-1,0),  FONTB),
        ('ROWBACKGROUNDS',(0,1), (-1,-1), [BG2, BG3]),
        ('GRID',          (0,0), (-1,-1), 0.4, HexColor('#1a2030')),
        ('TOPPADDING',    (0,0), (-1,-1), 5),
        ('BOTTOMPADDING', (0,0), (-1,-1), 5),
        ('LEFTPADDING',   (0,0), (-1,-1), 6),
        ('VALIGN',        (0,0), (-1,-1), 'TOP'),
    ]))
    return t

def bar_chart_ascii(data, max_val, width=30):
    """Simple text-based bar for PDF"""
    if max_val == 0: max_val = 1
    filled = int((data / max_val) * width)
    return '█' * filled + '░' * (width - filled)

# ── Data Collection ────────────────────────────────────────────────────────────
def get_month_range(test_mode=False):
    today = date.today()
    if test_mode:
        # Current month for testing
        start = date(today.year, today.month, 1)
        end = today
    else:
        # Previous month
        first_of_this_month = date(today.year, today.month, 1)
        last_month = first_of_this_month - relativedelta(months=1)
        start = date(last_month.year, last_month.month, 1)
        last_day = calendar.monthrange(last_month.year, last_month.month)[1]
        end = date(last_month.year, last_month.month, last_day)
    return start, end

def fetch_events(start_date, end_date):
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    ts_start = datetime(start_date.year, start_date.month, start_date.day).timestamp()
    ts_end   = datetime(end_date.year, end_date.month, end_date.day, 23, 59, 59).timestamp()
    rows = conn.execute(
        "SELECT ts, msg, level, ip, user FROM events WHERE ts >= ? AND ts <= ? ORDER BY ts DESC",
        (ts_start, ts_end)
    ).fetchall()
    conn.close()
    return [dict(r) for r in rows]

def fetch_users():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    rows = conn.execute("SELECT username, email, created FROM users WHERE verified=1 ORDER BY created").fetchall()
    conn.close()
    return [dict(r) for r in rows]

def analyze_events(events):
    total   = len(events)
    info    = [e for e in events if e['level'] == 'info']
    warning = [e for e in events if e['level'] == 'warning']
    critical= [e for e in events if e['level'] == 'critical']
    logins  = [e for e in events if 'Login' in e['msg'] and e['level'] == 'info']
    restarts= [e for e in events if 'restartat' in e['msg'].lower() or 'pornit' in e['msg'].lower()]

    # Count by day
    days = {}
    for e in events:
        day = datetime.fromtimestamp(e['ts']).strftime('%d')
        days[day] = days.get(day, 0) + 1

    # Most frequent messages
    msg_count = {}
    for e in events:
        msg = e['msg'][:50]
        msg_count[msg] = msg_count.get(msg, 0) + 1
    top_msgs = sorted(msg_count.items(), key=lambda x: x[1], reverse=True)[:10]

    return {
        'total': total,
        'info': info,
        'warning': warning,
        'critical': critical,
        'logins': logins,
        'restarts': restarts,
        'days': days,
        'top_msgs': top_msgs,
    }

def get_adguard_stats():
    """Try to get AdGuard stats from API"""
    try:
        import requests
        agh_host = os.getenv("AGH_HOST", "http://127.0.0.1")
        agh_user = os.getenv("AGH_USER", "adguard")
        agh_pass = os.getenv("AGH_PASS", "")
        auth = (agh_user, agh_pass)
        s = requests.get(f"{agh_host.rstrip('/')}/control/stats", auth=auth, timeout=6).json()
        return {
            'ok': True,
            'queries':       s.get('num_dns_queries', 0),
            'blocked':       s.get('num_blocked_filtering', 0),
            'avg_ms':        round(s.get('avg_processing_time', 0) * 1000, 2),
            'top_blocked':   s.get('top_blocked_domains', [])[:10],
            'top_clients':   s.get('top_clients', [])[:5],
        }
    except Exception as e:
        return {'ok': False, 'error': str(e)}

def get_system_info():
    """Get current system info"""
    try:
        import psutil
        cpu_temp = 0.0
        try:
            out = __import__('subprocess').check_output(
                ["vcgencmd", "measure_temp"], stderr=__import__('subprocess').DEVNULL).decode()
            cpu_temp = float(out.strip().replace("temp=","").replace("'C",""))
        except:
            try:
                cpu_temp = round(int(open("/sys/class/thermal/thermal_zone0/temp").read().strip()) / 1000, 1)
            except: pass

        ram  = psutil.virtual_memory()
        disk = psutil.disk_usage("/")
        up_s = time.time() - psutil.boot_time()
        d = int(up_s//86400); h = int((up_s%86400)//3600); m = int((up_s%3600)//60)

        return {
            'ok': True,
            'cpu_temp':   cpu_temp,
            'cpu_percent':psutil.cpu_percent(interval=0.5),
            'ram_percent':round(ram.percent, 1),
            'ram_used':   round(ram.used/1024**2, 1),
            'ram_total':  round(ram.total/1024**2, 1),
            'disk_percent':round(disk.percent, 1),
            'disk_used':  round(disk.used/1024**3, 2),
            'disk_total': round(disk.total/1024**3, 2),
            'uptime':     f"{d}z {h}h {m}m",
        }
    except Exception as e:
        return {'ok': False, 'error': str(e)}

# ── PDF Generation ─────────────────────────────────────────────────────────────
def generate_pdf(start_date, end_date, events, users, agh, sys_info):
    month_name = start_date.strftime('%B %Y').capitalize()
    month_str  = start_date.strftime('%m.%Y')
    fn = os.path.join(REPORTS_DIR, f"pi_guardian_raport_{start_date.strftime('%Y_%m')}.pdf")

    doc = DarkDoc(fn, month_str, pagesize=A4,
        leftMargin=18*mm, rightMargin=18*mm,
        topMargin=16*mm,  bottomMargin=16*mm)

    story = []
    analysis = analyze_events(events)

    # ── COVER ──────────────────────────────────────────────────────────────────
    story.append(Spacer(1, 22*mm))

    # Logo box
    logo_t = Table([[Paragraph('🛡', S('lg', FONT, 44, ACCENT, alignment=TA_CENTER))]],
        colWidths=[170*mm])
    logo_t.setStyle(TableStyle([
        ('BACKGROUND',    (0,0), (-1,-1), BG2),
        ('BOX',           (0,0), (-1,-1), 1.5, ACCENT),
        ('TOPPADDING',    (0,0), (-1,-1), 14),
        ('BOTTOMPADDING', (0,0), (-1,-1), 14),
        ('ALIGN',         (0,0), (-1,-1), 'CENTER'),
    ]))
    story.append(logo_t)
    story.append(Spacer(1, 8*mm))
    story.append(Paragraph(DEVICE_NAME, S_TITLE))
    story.append(Paragraph('Monthly Activity Report', S_SUB))
    story.append(Spacer(1, 3))
    story.append(Paragraph(f'Period: {start_date.strftime("%d.%m.%Y")} — {end_date.strftime("%d.%m.%Y")}',
        S('p', FONTB, 11, ACCENT, alignment=TA_CENTER)))
    story.append(Spacer(1, 8*mm))

    # Cover stats grid
    c_info = [
        ['Period', f'{start_date.strftime("%d.%m.%Y")} - {end_date.strftime("%d.%m.%Y")}'],
        ['Total Events', str(analysis['total'])],
        ['Warnings',       str(len(analysis['warning']))],
        ['Critical',          str(len(analysis['critical']))],
        ['Logins',        str(len(analysis['logins']))],
        ['Active users', str(len(users))],
    ]
    story.append(info_table(c_info))
    story.append(PageBreak())

    # ── SUMAR EXECUTIV ─────────────────────────────────────────────────────────
    story += section('Sumar Executiv')

    # Stat boxes row
    color_total = ACCENT
    color_warn  = YELLOW if len(analysis['warning']) > 0 else GREEN
    color_crit  = RED    if len(analysis['critical']) > 0 else GREEN

    boxes = [
        stat_box('TOTAL EVENTS', analysis['total'], ACCENT),
        stat_box('WARNINGS', len(analysis['warning']), color_warn),
        stat_box('CRITICAL',    len(analysis['critical']),color_crit),
    ]
    box_table = Table([boxes], colWidths=[58*mm, 58*mm, 58*mm])
    box_table.setStyle(TableStyle([
        ('ALIGN',   (0,0), (-1,-1), 'CENTER'),
        ('VALIGN',  (0,0), (-1,-1), 'TOP'),
        ('LEFTPADDING',  (0,0), (-1,-1), 2),
        ('RIGHTPADDING', (0,0), (-1,-1), 2),
    ]))
    story.append(box_table)
    story.append(Spacer(1, 8))

    boxes2 = [
        stat_box('LOGINS', len(analysis['logins']), ACCENT2),
        stat_box('RESTART-URI', len(analysis['restarts']), YELLOW),
        stat_box('USERS', len(users), GREEN),
    ]
    box_table2 = Table([boxes2], colWidths=[58*mm, 58*mm, 58*mm])
    box_table2.setStyle(TableStyle([
        ('ALIGN',   (0,0), (-1,-1), 'CENTER'),
        ('VALIGN',  (0,0), (-1,-1), 'TOP'),
        ('LEFTPADDING',  (0,0), (-1,-1), 2),
        ('RIGHTPADDING', (0,0), (-1,-1), 2),
    ]))
    story.append(box_table2)
    story.append(Spacer(1, 10))

    # Status general
    if len(analysis['critical']) == 0 and len(analysis['warning']) < 5:
        status_color = GREEN
        status_text = 'EXCELLENT MONTH - No critical issues detected'
    elif len(analysis['critical']) < 3:
        status_color = YELLOW
        status_text = f'GOOD MONTH - {len(analysis["critical"])} critical issues detected'
    else:
        status_color = RED
        status_text = f'WARNING - {len(analysis["critical"])} critical issues this month'

    status_t = Table([[Paragraph(status_text, S('st', FONTB, 10, status_color, alignment=TA_CENTER))]],
        colWidths=[174*mm])
    status_t.setStyle(TableStyle([
        ('BACKGROUND',    (0,0), (-1,-1), BG2),
        ('BOX',           (0,0), (-1,-1), 1.5, status_color),
        ('TOPPADDING',    (0,0), (-1,-1), 10),
        ('BOTTOMPADDING', (0,0), (-1,-1), 10),
        ('ALIGN',         (0,0), (-1,-1), 'CENTER'),
    ]))
    story.append(status_t)

    # ── SISTEM ─────────────────────────────────────────────────────────────────
    story += section('Current System Status')

    if sys_info.get('ok'):
        sys_rows = [
            ['CPU Temperature',    f"{sys_info['cpu_temp']}°C"],
            ['CPU Usage',          f"{sys_info['cpu_percent']}%"],
            ['RAM Utilizata',      f"{sys_info['ram_used']} / {sys_info['ram_total']} MB ({sys_info['ram_percent']}%)"],
            ['Disk Utilizat',      f"{sys_info['disk_used']} / {sys_info['disk_total']} GB ({sys_info['disk_percent']}%)"],
            ['Uptime curent',      sys_info['uptime']],
        ]
        story.append(info_table(sys_rows))
    else:
        story.append(Paragraph('System data could not be collected.', S_BODY))

    # ── ADGUARD ────────────────────────────────────────────────────────────────
    story += section('AdGuard Home — Statistici')

    if agh.get('ok'):
        blocked_pct = round(agh['blocked'] / max(agh['queries'], 1) * 100, 1)
        agh_rows = [
            ['Total Queries (24h)',    f"{agh['queries']:,}"],
            ['Blocked',                f"{agh['blocked']:,} ({blocked_pct}%)"],
            ['Timp mediu procesare',   f"{agh['avg_ms']} ms"],
        ]
        story.append(info_table(agh_rows))
        story.append(Spacer(1, 6))

        if agh.get('top_blocked'):
            story.append(Paragraph('Top Blocked Domains (24h)', S_H2))
            top_data = [
                [tk('Domeniu'), tk('Blocari')]
            ]
            for item in agh['top_blocked']:
                if isinstance(item, dict):
                    domain, count = list(item.items())[0]
                else:
                    domain, count = item, '-'
                top_data.append([tv(str(domain)), tv(str(count))])

            top_t = Table(top_data, colWidths=[140*mm, 34*mm])
            top_t.setStyle(TableStyle([
                ('BACKGROUND',    (0,0), (-1,0),  ACCENT2),
                ('TEXTCOLOR',     (0,0), (-1,0),  WHITE),
                ('ROWBACKGROUNDS',(0,1), (-1,-1), [BG2, BG3]),
                ('GRID',          (0,0), (-1,-1), 0.4, HexColor('#1a2030')),
                ('TOPPADDING',    (0,0), (-1,-1), 5),
                ('BOTTOMPADDING', (0,0), (-1,-1), 5),
                ('LEFTPADDING',   (0,0), (-1,-1), 8),
                ('ALIGN',         (-1,0),(-1,-1), 'CENTER'),
            ]))
            story.append(top_t)
    else:
        story.append(Paragraph(f"AdGuard offline: {agh.get('error', '?')}", S_BODY))

    story.append(PageBreak())

    # ── EVENIMENTE ─────────────────────────────────────────────────────────────
    story += section('Analiza Events')

    # Events by level breakdown
    level_data = [
        [tk('Nivel'), tk('Numar'), tk('Procent')],
        [tv('Info'),     tv(str(len(analysis['info']))),
         tv(f"{round(len(analysis['info'])/max(analysis['total'],1)*100, 1)}%")],
        [ty('Warning'),  ty(str(len(analysis['warning']))),
         ty(f"{round(len(analysis['warning'])/max(analysis['total'],1)*100, 1)}%")],
        [tr('Critical'), tr(str(len(analysis['critical']))),
         tr(f"{round(len(analysis['critical'])/max(analysis['total'],1)*100, 1)}%")],
        [Paragraph('<b>TOTAL</b>', S('_', FONTB, 9, ACCENT)),
         Paragraph(f'<b>{analysis["total"]}</b>', S('_', FONTB, 9, ACCENT)),
         Paragraph('<b>100%</b>', S('_', FONTB, 9, ACCENT))],
    ]
    level_t = Table(level_data, colWidths=[60*mm, 57*mm, 57*mm])
    level_t.setStyle(TableStyle([
        ('BACKGROUND',    (0,0), (-1,0),  HexColor('#1a2030')),
        ('ROWBACKGROUNDS',(0,1), (-1,-2), [BG2, BG3]),
        ('BACKGROUND',    (0,-1),(-1,-1), BG3),
        ('GRID',          (0,0), (-1,-1), 0.4, HexColor('#1a2030')),
        ('TOPPADDING',    (0,0), (-1,-1), 6),
        ('BOTTOMPADDING', (0,0), (-1,-1), 6),
        ('LEFTPADDING',   (0,0), (-1,-1), 10),
        ('ALIGN',         (1,0), (2,-1),  'CENTER'),
    ]))
    story.append(level_t)
    story.append(Spacer(1, 8))

    # Top messages
    if analysis['top_msgs']:
        story.append(Paragraph('Most Frequent Events', S_H2))
        top_ev_data = [[tk('Event'), tk('Occurrences')]]
        for msg, count in analysis['top_msgs']:
            top_ev_data.append([tv(msg), tv(str(count))])
        top_ev_t = Table(top_ev_data, colWidths=[148*mm, 26*mm])
        top_ev_t.setStyle(TableStyle([
            ('BACKGROUND',    (0,0), (-1,0),  ACCENT2),
            ('TEXTCOLOR',     (0,0), (-1,0),  WHITE),
            ('ROWBACKGROUNDS',(0,1), (-1,-1), [BG2, BG3]),
            ('GRID',          (0,0), (-1,-1), 0.4, HexColor('#1a2030')),
            ('TOPPADDING',    (0,0), (-1,-1), 5),
            ('BOTTOMPADDING', (0,0), (-1,-1), 5),
            ('LEFTPADDING',   (0,0), (-1,-1), 8),
            ('ALIGN',         (-1,0),(-1,-1), 'CENTER'),
        ]))
        story.append(top_ev_t)

    # ── EVENIMENTE CRITICAL ─────────────────────────────────────────────────────
    if analysis['critical']:
        story.append(PageBreak())
        story += section('Critical Events')
        story.append(Paragraph(
            f"Detected {len(analysis['critical'])} critical events this month:",
            S_BODY))
        story.append(Spacer(1, 4))
        story.append(event_table(analysis['critical']))

    # ── WARNINGS ─────────────────────────────────────────────────────────────
    if analysis['warning']:
        story.append(Spacer(1, 8))
        story += section('Warnings')
        story.append(Paragraph(
            f"Detected {len(analysis['warning'])} warnings this month:",
            S_BODY))
        story.append(Spacer(1, 4))
        # Show max 50 warnings
        show_warnings = analysis['warning'][:50]
        story.append(event_table(show_warnings))
        if len(analysis['warning']) > 50:
            story.append(Paragraph(
                f"... and {len(analysis['warning'])-50} more warnings (first 50 shown).",
                S_SMALL))

    story.append(PageBreak())

    # ── LOGINS ──────────────────────────────────────────────────────────────
    story += section('Login Activity')

    if analysis['logins']:
        login_data = [[tk('Data & Ora'), tk('Utilizator'), tk('IP')]]
        for ev in analysis['logins'][:30]:
            ts = datetime.fromtimestamp(ev['ts']).strftime('%d.%m.%Y %H:%M')
            user = ev.get('user', '') or ev['msg'].replace('Login: ', '').strip()
            ip   = ev.get('ip', '-') or '-'
            login_data.append([
                Paragraph(ts,   S('_', FONTM, 8, MUTED)),
                Paragraph(user, S('_', FONT,  8, ACCENT)),
                Paragraph(ip,   S('_', FONTM, 8, LIGHT)),
            ])
        login_t = Table(login_data, colWidths=[45*mm, 60*mm, 69*mm])
        login_t.setStyle(TableStyle([
            ('BACKGROUND',    (0,0), (-1,0),  ACCENT2),
            ('TEXTCOLOR',     (0,0), (-1,0),  WHITE),
            ('ROWBACKGROUNDS',(0,1), (-1,-1), [BG2, BG3]),
            ('GRID',          (0,0), (-1,-1), 0.4, HexColor('#1a2030')),
            ('TOPPADDING',    (0,0), (-1,-1), 5),
            ('BOTTOMPADDING', (0,0), (-1,-1), 5),
            ('LEFTPADDING',   (0,0), (-1,-1), 8),
        ]))
        story.append(login_t)
        if len(analysis['logins']) > 30:
            story.append(Paragraph(
                f"... and {len(analysis['logins'])-30} more logins (first 30 shown).",
                S_SMALL))
    else:
        story.append(Paragraph('No logins were recorded in this period.', S_BODY))

    # ── USERS ────────────────────────────────────────────────────────────
    story += section('Registered Users')

    if users:
        user_data = [[tk('Username'), tk('Email'), tk('Data Creare')]]
        for u in users:
            created = datetime.fromtimestamp(u['created']).strftime('%d.%m.%Y') if u['created'] else '-'
            user_data.append([
                Paragraph(u['username'], S('_', FONTB, 8, ACCENT)),
                Paragraph(u['email'],    S('_', FONT,  8, LIGHT)),
                Paragraph(created,       S('_', FONTM, 8, MUTED)),
            ])
        user_t = Table(user_data, colWidths=[45*mm, 90*mm, 39*mm])
        user_t.setStyle(TableStyle([
            ('BACKGROUND',    (0,0), (-1,0),  ACCENT2),
            ('TEXTCOLOR',     (0,0), (-1,0),  WHITE),
            ('ROWBACKGROUNDS',(0,1), (-1,-1), [BG2, BG3]),
            ('GRID',          (0,0), (-1,-1), 0.4, HexColor('#1a2030')),
            ('TOPPADDING',    (0,0), (-1,-1), 5),
            ('BOTTOMPADDING', (0,0), (-1,-1), 5),
            ('LEFTPADDING',   (0,0), (-1,-1), 8),
        ]))
        story.append(user_t)
    else:
        story.append(Paragraph('No registered users.', S_BODY))

    # ── FOOTER ─────────────────────────────────────────────────────────────────
    story.append(Spacer(1, 10))
    footer_t = Table([[Paragraph(
        f'Report generated automatically by {DEVICE_NAME} · {datetime.now().strftime("%d.%m.%Y %H:%M")} · Pi Guardian',
        S('ft', FONT, 8, MUTED, alignment=TA_CENTER)
    )]], colWidths=[174*mm])
    footer_t.setStyle(TableStyle([
        ('BACKGROUND',    (0,0), (-1,-1), BG2),
        ('BOX',           (0,0), (-1,-1), 0.5, HexColor('#1a2030')),
        ('TOPPADDING',    (0,0), (-1,-1), 8),
        ('BOTTOMPADDING', (0,0), (-1,-1), 8),
    ]))
    story.append(footer_t)

    doc.build(story)
    return fn

# ── Email ──────────────────────────────────────────────────────────────────────
def send_email_with_pdf(pdf_path, start_date, end_date):
    if not GMAIL_USER or not GMAIL_PASS:
        print("Email neconfigurat, skip.")
        return False

    month_str = start_date.strftime('%B %Y')
    subject   = f"[{DEVICE_NAME}] Monthly Report — {month_str}"

    msg = MIMEMultipart()
    msg['Subject'] = subject
    msg['From']    = GMAIL_USER
    msg['To']      = EMAIL_TO

    html_body = f"""
<!DOCTYPE html>
<html><head><meta charset="UTF-8"></head>
<body style="margin:0;padding:0;background:#07090f;font-family:Arial,sans-serif">
<table width="100%" cellpadding="0" cellspacing="0" style="background:#07090f;padding:40px 20px">
  <tr><td align="center">
    <table width="520" cellpadding="0" cellspacing="0" style="background:#0d1018;border-radius:18px;border:1px solid rgba(255,255,255,.07);overflow:hidden">
      <tr><td style="background:linear-gradient(135deg,#0d1018,#131720);padding:28px 32px;border-bottom:1px solid rgba(255,255,255,.07)">
        <table cellpadding="0" cellspacing="0"><tr>
          <td style="background:linear-gradient(135deg,#4fc3f7,#8b7cf8);border-radius:12px;width:44px;height:44px;text-align:center;vertical-align:middle;font-size:22px">🛡</td>
          <td style="padding-left:14px">
            <div style="color:#eceef5;font-size:18px;font-weight:800">{DEVICE_NAME}</div>
            <div style="color:#6b7591;font-size:12px;margin-top:2px">Automated Monthly Report</div>
          </td>
        </tr></table>
      </td></tr>
      <tr><td style="padding:28px 32px">
        <div style="text-align:center;margin-bottom:20px">
          <div style="color:#eceef5;font-size:20px;font-weight:800;margin-bottom:8px">Report {month_str}</div>
          <div style="color:#6b7591;font-size:13px">{start_date.strftime("%d.%m.%Y")} — {end_date.strftime("%d.%m.%Y")}</div>
        </div>
        <div style="background:rgba(79,195,247,.06);border:1px solid rgba(79,195,247,.2);border-radius:12px;padding:16px 20px;margin-bottom:20px">
          <div style="color:#6b7591;font-size:12px;margin-bottom:8px">Reportul PDF este atasat la acest email si contine:</div>
          <div style="color:#eceef5;font-size:13px;line-height:1.8">
            ✅ Sumar executiv cu toate statisticile<br>
            ✅ System status (CPU, RAM, Disk, Temperature)<br>
            ✅ Statistici AdGuard Home<br>
            ✅ All critical events and warnings<br>
            ✅ Logins and user activity<br>
            ✅ List of registered users
          </div>
        </div>
      </td></tr>
      <tr><td style="padding:16px 32px;border-top:1px solid rgba(255,255,255,.05);text-align:center">
        <div style="color:#6b7591;font-size:11px">{DEVICE_NAME} · Raspberry Pi Zero 2W · Automated report</div>
      </td></tr>
    </table>
  </td></tr>
</table>
</body></html>"""

    msg.attach(MIMEText(html_body, 'html', 'utf-8'))

    # Attach PDF
    with open(pdf_path, 'rb') as f:
        part = MIMEBase('application', 'pdf')
        part.set_payload(f.read())
        encoders.encode_base64(part)
        pdf_name = os.path.basename(pdf_path)
        part.add_header('Content-Disposition', f'attachment; filename="{pdf_name}"')
        msg.attach(part)

    try:
        with smtplib.SMTP('smtp.gmail.com', 587) as s:
            s.ehlo(); s.starttls(); s.ehlo()
            s.login(GMAIL_USER, GMAIL_PASS)
            s.sendmail(GMAIL_USER, EMAIL_TO, msg.as_string())
        print(f"Email trimis la {EMAIL_TO}")
        return True
    except Exception as e:
        print(f"Eroare email: {e}")
        return False

# ── Main ───────────────────────────────────────────────────────────────────────
def main():
    test_mode = len(sys.argv) > 1 and sys.argv[1] == 'test'

    start_date, end_date = get_month_range(test_mode)

    mode_str = "TEST (current month)" if test_mode else "previous month"
    print(f"Generating report for {mode_str}: {start_date} - {end_date}")

    print("Collecting events from DB...")
    events   = fetch_events(start_date, end_date)
    print(f"  → {len(events)} events found")

    print("Collecting users...")
    users    = fetch_users()
    print(f"  → {len(users)} users")

    print("Collecting AdGuard data...")
    agh      = get_adguard_stats()
    print(f"  → AdGuard: {'OK' if agh['ok'] else 'OFFLINE'}")

    print("Collecting system data...")
    sys_info = get_system_info()

    print("Generating PDF...")
    pdf_path = generate_pdf(start_date, end_date, events, users, agh, sys_info)
    print(f"  → PDF salvat: {pdf_path}")

    print("Trimit email...")
    send_email_with_pdf(pdf_path, start_date, end_date)

    print("Gata!")

if __name__ == '__main__':
    main()
