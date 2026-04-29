/**
 * Timer — localStorage-backed stopwatch
 * State: { curriculum_id, curriculum_name, item_id, start_ms, running, paused_seconds }
 */

const TC_KEY = 'tc_timer';

function timerGetState() {
  try { return JSON.parse(localStorage.getItem(TC_KEY)); } catch { return null; }
}
function timerSetState(s) {
  if (s) localStorage.setItem(TC_KEY, JSON.stringify(s));
  else localStorage.removeItem(TC_KEY);
}
function timerElapsed() {
  const s = timerGetState();
  if (!s) return 0;
  return s.running ? Math.floor((Date.now() - s.start_ms) / 1000) : (s.paused_seconds || 0);
}
function fmtTime(secs) {
  const h = Math.floor(secs / 3600), m = Math.floor((secs % 3600) / 60), s = secs % 60;
  return `${String(h).padStart(2,'0')}:${String(m).padStart(2,'0')}:${String(s).padStart(2,'0')}`;
}

function localDateString() {
  const now = new Date();
  const year = now.getFullYear();
  const month = String(now.getMonth() + 1).padStart(2, '0');
  const day = String(now.getDate()).padStart(2, '0');
  return `${year}-${month}-${day}`;
}

// ── Nav indicator (every page) ──────────────────────────────────────────────
function updateNavIndicator() {
  const state = timerGetState();
  const el = document.getElementById('nav-timer-indicator');
  const display = document.getElementById('nav-timer-display');
  if (!el || !display) return;
  if (state && (state.running || state.paused_seconds > 0)) {
    el.classList.remove('hidden'); el.classList.add('flex');
    display.textContent = fmtTime(timerElapsed());
  } else {
    el.classList.add('hidden'); el.classList.remove('flex');
  }
}
setInterval(updateNavIndicator, 1000);
updateNavIndicator();

// ── Timer page ──────────────────────────────────────────────────────────────
document.addEventListener('DOMContentLoaded', () => {
  const display  = document.getElementById('timer-display');
  if (!display) return;

  const startBtn = document.getElementById('timer-start');
  const pauseBtn = document.getElementById('timer-pause');
  const stopBtn  = document.getElementById('timer-stop');
  const noteEl   = document.getElementById('timer-note');
  const confirmEl = document.getElementById('timer-confirm');
  const currSel  = document.getElementById('timer-curriculum');
  const itemSel  = document.getElementById('timer-item');

  let tickInterval = null;

  function tick() { display.textContent = fmtTime(timerElapsed()); }

  function applyUI(state) {
    if (!state || (!state.running && !state.paused_seconds)) {
      startBtn.textContent = 'Start'; startBtn.classList.remove('hidden');
      if (pauseBtn) pauseBtn.classList.add('hidden');
      if (stopBtn)  stopBtn.classList.add('hidden');
      if (currSel) currSel.disabled = false;
      if (itemSel) itemSel.disabled = false;
      display.textContent = '00:00:00';
    } else if (state.running) {
      startBtn.classList.add('hidden');
      if (pauseBtn) pauseBtn.classList.remove('hidden');
      if (stopBtn)  stopBtn.classList.remove('hidden');
      if (currSel) currSel.disabled = true;
      if (itemSel) itemSel.disabled = true;
    } else {
      startBtn.textContent = 'Resume'; startBtn.classList.remove('hidden');
      if (pauseBtn) pauseBtn.classList.add('hidden');
      if (stopBtn)  stopBtn.classList.remove('hidden');
      if (currSel) currSel.disabled = true;
      if (itemSel) itemSel.disabled = true;
    }
  }

  // Restore on page load
  const existing = timerGetState();
  if (existing) {
    applyUI(existing); tick();
    if (existing.running) tickInterval = setInterval(tick, 1000);
    if (currSel && existing.curriculum_id) currSel.value = String(existing.curriculum_id);
  }

  if (startBtn) startBtn.addEventListener('click', () => {
    if (!currSel || !currSel.value) { alert('Select a curriculum first.'); return; }
    if (itemSel) {
      const opts = itemSel.querySelectorAll('option');
      const onlyCurriculum = opts.length === 1 && opts[0].value === '0';
      const needsItem = opts.length > 0 && !onlyCurriculum;
      if (needsItem && (!itemSel.value || itemSel.value === '')) {
        alert('Select a roadmap item. This curriculum tracks time per item.');
        return;
      }
    }
    const prev = timerGetState();
    const resumeSecs = (prev && !prev.running) ? (prev.paused_seconds || 0) : 0;
    timerSetState({
      curriculum_id:   parseInt(currSel.value),
      curriculum_name: currSel.options[currSel.selectedIndex].text,
      item_id:         (itemSel && itemSel.value && itemSel.value !== '0') ? parseInt(itemSel.value) : null,
      start_ms:        Date.now() - resumeSecs * 1000,
      running:         true,
      paused_seconds:  0
    });
    clearInterval(tickInterval);
    tickInterval = setInterval(tick, 1000);
    tick(); applyUI(timerGetState());
  });

  if (pauseBtn) pauseBtn.addEventListener('click', () => {
    const state = timerGetState();
    if (!state || !state.running) return;
    clearInterval(tickInterval);
    timerSetState({ ...state, running: false, paused_seconds: timerElapsed() });
    applyUI(timerGetState());
  });

  if (stopBtn) stopBtn.addEventListener('click', async () => {
    const state = timerGetState();
    if (!state) return;
    const elapsed = timerElapsed();
    const duration_minutes = Math.max(1, Math.round(elapsed / 60));
    if (!confirm(`Log ${fmtTime(elapsed)} (~${duration_minutes} min) for ${state.curriculum_name}?`)) return;
    clearInterval(tickInterval);
    try {
      const res = await fetch('/api/sessions/stop', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          curriculum_id: state.curriculum_id,
          item_id: state.item_id || null,
          duration_minutes,
          note: noteEl ? noteEl.value : '',
          date: localDateString()
        })
      });
      if (res.ok) {
        timerSetState(null); applyUI(null);
        if (confirmEl) {
          confirmEl.textContent = `✓ Logged ${duration_minutes}m on ${state.curriculum_name}`;
          confirmEl.classList.remove('hidden');
          setTimeout(() => confirmEl.classList.add('hidden'), 5000);
        }
      } else { alert('Failed to save. Try logging manually.'); }
    } catch { alert('Network error. Try logging manually.'); }
  });
});
