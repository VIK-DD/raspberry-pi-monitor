/* nav.js v5 — Pi Guardian */

// Fix viewport
const _vp = document.querySelector('meta[name="viewport"]');
if (_vp) _vp.content = 'width=device-width, initial-scale=1.0, minimum-scale=1.0';

const NAV_PAGES = [
  { label:"Dashboard",    icon:"💻", color:"#4fc3f7", href:"/",             id:"dashboard"    },
  { label:"AdGuard",      icon:"🔰", color:"#34d399", href:"/adguard",      id:"adguard"      },
  { label:"Healthchecks", icon:"💗", color:"#f472b6", href:"/healthchecks", id:"healthchecks" },
  { label:"Network",        icon:"🌐", color:"#60a5fa", href:"/network",      id:"network"      },
  { label:"Alerts",       icon:"🔔", color:"#fbbf24", href:"/alerts",       id:"alerts"       },
  { label:"System",       icon:"⚙️", color:"#f87171", href:"/system",       id:"system"       },
  { label:"Settings",       icon:"🔧", color:"#94a3b8", href:"/settings",     id:"settings"     },
];

const NAV_CSS = `
@import url('https://fonts.googleapis.com/css2?family=JetBrains+Mono:wght@400;500;600&family=Syne:wght@600;700;800&display=swap');

#main-nav {
  position: sticky; top: 0; z-index: 100;
  background: var(--bg2);
  border-bottom: 1px solid var(--border);
  backdrop-filter: blur(24px); -webkit-backdrop-filter: blur(24px);
}
[data-theme="dark"] #main-nav { background: rgba(13,16,24,.95); }
[data-theme="light"] #main-nav { background: rgba(255,255,255,.95); }

.nav-top {
  max-width: 1400px; margin: 0 auto; padding: 0 32px;
  display: grid; grid-template-columns: 1fr auto 1fr;
  align-items: center; height: 68px;
}
.nav-brand { display: flex; align-items: center; gap: 10px; text-decoration: none; transition: opacity .2s; }
.nav-brand:hover { opacity: .85; }
.nav-logo {
  width: 40px; height: 40px; border-radius: 11px;
  background: linear-gradient(135deg, var(--accent), var(--accent2));
  display: flex; align-items: center; justify-content: center;
  font-size: 20px; flex-shrink: 0; box-shadow: 0 0 20px rgba(79,195,247,.2);
}
.nav-brand-text { display: flex; flex-direction: column; line-height: 1.25; }
.nav-title { font-family: 'Syne', sans-serif; font-size: 15px; font-weight: 800; color: var(--text); }
.nav-sub   { font-family: 'JetBrains Mono', monospace; font-size: 9px; color: var(--muted); letter-spacing: .5px; text-transform: uppercase; }

.nav-links { display: flex; align-items: center; justify-content: center; gap: 2px; transform: translateX(25px); }
.nav-link {
  display: flex; align-items: center; gap: 5px; padding: 6px 9px; border-radius: 9px;
  font-family: 'Syne', sans-serif; font-size: 12px; font-weight: 700;
  color: var(--muted); text-decoration: none; transition: all .2s;
  position: relative; white-space: nowrap; flex-shrink: 0;
}
.nav-link:hover { background: var(--bg3); color: var(--text2); }
.nav-link.active { background: var(--bg3); }
.nav-link.active .nl-label { color: var(--nl-color, var(--accent)); }
.nav-link.active::after {
  content: ''; position: absolute; bottom: -1px; left: 10px; right: 10px;
  height: 2.5px; background: var(--nl-color, var(--accent)); border-radius: 2px 2px 0 0;
}
.nl-icon { font-size: 15px; flex-shrink: 0; }
.nav-alert-dot {
  position: absolute; top: 7px; right: 7px; width: 7px; height: 7px; border-radius: 50%;
  background: var(--red); box-shadow: 0 0 7px var(--red); animation: nadot 1.5s infinite; display: none;
}
@keyframes nadot { 0%,100%{opacity:1} 50%{opacity:.4} }

.nav-right { display: flex; align-items: center; justify-content: flex-end; gap: 5px; }
.nav-ws {
  display: flex; align-items: center; gap: 5px; padding: 4px 9px; border-radius: 999px;
  border: 1px solid var(--border); background: var(--bg3);
  font-family: 'JetBrains Mono', monospace; font-size: 10px; color: var(--muted);
  max-width: 72px; overflow: hidden; flex-shrink: 0; transition: all .3s;
}
.nav-ws.on  { border-color: rgba(52,211,153,.35); color: var(--green); }
.nav-ws.off { border-color: rgba(248,113,113,.35); color: var(--red); }
.nav-ws-dot { width: 7px; height: 7px; border-radius: 50%; background: var(--muted); flex-shrink: 0; transition: background .3s; }
.nav-ws.on  .nav-ws-dot { background: var(--green); animation: pulse 2s infinite; }
.nav-ws.off .nav-ws-dot { background: var(--red); }
.nav-clock {
  font-family: 'JetBrains Mono', monospace; font-size: 11px; color: var(--text2);
  background: var(--bg3); border: 1px solid var(--border); border-radius: 9px;
  padding: 4px 9px; min-width: 76px; text-align: center;
}
.nav-btn {
  width: 36px; height: 36px; border-radius: 9px;
  border: 1px solid var(--border); background: var(--bg3);
  display: flex; align-items: center; justify-content: center;
  cursor: pointer; font-size: 18px; transition: all .2s;
  user-select: none; flex-shrink: 0; text-decoration: none; color: var(--text);
  -webkit-tap-highlight-color: transparent;
}
.nav-btn:hover { border-color: var(--border-h); transform: scale(1.05); }
.nav-hamburger { display: none; }
.nav-hide-desktop { display: none; }
.nav-ham-btn {
  width: 38px; height: 38px; border-radius: 10px;
  border: 1px solid var(--border); background: var(--bg3);
  display: flex; flex-direction: column; align-items: center; justify-content: center;
  gap: 5px; cursor: pointer; transition: all .2s; flex-shrink: 0;
  -webkit-tap-highlight-color: transparent;
}
.nav-ham-btn:hover { border-color: var(--border-h); transform: scale(1.05); }
.nav-ham-line { height: 2px; border-radius: 1px; background: var(--text2); transition: all .2s; }
.nav-ham-line:nth-child(1) { width: 16px; }
.nav-ham-line:nth-child(2) { width: 12px; }
.nav-ham-line:nth-child(3) { width: 16px; }
.nav-ham-btn:hover .nav-ham-line { background: var(--text); }

.nav-user {
  display: flex; align-items: center; gap: 5px;
  padding: 4px 9px; border-radius: 999px;
  border: 1px solid var(--border); background: var(--bg3);
  font-family: 'JetBrains Mono', monospace; font-size: 10px;
  color: var(--text2); white-space: nowrap; flex-shrink: 0;
  max-width: 100px; overflow: hidden; text-overflow: ellipsis;
}
.nav-user-dot {
  width: 6px; height: 6px; border-radius: 50%;
  background: var(--green); flex-shrink: 0;
  box-shadow: 0 0 5px var(--green);
}

/* ── Bottom Sheet ── */
.nav-overlay {
  display: none; position: fixed; inset: 0; z-index: 198;
  background: rgba(0,0,0,.55);
  backdrop-filter: blur(5px); -webkit-backdrop-filter: blur(5px);
}
.nav-overlay.open { display: block; }

.nav-sheet {
  display: none; position: fixed;
  left: 0; right: 0; bottom: 0; z-index: 199;
  background: var(--bg2);
  border-top: 1px solid var(--border-h);
  border-radius: 22px 22px 0 0;
  padding-bottom: max(env(safe-area-inset-bottom, 16px), 16px);
  transform: translateY(100%);
  transition: transform .32s cubic-bezier(.32,0,.67,0);
  box-shadow: 0 -20px 60px rgba(0,0,0,.45);
}
.nav-sheet.open { display: block; }
.nav-sheet.visible { transform: translateY(0); transition: transform .32s cubic-bezier(.33,1,.68,1); }

.sheet-handle { width: 40px; height: 4px; border-radius: 2px; background: var(--border-h); margin: 12px auto 0; }
.sheet-header {
  display: flex; align-items: center; justify-content: space-between;
  padding: 14px 18px 12px;
}
.sheet-brand { display: flex; align-items: center; gap: 10px; font-family: 'Syne', sans-serif; font-size: 15px; font-weight: 800; color: var(--text); }
.sheet-logo { width: 32px; height: 32px; border-radius: 9px; background: linear-gradient(135deg, var(--accent), var(--accent2)); display: flex; align-items: center; justify-content: center; font-size: 15px; }
.sheet-close {
  width: 30px; height: 30px; border-radius: 999px;
  background: var(--bg3); border: 1px solid var(--border);
  display: flex; align-items: center; justify-content: center;
  font-size: 12px; color: var(--muted); cursor: pointer; font-weight: 700;
  -webkit-tap-highlight-color: transparent;
}
.sheet-grid { display: grid; grid-template-columns: 1fr 1fr; gap: 8px; padding: 4px 14px 14px; }
.sheet-link {
  display: flex; flex-direction: column; align-items: center; gap: 8px;
  padding: 16px 8px; border-radius: 14px;
  border: 1px solid var(--border); background: var(--bg3);
  font-family: 'Syne', sans-serif; font-size: 13px; font-weight: 700;
  color: var(--muted); text-decoration: none; text-align: center;
  -webkit-tap-highlight-color: transparent; transition: transform .1s;
}
.sheet-link:active { transform: scale(.95); }
.sheet-link.active { border-color: var(--accent); background: rgba(79,195,247,.08); color: var(--accent); }
.sheet-link-icon { font-size: 26px; }
.sheet-footer { display: grid; grid-template-columns: 1fr 1fr; gap: 8px; padding: 0 14px 6px; border-top: 1px solid var(--border); padding-top: 12px; }
.sheet-action {
  display: flex; align-items: center; justify-content: center; gap: 8px; padding: 13px; border-radius: 12px;
  border: 1px solid var(--border); background: var(--bg3);
  font-family: 'Syne', sans-serif; font-size: 13px; font-weight: 700;
  color: var(--muted); cursor: pointer; text-decoration: none;
  -webkit-tap-highlight-color: transparent; transition: transform .1s;
}
.sheet-action:active { transform: scale(.96); }
.sheet-action.red { color: var(--red); border-color: rgba(248,113,113,.25); background: rgba(248,113,113,.07); }

/* ── Side Panel (desktop) ── */
.nav-panel {
  display: none; position: fixed;
  top: 0; right: 0; bottom: 0; width: 300px; z-index: 199;
  background: var(--bg2); border-left: 1px solid var(--border-h);
  transform: translateX(100%);
  transition: transform .32s cubic-bezier(.32,0,.67,0);
  box-shadow: -20px 0 60px rgba(0,0,0,.4);
  flex-direction: column;
}
.nav-panel.open { display: flex; }
.nav-panel.visible { transform: translateX(0); transition: transform .32s cubic-bezier(.33,1,.68,1); }
.panel-head { padding: 24px 20px 20px; border-bottom: 1px solid var(--border); display: flex; align-items: center; justify-content: space-between; }
.panel-user { display: flex; align-items: center; gap: 12px; }
.panel-avatar { width: 46px; height: 46px; border-radius: 13px; background: linear-gradient(135deg, var(--accent), var(--accent2)); display: flex; align-items: center; justify-content: center; font-family: 'Syne', sans-serif; font-size: 20px; font-weight: 800; color: #fff; flex-shrink: 0; }
.panel-uname { font-family: 'Syne', sans-serif; font-size: 15px; font-weight: 800; color: var(--text); margin-bottom: 4px; }
.panel-status { display: flex; align-items: center; gap: 5px; font-family: 'JetBrains Mono', monospace; font-size: 11px; }
.panel-status-dot { width: 6px; height: 6px; border-radius: 50%; background: var(--green); animation: pulse 2s infinite; }
.panel-status-txt { color: var(--green); }
.panel-status { display: none; }
.panel-live-pill { display: inline-flex; align-items: center; gap: 5px; margin-top: 4px; font-family: 'JetBrains Mono', monospace; font-size: 10px; color: var(--muted); }
.panel-live-dot { width: 6px; height: 6px; border-radius: 50%; background: var(--muted); flex-shrink: 0; }
.panel-live-pill.on .panel-live-dot { background: var(--green); animation: pulse 2s infinite; }
.panel-live-pill.off .panel-live-dot { background: var(--red); }
.panel-live-pill.on { color: var(--green); }
.panel-live-pill.off { color: var(--red); }
.panel-close { width: 32px; height: 32px; border-radius: 999px; background: var(--bg3); border: 1px solid var(--border); display: flex; align-items: center; justify-content: center; font-size: 12px; font-weight: 700; color: var(--muted); cursor: pointer; transition: all .2s; flex-shrink: 0; }
.panel-close:hover { border-color: var(--border-h); color: var(--text); }
.panel-body { flex: 1; padding: 16px; display: flex; flex-direction: column; gap: 10px; overflow-y: auto; }
.panel-card { background: var(--bg3); border: 1px solid var(--border); border-radius: 12px; padding: 14px 16px; }
.panel-card-label { font-family: 'JetBrains Mono', monospace; font-size: 9px; color: var(--muted); letter-spacing: 1.5px; text-transform: uppercase; margin-bottom: 6px; }
.panel-card-value { font-family: 'JetBrains Mono', monospace; font-size: 22px; font-weight: 600; color: var(--text); letter-spacing: -1px; }
.panel-card-sub { font-family: 'JetBrains Mono', monospace; font-size: 10px; color: var(--muted); margin-top: 3px; }
.panel-ws-row { display: flex; align-items: center; gap: 8px; padding: 12px 14px; border-radius: 10px; background: var(--bg3); border: 1px solid var(--border); font-family: 'JetBrains Mono', monospace; font-size: 12px; }
.panel-ws-dot { width: 8px; height: 8px; border-radius: 50%; background: var(--green); flex-shrink: 0; animation: pulse 2s infinite; }
.panel-ws-row.off .panel-ws-dot { background: var(--red); animation: none; }
.panel-ws-row.off { border-color: rgba(248,113,113,.2); }
.panel-ws-row.on  { border-color: rgba(52,211,153,.2); }
.panel-ws-label { color: var(--text2); flex: 1; }
.panel-ws-badge { font-size: 10px; color: var(--muted); background: var(--bg2); border: 1px solid var(--border); border-radius: 5px; padding: 2px 6px; }
.panel-footer { padding: 12px 16px 20px; border-top: 1px solid var(--border); display: flex; flex-direction: column; gap: 8px; }
.panel-footer-btn { display: flex; align-items: center; gap: 10px; padding: 12px 14px; border-radius: 11px; border: 1px solid var(--border); background: var(--bg3); font-family: 'Syne', sans-serif; font-size: 13px; font-weight: 700; color: var(--muted); cursor: pointer; text-decoration: none; transition: all .2s; }
.panel-footer-btn:hover { border-color: var(--border-h); color: var(--text); }
.panel-footer-btn.red { color: var(--red); border-color: rgba(248,113,113,.2); background: rgba(248,113,113,.06); }

/* ── Responsive ── */
@media (max-width: 1380px) { .nl-label { display: none; } .nav-link { padding: 6px 9px; } }
@media (max-width: 900px) {
  .nav-links { display: none; }
  .nav-hamburger { display: flex; }
  .nav-top { padding: 0 16px; grid-template-columns: auto 1fr auto; }
  .nav-clock { display: none; }
  .nav-ws { display: none; }
  .nav-hide-mobile { display: none !important; }
  .nav-hide-desktop { display: flex !important; }
  .nav-user { display: none !important; }
}
@media (max-width: 480px) {
  .nav-top { height: 62px; padding: 0 12px; }
  .nav-title { font-size: 13px; }
  .nav-sub { font-size: 8px; display: block !important; }
  .nav-logo { width: 36px; height: 36px; font-size: 17px; }
  .nav-btn { width: 42px; height: 42px; font-size: 17px; }
}
`;

