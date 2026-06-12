// ==UserScript==
// @name         Dance Platform — Send to Dance
// @namespace    https://dance-api.takelord.com
// @version      1.0.0
// @description  Adds a "Send to Dance" button on YouTube to import the current video into Dance Platform
// @author       Justas V
// @match        https://www.youtube.com/watch*
// @grant        GM_setValue
// @grant        GM_getValue
// @grant        GM_xmlhttpRequest
// @connect      dance-api.takelord.com
// @connect      localhost
// @run-at       document-idle
// ==/UserScript==

(function () {
  'use strict';

  // ── Configuration ──────────────────────────────────────────────────────────
  const DEFAULT_API = 'https://dance-api.takelord.com/api';

  // ── State ──────────────────────────────────────────────────────────────────
  let token = GM_getValue('dp_token', '');
  let apiUrl = GM_getValue('dp_api_url', DEFAULT_API);
  let allDances = [];
  let selectedDance = null;
  let panelOpen = false;
  let lastVideoId = '';

  // ── Styles ─────────────────────────────────────────────────────────────────
  const css = `
    #dp-btn {
      display: inline-flex;
      align-items: center;
      gap: 6px;
      height: 36px;
      padding: 0 16px;
      background: #0f0f0f;
      color: #f1f1f1;
      border: 1px solid #3f3f3f;
      border-radius: 18px;
      font-family: Roboto, Arial, sans-serif;
      font-size: 14px;
      font-weight: 500;
      cursor: pointer;
      transition: background 0.15s, border-color 0.15s;
      flex-shrink: 0;
    }
    #dp-btn:hover { background: #272727; border-color: #717171; }
    #dp-btn svg { width: 16px; height: 16px; fill: #f1f1f1; flex-shrink: 0; }

    #dp-panel {
      position: fixed;
      top: 72px;
      right: 24px;
      width: 360px;
      background: #1f1f1f;
      border: 1px solid #3f3f3f;
      border-radius: 12px;
      box-shadow: 0 8px 32px rgba(0,0,0,0.6);
      font-family: Roboto, Arial, sans-serif;
      font-size: 14px;
      color: #e0e0e0;
      z-index: 9999;
      display: flex;
      flex-direction: column;
      overflow: hidden;
      animation: dp-slide-in 0.18s ease;
    }
    @keyframes dp-slide-in {
      from { opacity: 0; transform: translateY(-8px) scale(0.98); }
      to   { opacity: 1; transform: translateY(0)   scale(1); }
    }

    #dp-panel-header {
      display: flex;
      align-items: center;
      justify-content: space-between;
      padding: 14px 16px 12px;
      border-bottom: 1px solid #3f3f3f;
    }
    #dp-panel-header h3 {
      margin: 0;
      font-size: 15px;
      font-weight: 600;
      color: #fff;
      display: flex;
      align-items: center;
      gap: 8px;
    }
    #dp-close-btn {
      background: none;
      border: none;
      color: #aaa;
      cursor: pointer;
      padding: 4px;
      border-radius: 50%;
      line-height: 1;
      font-size: 18px;
      transition: color 0.15s, background 0.15s;
    }
    #dp-close-btn:hover { color: #fff; background: #3f3f3f; }

    #dp-panel-body { padding: 16px; display: flex; flex-direction: column; gap: 14px; }

    .dp-auth-info {
      display: flex;
      align-items: center;
      gap: 8px;
      padding: 8px 12px;
      background: #2a2a2a;
      border-radius: 8px;
      font-size: 12px;
      color: #aaa;
    }
    .dp-auth-info .dp-dot {
      width: 8px; height: 8px; border-radius: 50%; flex-shrink: 0;
      background: #4caf50;
    }
    .dp-auth-info .dp-dot.offline { background: #f44336; }
    .dp-auth-logout {
      margin-left: auto;
      background: none;
      border: none;
      color: #ff6b6b;
      font-size: 11px;
      cursor: pointer;
      padding: 2px 6px;
      border-radius: 4px;
      transition: background 0.15s;
    }
    .dp-auth-logout:hover { background: #3f3f3f; }

    .dp-field { display: flex; flex-direction: column; gap: 5px; }
    .dp-field label { font-size: 11px; font-weight: 600; text-transform: uppercase; letter-spacing: 0.06em; color: #888; }
    .dp-field input, .dp-field textarea {
      background: #2a2a2a;
      border: 1px solid #3f3f3f;
      border-radius: 8px;
      color: #e0e0e0;
      font-family: Roboto, Arial, sans-serif;
      font-size: 13px;
      padding: 8px 10px;
      outline: none;
      transition: border-color 0.15s;
      width: 100%;
      box-sizing: border-box;
    }
    .dp-field input:focus, .dp-field textarea:focus { border-color: #717171; }
    .dp-field textarea { resize: vertical; min-height: 54px; }

    .dp-time-row { display: flex; gap: 10px; }
    .dp-time-row .dp-field { flex: 1; }

    .dp-dance-search { position: relative; }
    .dp-dance-list {
      position: absolute;
      top: 100%;
      left: 0; right: 0;
      background: #2a2a2a;
      border: 1px solid #3f3f3f;
      border-top: none;
      border-radius: 0 0 8px 8px;
      max-height: 180px;
      overflow-y: auto;
      z-index: 10000;
    }
    .dp-dance-list:empty { display: none; }
    .dp-dance-item {
      padding: 8px 10px;
      cursor: pointer;
      font-size: 13px;
      color: #e0e0e0;
      transition: background 0.1s;
      border-bottom: 1px solid #333;
    }
    .dp-dance-item:last-child { border-bottom: none; }
    .dp-dance-item:hover, .dp-dance-item.selected { background: #3f3f3f; }
    .dp-dance-selected {
      padding: 6px 10px;
      background: #1a3a1a;
      border: 1px solid #2e6b2e;
      border-radius: 6px;
      font-size: 12px;
      color: #4caf50;
      display: flex;
      align-items: center;
      justify-content: space-between;
      margin-top: 4px;
    }
    .dp-dance-selected button {
      background: none; border: none; color: #888; cursor: pointer; font-size: 14px; padding: 0;
    }
    .dp-dance-selected button:hover { color: #f1f1f1; }

    .dp-submit-btn {
      width: 100%;
      padding: 10px;
      background: #ff0000;
      color: #fff;
      border: none;
      border-radius: 8px;
      font-family: Roboto, Arial, sans-serif;
      font-size: 14px;
      font-weight: 600;
      cursor: pointer;
      transition: background 0.15s, opacity 0.15s;
    }
    .dp-submit-btn:hover:not(:disabled) { background: #cc0000; }
    .dp-submit-btn:disabled { opacity: 0.5; cursor: not-allowed; }

    .dp-status {
      text-align: center;
      font-size: 12px;
      padding: 6px;
      border-radius: 6px;
    }
    .dp-status.success { background: #1a3a1a; color: #4caf50; }
    .dp-status.error   { background: #3a1a1a; color: #f44336; }

    #dp-login-section { display: flex; flex-direction: column; gap: 12px; }
    #dp-login-section .dp-login-title {
      font-size: 13px; color: #aaa; text-align: center; padding: 4px 0;
    }
    .dp-settings-row {
      display: flex;
      align-items: center;
      gap: 8px;
    }
    .dp-settings-row .dp-field { flex: 1; }
    .dp-settings-btn {
      background: #3f3f3f;
      border: none;
      color: #e0e0e0;
      border-radius: 8px;
      padding: 8px 12px;
      font-size: 13px;
      cursor: pointer;
      white-space: nowrap;
      transition: background 0.15s;
    }
    .dp-settings-btn:hover { background: #555; }
  `;

  function injectStyles() {
    if (document.getElementById('dp-styles')) return;
    const s = document.createElement('style');
    s.id = 'dp-styles';
    s.textContent = css;
    document.head.appendChild(s);
  }

  // ── API helpers ────────────────────────────────────────────────────────────
  function apiFetch(method, path, body) {
    return new Promise((resolve, reject) => {
      GM_xmlhttpRequest({
        method,
        url: `${apiUrl}${path}`,
        headers: {
          'Content-Type': 'application/json',
          ...(token ? { 'Authorization': `Bearer ${token}` } : {})
        },
        data: body ? JSON.stringify(body) : undefined,
        onload: (res) => {
          if (res.status >= 200 && res.status < 300) {
            try { resolve(JSON.parse(res.responseText)); }
            catch { resolve(res.responseText); }
          } else {
            let msg = `HTTP ${res.status}`;
            try { msg = JSON.parse(res.responseText)?.message || msg; } catch {}
            reject(new Error(msg));
          }
        },
        onerror: () => reject(new Error('Network error — is the API running?'))
      });
    });
  }

  // ── YouTube helpers ────────────────────────────────────────────────────────
  function getVideoId() {
    return new URLSearchParams(window.location.search).get('v') || '';
  }

  function getVideoTitle() {
    return (
      document.querySelector('ytd-watch-flexy #title h1 yt-formatted-string')?.textContent?.trim() ||
      document.querySelector('#title h1 yt-formatted-string')?.textContent?.trim() ||
      document.querySelector('#title h1')?.textContent?.trim() ||
      document.title.replace(/ - YouTube$/, '').trim()
    );
  }

  function getCurrentTime() {
    const video = document.querySelector('video.html5-main-video') || document.querySelector('video');
    return video ? Math.floor(video.currentTime) : 0;
  }

  function formatTime(secs) {
    if (!secs && secs !== 0) return '';
    const m = Math.floor(secs / 60);
    const s = Math.floor(secs % 60);
    return `${m}:${s.toString().padStart(2, '0')}`;
  }

  function parseTime(str) {
    const s = (str || '').trim();
    if (!s) return undefined;
    if (s.includes(':')) {
      const parts = s.split(':').map(Number);
      if (parts.some(isNaN)) return undefined;
      return parts.length === 3
        ? parts[0] * 3600 + parts[1] * 60 + parts[2]
        : parts[0] * 60 + parts[1];
    }
    const n = Number(s);
    return isNaN(n) ? undefined : n;
  }

  // ── Panel ──────────────────────────────────────────────────────────────────
  function buildPanel() {
    const existing = document.getElementById('dp-panel');
    if (existing) { existing.remove(); panelOpen = false; return; }

    const videoId = getVideoId();
    const title = getVideoTitle();
    const startSecs = getCurrentTime();

    const panel = document.createElement('div');
    panel.id = 'dp-panel';

    panel.innerHTML = `
      <div id="dp-panel-header">
        <h3>
          <svg viewBox="0 0 24 24"><path d="M12 2C6.48 2 2 6.48 2 12s4.48 10 10 10 10-4.48 10-10S17.52 2 12 2zm-2 14.5v-9l6 4.5-6 4.5z"/></svg>
          Send to Dance
        </h3>
        <button id="dp-close-btn" title="Close">✕</button>
      </div>
      <div id="dp-panel-body">
        ${token ? buildImportSection(title, startSecs, videoId) : buildLoginSection()}
      </div>
    `;

    document.body.appendChild(panel);
    panelOpen = true;

    document.getElementById('dp-close-btn').onclick = () => { panel.remove(); panelOpen = false; };

    if (token) {
      bindImportSection(panel, videoId);
    } else {
      bindLoginSection(panel);
    }
  }

  function buildLoginSection() {
    return `
      <div id="dp-login-section">
        <p class="dp-login-title">Log in to Dance Platform to continue</p>
        <div class="dp-field">
          <label>API URL</label>
          <input id="dp-api-input" type="text" value="${apiUrl}" placeholder="https://dance-api.takelord.com/api" />
        </div>
        <div class="dp-field">
          <label>Username</label>
          <input id="dp-username" type="text" autocomplete="username" placeholder="your username" />
        </div>
        <div class="dp-field">
          <label>Password</label>
          <input id="dp-password" type="password" autocomplete="current-password" placeholder="••••••••" />
        </div>
        <button class="dp-submit-btn" id="dp-login-btn">Log In</button>
        <div id="dp-login-status"></div>
      </div>
    `;
  }

  function buildImportSection(title, startSecs, videoId) {
    return `
      <div class="dp-auth-info">
        <span class="dp-dot"></span>
        <span>Connected · <span id="dp-api-label">${apiUrl.replace('https://', '').replace('/api', '')}</span></span>
        <button class="dp-auth-logout" id="dp-logout-btn">Log out</button>
      </div>

      <div class="dp-field">
        <label>Video Title</label>
        <input id="dp-title" type="text" value="${escHtml(title)}" placeholder="Video title" />
      </div>

      <div class="dp-field dp-dance-search" id="dp-dance-field">
        <label>Dance</label>
        <input id="dp-dance-input" type="text" placeholder="Type to search dances…" autocomplete="off" />
        <div class="dp-dance-list" id="dp-dance-list"></div>
        <div class="dp-dance-selected" id="dp-dance-selected" style="display:none">
          <span id="dp-dance-selected-name"></span>
          <button id="dp-dance-clear">✕</button>
        </div>
      </div>

      <div class="dp-time-row">
        <div class="dp-field">
          <label>Start Time</label>
          <input id="dp-start" type="text" value="${formatTime(startSecs)}" placeholder="m:ss or blank" />
        </div>
        <div class="dp-field">
          <label>End Time</label>
          <input id="dp-end" type="text" value="" placeholder="m:ss or blank" />
        </div>
      </div>

      <button class="dp-submit-btn" id="dp-import-btn" disabled>Select a dance first</button>
      <div id="dp-import-status"></div>
    `;
  }

  function escHtml(str) {
    return (str || '').replace(/&/g, '&amp;').replace(/"/g, '&quot;').replace(/</g, '&lt;').replace(/>/g, '&gt;');
  }

  function bindLoginSection(panel) {
    const apiInput = panel.querySelector('#dp-api-input');
    const loginBtn = panel.querySelector('#dp-login-btn');
    const statusEl = panel.querySelector('#dp-login-status');

    loginBtn.onclick = async () => {
      const url = (apiInput.value || '').trim().replace(/\/$/, '');
      const username = panel.querySelector('#dp-username').value.trim();
      const password = panel.querySelector('#dp-password').value;
      if (!username || !password) { showStatus(statusEl, 'Enter username and password.', 'error'); return; }

      apiUrl = url || DEFAULT_API;
      GM_setValue('dp_api_url', apiUrl);

      loginBtn.disabled = true;
      loginBtn.textContent = 'Logging in…';
      statusEl.textContent = '';

      try {
        const res = await apiFetch('POST', '/auth/login', { username, password });
        token = res.token;
        GM_setValue('dp_token', token);
        // Rebuild panel with import section
        const videoId = getVideoId();
        panel.querySelector('#dp-panel-body').innerHTML = buildImportSection(getVideoTitle(), getCurrentTime(), videoId);
        bindImportSection(panel, videoId);
      } catch (err) {
        loginBtn.disabled = false;
        loginBtn.textContent = 'Log In';
        showStatus(statusEl, err.message, 'error');
      }
    };

    panel.querySelector('#dp-username')?.addEventListener('keydown', e => { if (e.key === 'Enter') panel.querySelector('#dp-password')?.focus(); });
    panel.querySelector('#dp-password')?.addEventListener('keydown', e => { if (e.key === 'Enter') loginBtn.click(); });
  }

  function bindImportSection(panel, videoId) {
    const danceInput = panel.querySelector('#dp-dance-input');
    const danceList = panel.querySelector('#dp-dance-list');
    const danceSelected = panel.querySelector('#dp-dance-selected');
    const danceSelectedName = panel.querySelector('#dp-dance-selected-name');
    const danceClear = panel.querySelector('#dp-dance-clear');
    const importBtn = panel.querySelector('#dp-import-btn');
    const statusEl = panel.querySelector('#dp-import-status');

    panel.querySelector('#dp-logout-btn')?.addEventListener('click', () => {
      token = '';
      GM_setValue('dp_token', '');
      panel.querySelector('#dp-panel-body').innerHTML = buildLoginSection();
      bindLoginSection(panel);
    });

    // Load dances
    if (allDances.length === 0) {
      apiFetch('GET', '/dances').then(data => {
        allDances = data || [];
        if (danceInput === document.activeElement) renderDanceList(danceInput.value);
      }).catch(() => {});
    }

    function renderDanceList(query) {
      const q = query.toLowerCase();
      const filtered = allDances
        .filter(d => d.name.toLowerCase().includes(q))
        .slice(0, 25);

      danceList.innerHTML = filtered.map(d =>
        `<div class="dp-dance-item" data-id="${d.id}" data-name="${escHtml(d.name)}">${escHtml(d.name)}</div>`
      ).join('');

      danceList.style.display = filtered.length ? '' : 'none';
    }

    function selectDance(id, name) {
      selectedDance = { id, name };
      danceInput.style.display = 'none';
      danceList.innerHTML = '';
      danceList.style.display = 'none';
      danceSelectedName.textContent = name;
      danceSelected.style.display = 'flex';
      importBtn.disabled = false;
      importBtn.textContent = 'Send to Dance';
    }

    danceInput.addEventListener('input', () => renderDanceList(danceInput.value));
    danceInput.addEventListener('focus', () => renderDanceList(danceInput.value));
    danceInput.addEventListener('blur', () => setTimeout(() => { danceList.style.display = 'none'; }, 150));

    danceList.addEventListener('mousedown', e => {
      const item = e.target.closest('.dp-dance-item');
      if (item) selectDance(Number(item.dataset.id), item.dataset.name);
    });

    danceClear?.addEventListener('click', () => {
      selectedDance = null;
      danceInput.style.display = '';
      danceSelected.style.display = 'none';
      importBtn.disabled = true;
      importBtn.textContent = 'Select a dance first';
      danceInput.focus();
    });

    importBtn.addEventListener('click', async () => {
      if (!selectedDance) return;
      const title = panel.querySelector('#dp-title').value.trim();
      if (!title) { showStatus(statusEl, 'Title is required.', 'error'); return; }

      const startTime = parseTime(panel.querySelector('#dp-start').value);
      const endTime = parseTime(panel.querySelector('#dp-end').value);

      importBtn.disabled = true;
      importBtn.textContent = 'Sending…';
      statusEl.textContent = '';

      try {
        const result = await apiFetch('POST', '/import/youtube-video', {
          youtubeUrl: `https://www.youtube.com/watch?v=${videoId}`,
          title,
          danceId: selectedDance.id,
          startTime,
          endTime
        });
        showStatus(statusEl, `✓ Added "${result.title}" to ${selectedDance.name}`, 'success');
        importBtn.textContent = 'Sent!';
        setTimeout(() => { importBtn.disabled = false; importBtn.textContent = 'Send Another'; }, 2500);
      } catch (err) {
        showStatus(statusEl, err.message, 'error');
        importBtn.disabled = false;
        importBtn.textContent = 'Send to Dance';
      }
    });
  }

  function showStatus(el, msg, type) {
    el.className = `dp-status ${type}`;
    el.textContent = msg;
  }

  // ── Button injection ───────────────────────────────────────────────────────
  function injectButton() {
    if (document.getElementById('dp-btn')) return;

    const container =
      document.querySelector('#actions #top-level-buttons-computed') ||
      document.querySelector('ytd-watch-metadata #actions #top-level-buttons-computed') ||
      document.querySelector('#actions ytd-button-renderer')?.parentElement ||
      document.querySelector('#actions');

    if (!container) return;

    const btn = document.createElement('button');
    btn.id = 'dp-btn';
    btn.title = 'Send to Dance Platform';
    btn.innerHTML = `
      <svg viewBox="0 0 24 24"><path d="M12 3v10.55c-.59-.34-1.27-.55-2-.55-2.21 0-4 1.79-4 4s1.79 4 4 4 4-1.79 4-4V7h4V3h-6z"/></svg>
      Send to Dance
    `;
    btn.addEventListener('click', buildPanel);
    container.appendChild(btn);
  }

  // ── Navigation observer ────────────────────────────────────────────────────
  function onNavigate() {
    const vid = getVideoId();
    if (vid === lastVideoId) return;
    lastVideoId = vid;

    // Remove stale button and panel
    document.getElementById('dp-btn')?.remove();
    document.getElementById('dp-panel')?.remove();
    panelOpen = false;

    // Re-inject after DOM settles
    let attempts = 0;
    const tryInject = () => {
      injectButton();
      if (!document.getElementById('dp-btn') && ++attempts < 15) {
        setTimeout(tryInject, 800);
      }
    };
    setTimeout(tryInject, 1200);
  }

  // YouTube fires this on SPA navigation
  window.addEventListener('yt-navigate-finish', onNavigate);

  // Also watch URL via polling fallback (some navigation events are missed)
  let pollUrl = location.href;
  setInterval(() => {
    if (location.href !== pollUrl) {
      pollUrl = location.href;
      if (location.pathname === '/watch') onNavigate();
    }
  }, 1000);

  // ── Init ───────────────────────────────────────────────────────────────────
  injectStyles();

  let initAttempts = 0;
  function init() {
    injectButton();
    if (!document.getElementById('dp-btn') && ++initAttempts < 20) {
      setTimeout(init, 800);
    } else {
      lastVideoId = getVideoId();
    }
  }
  setTimeout(init, 1500);

})();