function buildNav() {
  const current = location.pathname === '/' ? 'dashboard'
    : location.pathname.slice(1).split('/')[0];

  const style = document.createElement('style');
  style.textContent = NAV_CSS;
  document.head.appendChild(style);

  // Main nav
  const nav = document.createElement('nav');
  nav.id = 'main-nav';
  nav.innerHTML = `
    <div class="nav-top">
      <a href="/" class="nav-brand">
        <div class="nav-logo">🛡</div>
        <div class="nav-brand-text">
          <span class="nav-title" id="nav-name">Pi Guardian</span>
          <span class="nav-sub">Raspberry Pi Zero 2W</span>
        </div>
      </a>
      <div class="nav-links">
        ${NAV_PAGES.map(p => `
          <a href="${p.href}" class="nav-link ${p.id===current?'active':''}" style="--nl-color:${p.color}">
            <span class="nl-icon">${p.icon}</span>
            <span class="nl-label">${p.label}</span>
            ${p.id==='alerts'?'<span class="nav-alert-dot" id="nav-dot"></span>':''}
          </a>
        `).join('')}
      </div>
      <div class="nav-right">
        <div class="nav-ham-btn" id="nav-ham" title="Meniu">
          <div class="nav-ham-line"></div>
          <div class="nav-ham-line"></div>
          <div class="nav-ham-line"></div>
        </div>
      </div>
    </div>
  `;
  document.body.insertBefore(nav, document.body.firstChild);

  // Overlay
  const overlay = document.createElement('div');
  overlay.className = 'nav-overlay';
  overlay.id = 'nav-overlay';
  overlay.style.cssText = 'display:none!important';
  document.body.appendChild(overlay);

  // Bottom sheet
  const sheet = document.createElement('div');
  sheet.className = 'nav-sheet';
  sheet.id = 'nav-sheet';
  sheet.style.cssText = 'display:none!important';
  sheet.innerHTML = `
    <div class="sheet-handle"></div>
    <div class="sheet-header">
      <div class="sheet-brand">
        <div class="sheet-logo">🛡</div>
        <span id="sheet-name">Pi Guardian</span>
      </div>
      <div style="display:grid;grid-template-columns:10px auto;align-items:center;row-gap:4px;column-gap:6px">
        <div id="sheet-user-dot" style="width:6px;height:6px;border-radius:50%;background:var(--green);animation:pulse 2s infinite;justify-self:center"></div>
        <span id="sheet-username" style="display:none;font-family:'JetBrains Mono',monospace;font-size:11px;color:var(--text2)">--</span>
        <div id="sheet-live-dot" style="width:6px;height:6px;border-radius:50%;background:var(--green);animation:pulse 2s infinite;justify-self:center;display:none"></div>
        <span id="sheet-live-lbl" style="display:none;font-family:'JetBrains Mono',monospace;font-size:10px;color:var(--green)">Live</span>
      </div>
    </div>
    <div class="sheet-grid">
      ${NAV_PAGES.map(p => `
        <a href="${p.href}" class="sheet-link ${p.id===current?'active':''}">
          <span class="sheet-link-icon">${p.icon}</span>
          ${p.label}
        </a>
      `).join('')}
    </div>
    <div class="sheet-footer">
      <div class="sheet-action" id="sheet-theme-btn">🌙 Theme</div>
      <a href="/logout" class="sheet-action red">🚪 Exit</a>
    </div>
  `;
  document.body.appendChild(sheet);

  // Side Panel
  const panel = document.createElement('div');
  panel.className = 'nav-panel';
  panel.id = 'nav-panel';
  panel.innerHTML = `
    <div class="panel-head">
      <div class="panel-user">
        <div class="panel-avatar" id="panel-avatar">?</div>
        <div>
          <div class="panel-uname" id="panel-uname">--</div>
          <div class="panel-status">
            <div class="panel-status-dot" id="panel-status-dot"></div>
            <span class="panel-status-txt" id="panel-status-txt">Online</span>
          </div>
          <div class="panel-live-pill" id="panel-live-pill">
            <div class="panel-live-dot"></div>
            <span id="panel-live-lbl">Live</span>
          </div>
        </div>
      </div>
      <div class="panel-close" id="panel-close">✕</div>
    </div>
    <div class="panel-body">
      <div class="panel-card">
        <div class="panel-card-label">🕐 Current time</div>
        <div class="panel-card-value" id="panel-clock">--:--:--</div>
        <div class="panel-card-sub" id="panel-date">--</div>
      </div>
      <div class="panel-ws-row" id="panel-ws-row">
        <div class="panel-ws-dot"></div>
        <span class="panel-ws-label" id="panel-ws-label">Connected</span>
        <span class="panel-ws-badge">WebSocket</span>
      </div>
      <div class="panel-card">
        <div class="panel-card-label">🛡 Device</div>
        <div class="panel-card-value" style="font-size:16px" id="panel-device">Pi Guardian</div>
        <div class="panel-card-sub">Raspberry Pi Zero 2W</div>
      </div>
    </div>
    <div class="panel-footer">
      <div class="panel-footer-btn" id="panel-theme-btn">🌙 Switch theme</div>
      <a href="/logout" class="panel-footer-btn red">🚪 Log out</a>
    </div>
  `;
  document.body.appendChild(panel);

  // Theme
  const themeBtn = null; // removed from desktop navbar
  const sheetThemeBtn = document.getElementById('sheet-theme-btn');
  function applyTheme(t) {
    document.documentElement.setAttribute('data-theme', t);
    const icon = t === 'dark' ? '🌙' : '☀️';
    if (themeBtn) themeBtn.textContent = icon;
    if (sheetThemeBtn) sheetThemeBtn.textContent = icon + ' Theme';
    localStorage.setItem('pi-theme', t);
  }
  const toggleTheme = () => applyTheme(
    document.documentElement.getAttribute('data-theme') === 'dark' ? 'light' : 'dark'
  );
  if (themeBtn) themeBtn.addEventListener('click', toggleTheme);
  if (sheetThemeBtn) sheetThemeBtn.addEventListener('click', toggleTheme);
  applyTheme(localStorage.getItem('pi-theme') || 'dark');

  // Clock
  const clockEl = document.getElementById('nav-clock');
  function tick() { if (clockEl) clockEl.textContent = new Date().toLocaleTimeString('en-GB'); }
  tick(); setInterval(tick, 1000);

  // Sheet open/close
  const ham = document.getElementById('nav-ham');
  const closeBtn = document.getElementById('sheet-close');

  function openSheet() {
    overlay.style.cssText = '';
    sheet.style.cssText = '';
    sheet.classList.add('open');
    overlay.classList.add('open');
    document.body.style.overflow = 'hidden';
    requestAnimationFrame(() => requestAnimationFrame(() => sheet.classList.add('visible')));
  }
  function closeSheet() {
    sheet.classList.remove('visible');
    document.body.style.overflow = '';
    setTimeout(() => {
      sheet.classList.remove('open');
      overlay.classList.remove('open');
      sheet.style.cssText = 'display:none!important';
      overlay.style.cssText = 'display:none!important';
    }, 340);
  }

  // Panel open/close
  const panelClose = document.getElementById('panel-close');
  const panelThemeBtn = document.getElementById('panel-theme-btn');
  let panelClockInterval = null;

  function isMobile() { return window.innerWidth <= 900; }

  function openPanel() {
    panel.classList.add('open');
    overlay.style.cssText = '';
    overlay.classList.add('open');
    document.body.style.overflow = 'hidden';
    requestAnimationFrame(() => requestAnimationFrame(() => panel.classList.add('visible')));
    updatePanelClock();
    panelClockInterval = setInterval(updatePanelClock, 1000);
  }
  function closePanel() {
    panel.classList.remove('visible');
    document.body.style.overflow = '';
    clearInterval(panelClockInterval);
    setTimeout(() => {
      panel.classList.remove('open');
      overlay.classList.remove('open');
      overlay.style.cssText = 'display:none!important';
    }, 340);
  }
  function updatePanelClock() {
    const now = new Date();
    const cl = document.getElementById('panel-clock');
    const dt = document.getElementById('panel-date');
    if (cl) cl.textContent = now.toLocaleTimeString('en-GB');
    if (dt) dt.textContent = now.toLocaleDateString('en-GB', {weekday:'long', day:'2-digit', month:'long', year:'numeric'});
  }

  if (ham) ham.addEventListener('click', () => {
    if (isMobile()) {
      sheet.classList.contains('open') ? closeSheet() : openSheet();
    } else {
      panel.classList.contains('open') ? closePanel() : openPanel();
    }
  });
  overlay.addEventListener('click', () => {
    if (panel.classList.contains('open')) closePanel();
    else closeSheet();
  });
  if (panelClose) panelClose.addEventListener('click', closePanel);
  if (panelThemeBtn) panelThemeBtn.addEventListener('click', () => {
    const t = document.documentElement.getAttribute('data-theme') === 'dark' ? 'light' : 'dark';
    applyTheme(t);
  });
  // Sheet closes via swipe, overlay click, or ESC — no X button needed
  sheet.querySelectorAll('a').forEach(a => a.addEventListener('click', closeSheet));
  document.addEventListener('keydown', e => { if (e.key === 'Escape') { closeSheet(); closePanel(); } });

  // Swipe down to close
  let ty = 0;
  sheet.addEventListener('touchstart', e => { ty = e.touches[0].clientY; }, {passive:true});
  sheet.addEventListener('touchmove', e => {
    const d = e.touches[0].clientY - ty;
    if (d > 0) sheet.style.transform = `translateY(${d}px)`;
  }, {passive:true});
  sheet.addEventListener('touchend', e => {
    const d = e.changedTouches[0].clientY - ty;
    sheet.style.transform = '';
    if (d > 70) closeSheet();
  }, {passive:true});

  // Device name
  fetch('/api/device').then(r => r.json()).then(d => {
    if (d.name) {
      const n = document.getElementById('nav-name');
      const s = document.getElementById('sheet-name');
      if (n) n.textContent = d.name;
      if (s) s.textContent = d.name;
      const page = NAV_PAGES.find(p => p.id === current);
      document.title = (page ? page.label + ' — ' : '') + d.name;
    }
    if (d.username) {
      const sspan = document.getElementById('sheet-username');
      const sldot = document.getElementById('sheet-live-dot');
      const slbl = document.getElementById('sheet-live-lbl');
      const sudot = document.getElementById('sheet-user-dot');
      if (sspan) { sspan.textContent = d.username; sspan.style.display = 'block'; }
      if (sudot) sudot.style.display = 'block';
      if (sldot) sldot.style.display = 'block';
      if (slbl) slbl.style.display = 'block';
      // Panel
      const pu = document.getElementById('panel-uname');
      const pa = document.getElementById('panel-avatar');
      const pd = document.getElementById('panel-device');
      if (pu) pu.textContent = d.username;
      if (pa) { pa.style.background = 'transparent'; pa.style.border = '1px solid var(--border)'; pa.style.fontSize = '24px'; pa.textContent = '👤'; }
    }
    if (d.name) {
      const pd = document.getElementById('panel-device');
      if (pd) pd.textContent = d.name;
    }
  }).catch(() => {});

  // Global helpers
  window._setWs = online => {
    // Sheet sync
    const sud = document.getElementById('sheet-user-dot');
    const sld = document.getElementById('sheet-live-dot');
    const sll = document.getElementById('sheet-live-lbl');
    if (sud) { sud.style.background = online ? 'var(--green)' : 'var(--red)'; sud.style.animation = online ? 'pulse 2s infinite' : 'none'; }
    if (sld) { sld.style.background = online ? 'var(--green)' : 'var(--red)'; sld.style.animation = online ? 'pulse 2s infinite' : 'none'; }
    if (sll) { sll.textContent = online ? 'Live' : 'Offline'; sll.style.color = online ? 'var(--green)' : 'var(--red)'; }
    // Panel sync
    const pwr = document.getElementById('panel-ws-row');
    const pwl = document.getElementById('panel-ws-label');
    const plp = document.getElementById('panel-live-pill');
    const pll = document.getElementById('panel-live-lbl');
    const psd = document.getElementById('panel-status-dot');
    const pst = document.getElementById('panel-status-txt');
    if (pwr) pwr.className = 'panel-ws-row ' + (online ? 'on' : 'off');
    if (pwl) pwl.textContent = online ? 'Online' : 'Offline';
    if (plp) plp.className = 'panel-live-pill ' + (online ? 'on' : 'off');
    if (pll) pll.textContent = online ? 'Live' : 'Offline';
    if (psd) { psd.style.background = online ? 'var(--green)' : 'var(--red)'; psd.style.animation = online ? 'pulse 2s infinite' : 'none'; }
    if (pst) { pst.textContent = online ? 'Online' : 'Offline'; pst.style.color = online ? 'var(--green)' : 'var(--red)'; }
  };
  window._setAlertDot = show => {
    const d = document.getElementById('nav-dot');
    if (d) d.style.display = show ? 'block' : 'none';
  };
  window._notify = (title, body) => {
    if (!('Notifiedion' in window)) return;
    if (Notifiedion.permission === 'granted') new Notifiedion(title, { body });
    else if (Notifiedion.permission !== 'denied') Notifiedion.requestPermission();
  };

  // WS connection
  if (!window._wsExternal) {
    let retries = 0;
    function connectWs() {
      const ws = new WebSocket((location.protocol === 'https:' ? 'wss' : 'ws') + '://' + location.host + '/ws');
      ws.onopen = () => {
        retries = 0;
        if (window._setWs) window._setWs(true);
        const ka = setInterval(() => { if (ws.readyState === 1) ws.send('ping'); else clearInterval(ka); }, 25000);
      };
      ws.onclose = () => {
        if (window._setWs) window._setWs(false);
        setTimeout(connectWs, Math.min(3000 * Math.pow(1.5, retries++), 30000));
      };
      ws.onerror = () => ws.close();
      ws.onmessage = ({data}) => {
        try {
          const d = JSON.parse(data);
          const s = d.system, a = d.adguard;
          let alert = false;
          if (s && (s.cpu_temp >= 75 || s.cpu_percent >= 90 || s.ram_percent >= 90 || s.disk_percent >= 85)) alert = true;
          if (a && !a.ok) alert = true;
          if (window._setAlertDot) window._setAlertDot(alert);
          if (window._onWsData) window._onWsData(d);
        } catch(e) {}
      };
    }
    connectWs();
  }

  if ('Notifiedion' in window && Notifiedion.permission === 'default') {
    setTimeout(() => Notifiedion.requestPermission(), 3000);
  }
}

document.addEventListener('DOMContentLoaded', buildNav);