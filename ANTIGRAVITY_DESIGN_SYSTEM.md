
# AI Consulting Copilot — Light Theme

# Antigravity Build Prompts

---

## HOW TO USE

Send one PROMPT BLOCK at a time.
Wait for screenshot confirmation before the next block.

---

## ════════════════════════════════════

## PROMPT BLOCK 1 — FONTS + CSS VARIABLES

## ════════════════════════════════════

Open index.html and add these two lines inside `<head>`:

```html
<link rel="preconnect" href="https://fonts.googleapis.com" />
<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin />
<link href="https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600&family=DM+Mono:wght@400;500&display=swap" rel="stylesheet" />
```

Then open src/index.css and REPLACE the entire :root block with this:

```css
:root {
  /* BACKGROUNDS */
  --bg:           #ffffff;
  --bg-page:      #f5f6f8;
  --bg-card:      #ffffff;
  --bg-hover:     #f0f2f5;
  --bg-subtle:    #f8f9fb;

  /* BORDERS */
  --border:       #e4e7ed;
  --border-mid:   #d0d5de;
  --border-focus: #0066ff;

  /* TEXT — 3 tiers */
  --text:         #111318;
  --text-2:       #4a5568;
  --text-3:       #9aa3b2;
  --text-inv:     #ffffff;

  /* ACCENT */
  --accent:       #0066ff;
  --accent-light: #edf2ff;
  --accent-mid:   #c7d9ff;
  --accent-hover: #0052d9;
  --accent-glow:  rgba(0,102,255,0.10);

  /* SEMANTIC */
  --green:        #12a05a;
  --green-light:  #edfaf3;
  --green-border: rgba(18,160,90,0.25);
  --amber:        #c47a00;
  --amber-light:  #fef6e4;
  --amber-border: rgba(196,122,0,0.25);
  --red:          #d93535;
  --red-light:    #fff0f0;
  --red-border:   rgba(217,53,53,0.25);

  /* SHADOWS */
  --shadow:    0 1px 3px rgba(0,0,0,0.07), 0 0 0 0.5px rgba(0,0,0,0.06);
  --shadow-md: 0 4px 14px rgba(0,0,0,0.09), 0 0 0 0.5px rgba(0,0,0,0.06);
  --shadow-focus: 0 0 0 3px rgba(0,102,255,0.10);

  /* SHAPE */
  --r-sm: 6px;
  --r-md: 9px;
  --r-lg: 13px;
  --r-xl: 18px;

  /* FONTS */
  --font-h: 'Inter', sans-serif;
  --font-b: 'DM Mono', monospace;

  /* TRANSITION */
  --t: 0.15s ease;
}
```

Also update the body rule:

```css
html, body, #root {
  height: 100%;
  width: 100%;
}

body {
  background: var(--bg-page);
  color: var(--text);
  font-family: var(--font-h);
  font-size: 13px;
  line-height: 1.6;
  -webkit-font-smoothing: antialiased;
}

::-webkit-scrollbar { width: 4px; }
::-webkit-scrollbar-track { background: var(--bg-page); }
::-webkit-scrollbar-thumb { background: var(--border-mid); border-radius: 4px; }
```

Screenshot after saving — confirm white background with Inter font.

---

## ════════════════════════════════════

## PROMPT BLOCK 2 — UTILITY CLASSES

## ════════════════════════════════════

In src/index.css, replace ALL utility classes (badge, btn, input, card, etc.)
with these exact replacements:

```css
/* ── BADGE ── */
.badge {
  font-family: var(--font-h);
  font-size: 11px;
  font-weight: 500;
  padding: 3px 9px;
  border-radius: 20px;
  border: 1px solid;
  display: inline-block;
  line-height: 1.5;
}
.badge-default { border-color: var(--border-mid);    color: var(--text-2); background: var(--bg-subtle); }
.badge-accent  { border-color: var(--accent-mid);    color: var(--accent); background: var(--accent-light); }
.badge-green   { border-color: var(--green-border);  color: var(--green);  background: var(--green-light); }
.badge-amber   { border-color: var(--amber-border);  color: var(--amber);  background: var(--amber-light); }
.badge-red     { border-color: var(--red-border);    color: var(--red);    background: var(--red-light); }

/* ── BUTTONS ── */
.btn {
  font-family: var(--font-h);
  font-size: 13px;
  font-weight: 500;
  padding: 8px 18px;
  border-radius: var(--r-md);
  border: none;
  cursor: pointer;
  display: inline-flex;
  align-items: center;
  gap: 6px;
  letter-spacing: 0.01em;
  transition: all var(--t);
  line-height: 1;
  text-decoration: none;
}
.btn-primary {
  background: var(--accent);
  color: var(--text-inv);
}
.btn-primary:hover {
  background: var(--accent-hover);
  transform: translateY(-1px);
  box-shadow: 0 3px 12px rgba(0,102,255,0.3);
}
.btn-secondary {
  background: var(--bg-card);
  color: var(--text);
  border: 1px solid var(--border-mid);
  box-shadow: var(--shadow);
}
.btn-secondary:hover {
  border-color: var(--accent-mid);
  color: var(--accent);
  background: var(--accent-light);
}
.btn-ghost {
  background: transparent;
  color: var(--text-2);
  border: 1px solid var(--border);
}
.btn-ghost:hover {
  background: var(--bg-hover);
  color: var(--text);
  border-color: var(--border-mid);
}
.btn-danger {
  background: var(--red-light);
  color: var(--red);
  border: 1px solid var(--red-border);
}
.btn-danger:hover { background: #fde0e0; }
.btn-sm { padding: 5px 12px; font-size: 12px; border-radius: var(--r-sm); }
.btn:disabled {
  opacity: 0.4;
  cursor: not-allowed;
  transform: none !important;
  box-shadow: none !important;
}

/* ── INPUT ── */
.input {
  width: 100%;
  background: var(--bg-card);
  border: 1px solid var(--border);
  border-radius: var(--r-md);
  color: var(--text);
  font-family: var(--font-h);
  font-size: 13px;
  padding: 9px 13px;
  outline: none;
  transition: border-color var(--t), box-shadow var(--t);
}
.input:hover { border-color: var(--border-mid); }
.input:focus {
  border-color: var(--accent);
  box-shadow: var(--shadow-focus);
}
.input::placeholder { color: var(--text-3); }
.input-error { border-color: rgba(217,53,53,0.5) !important; }
.input-error:focus { box-shadow: 0 0 0 3px rgba(217,53,53,0.10) !important; }
.input-success { border-color: rgba(18,160,90,0.5) !important; }
textarea.input { min-height: 80px; resize: vertical; line-height: 1.6; }
select.input { appearance: none; cursor: pointer; }

.input-group { display: flex; flex-direction: column; gap: 5px; }
.input-group label {
  font-family: var(--font-h);
  font-size: 11px;
  font-weight: 500;
  color: var(--text-2);
  letter-spacing: 0.02em;
}
.input-hint    { font-size: 11px; color: var(--text-3); margin-top: 3px; }
.input-err-msg { font-size: 11px; color: var(--red); margin-top: 3px; }
.input-ok-msg  { font-size: 11px; color: var(--green); margin-top: 3px; }

/* ── CARD ── */
.card {
  background: var(--bg-card);
  border: 1px solid var(--border);
  border-radius: var(--r-lg);
  padding: 16px 18px;
  box-shadow: var(--shadow);
  transition: border-color var(--t), box-shadow var(--t);
}
.card:hover { border-color: var(--border-mid); }

.card-flat {
  background: var(--bg-subtle);
  border: 1px solid var(--border);
  border-radius: var(--r-lg);
  padding: 16px 18px;
}

.card-accent {
  background: var(--bg-card);
  border: 1px solid var(--border);
  border-left: 2.5px solid var(--accent);
  border-radius: var(--r-lg);
  padding: 14px 18px;
  transition: box-shadow var(--t);
}
.card-accent:hover {
  box-shadow: var(--shadow-focus);
  border-color: var(--accent-mid);
}

/* ── CHIP ── */
.chip {
  font-family: var(--font-h);
  font-size: 11px;
  font-weight: 500;
  padding: 3px 9px;
  border-radius: 20px;
  border: 1px solid var(--accent-mid);
  color: var(--accent);
  background: var(--accent-light);
  display: inline-block;
}
.chip-green { border-color: var(--green-border); color: var(--green); background: var(--green-light); }
.chip-dim   { border-color: var(--border); color: var(--text-3); background: transparent; }

/* ── DIVIDER ── */
.divider { border: none; border-top: 1px solid var(--border); }

/* ── SPINNER ── */
.spinner {
  width: 14px; height: 14px;
  border: 1.5px solid rgba(255,255,255,0.3);
  border-top-color: #fff;
  border-radius: 50%;
  animation: spin 0.7s linear infinite;
  display: inline-block; flex-shrink: 0;
}
.spinner-blue {
  border-color: var(--accent-mid);
  border-top-color: var(--accent);
}

/* ── LIVE DOT ── */
.live-dot {
  width: 6px; height: 6px; border-radius: 50%;
  background: var(--green); display: inline-block; flex-shrink: 0;
}

/* ── ERROR BANNER ── */
.error-banner {
  background: var(--red-light);
  border: 1px solid var(--red-border);
  border-radius: var(--r-md);
  padding: 10px 14px;
  color: var(--red);
  font-size: 12px;
}

/* ── GRIDS ── */
.grid-2 { display: grid; grid-template-columns: 1fr 1fr; gap: 12px; }
.grid-3 { display: grid; grid-template-columns: 1fr 1fr 1fr; gap: 10px; }
.grid-4 { display: grid; grid-template-columns: repeat(4,1fr); gap: 10px; }
@media (max-width: 400px) {
  .grid-2, .grid-3, .grid-4 { grid-template-columns: 1fr; }
}

/* ── ANIMATIONS ── */
@keyframes spin { to { transform: rotate(360deg); } }
@keyframes fadeUp {
  from { opacity: 0; transform: translateY(12px); }
  to   { opacity: 1; transform: translateY(0); }
}
.fade-up { animation: fadeUp 0.3s ease forwards; }
@keyframes pulse {
  0%, 100% { opacity: 1; }
  50%       { opacity: 0.35; }
}
.pulse { animation: pulse 2s ease infinite; }
@keyframes thinking {
  0%, 100% { opacity: 0.25; transform: scale(0.8); }
  50%       { opacity: 1; transform: scale(1); }
}
```

Screenshot after saving.

---

## ════════════════════════════════════

## PROMPT BLOCK 3 — PHASE SHELL (App.css)

## ════════════════════════════════════

Replace the ENTIRE contents of src/App.css with this:

```css
/* ══ HOME SCREEN ══ */
.app-home {
  min-height: 100vh;
  display: flex; flex-direction: column;
  align-items: center; justify-content: center;
  padding: 40px 24px; gap: 36px;
  background: var(--bg-page);
}

.home-logo {
  display: flex; align-items: center; gap: 9px;
  font-family: var(--font-h); font-size: 15px;
  font-weight: 600; color: var(--accent);
}
.logo-icon { font-size: 20px; }

.home-hero {
  text-align: center;
  display: flex; flex-direction: column;
  align-items: center; gap: 12px;
}
.home-title {
  font-family: var(--font-h);
  font-size: clamp(30px, 8vw, 48px);
  font-weight: 600; line-height: 1.15;
  letter-spacing: -0.025em; color: var(--text);
}
.home-sub { color: var(--text-2); font-size: 14px; line-height: 1.7; }

.home-cards {
  display: flex; gap: 12px; flex-wrap: wrap;
  justify-content: center; width: 100%; max-width: 560px;
}

.role-card {
  flex: 1; min-width: 200px;
  background: var(--bg-card);
  border: 1px solid var(--border);
  border-radius: var(--r-lg);
  padding: 20px 18px;
  cursor: pointer; text-align: left;
  display: flex; flex-direction: column; gap: 7px;
  transition: all var(--t);
  box-shadow: var(--shadow);
}
.role-card:hover {
  border-color: var(--accent-mid);
  box-shadow: var(--shadow-md);
  transform: translateY(-1px);
}
.role-icon  { font-size: 20px; color: var(--accent); display: block; }
.role-label { font-family: var(--font-h); font-size: 14px; font-weight: 600; color: var(--text); display: block; }
.role-desc  { font-size: 12px; color: var(--text-2); line-height: 1.5; display: block; }
.role-arrow { font-size: 16px; color: var(--accent); margin-top: 4px; display: block; transition: transform var(--t); }
.role-card:hover .role-arrow { transform: translateX(3px); }

.home-version { font-size: 11px; color: var(--text-3); letter-spacing: 0.04em; }

/* ══ PHASE SHELL ══ */
.phase-shell {
  min-height: 100vh;
  display: flex; flex-direction: column;
  background: var(--bg-page);
}

.phase-header {
  display: flex; align-items: center; justify-content: space-between;
  padding: 14px 22px;
  border-bottom: 1px solid var(--border);
  background: var(--bg-card);
  flex-shrink: 0;
}
.phase-logo {
  display: flex; align-items: center; gap: 7px;
  font-family: var(--font-h); font-size: 13px;
  font-weight: 600; color: var(--accent);
}
.phase-indicator { display: flex; align-items: center; gap: 7px; }
.phase-ind-dot   { width: 6px; height: 6px; border-radius: 50%; background: var(--accent); }
.phase-ind-label { font-size: 10px; color: var(--text-3); letter-spacing: 0.08em; text-transform: uppercase; font-weight: 600; }

.step-track {
  display: flex; align-items: center;
  padding: 0 22px;
  background: var(--bg-card);
  border-bottom: 1px solid var(--border);
  flex-shrink: 0; overflow-x: auto;
}
.step-item {
  display: flex; align-items: center; gap: 7px;
  padding: 11px 14px 11px 0;
  opacity: 0.3; transition: opacity var(--t);
  position: relative; white-space: nowrap;
}
.step-item:not(:last-child)::after {
  content: '→'; position: absolute; right: 1px;
  color: var(--border-mid); font-size: 11px;
}
.step-item.active { opacity: 1; }
.step-item.done   { opacity: 0.6; }
.step-dot {
  width: 20px; height: 20px; border-radius: 50%;
  border: 1px solid var(--border-mid);
  display: flex; align-items: center; justify-content: center;
  font-size: 10px; font-family: var(--font-h); font-weight: 600;
  color: var(--text-3); flex-shrink: 0; transition: all var(--t);
}
.step-item.active .step-dot {
  border-color: var(--accent); color: var(--accent);
  background: var(--accent-light);
}
.step-item.done .step-dot {
  border-color: var(--green); color: var(--green);
  background: var(--green-light);
}
.step-name {
  font-size: 11px; font-family: var(--font-h);
  font-weight: 500; color: var(--text-2);
}

.live-bar {
  display: flex; align-items: center; gap: 7px;
  padding: 6px 22px;
  background: var(--bg-card);
  border-bottom: 1px solid var(--border);
  flex-shrink: 0;
}
.live-text { font-size: 11px; color: var(--text-3); }

.phase-body {
  flex: 1; overflow-y: auto;
  padding: 32px 22px;
  max-width: 520px; width: 100%; margin: 0 auto;
  display: flex; flex-direction: column; gap: 24px;
}

.phase-footer {
  display: flex; justify-content: space-between; align-items: center;
  padding: 14px 22px;
  border-top: 1px solid var(--border);
  background: var(--bg-card);
  flex-shrink: 0;
}

/* ══ CONTENT BLOCKS ══ */
.phase-title-block { display: flex; flex-direction: column; gap: 8px; }
.phase-title {
  font-family: var(--font-h); font-size: 22px;
  font-weight: 600; line-height: 1.25;
  letter-spacing: -0.018em; color: var(--text);
}
.phase-desc { color: var(--text-2); font-size: 12px; line-height: 1.7; }
.phase-form { display: flex; flex-direction: column; gap: 16px; }
.form-two-col { display: grid; grid-template-columns: 1fr 1fr; gap: 12px; }
@media (max-width: 400px) { .form-two-col { grid-template-columns: 1fr; } }

/* ══ SESSION CODE BOX ══ */
.session-code-box {
  background: var(--bg-card);
  border: 1px solid var(--accent-mid);
  border-radius: var(--r-lg); padding: 16px 20px;
  display: flex; flex-direction: column; gap: 7px;
}
.session-code-label { font-size: 10px; text-transform: uppercase; letter-spacing: 0.1em; color: var(--text-3); font-weight: 600; }
.session-code-value {
  font-family: var(--font-h); font-size: 30px;
  font-weight: 600; color: var(--accent); letter-spacing: 0.1em;
}
.session-code-hint { font-size: 11px; color: var(--text-3); }

/* ══ INFO ROWS ══ */
.info-card { background: var(--bg-subtle); border: 1px solid var(--border); border-radius: var(--r-md); padding: 12px 16px; display: flex; flex-direction: column; gap: 8px; }
.info-row  { display: flex; justify-content: space-between; align-items: center; font-size: 12px; }
.info-key  { color: var(--text-3); }
.info-val  { color: var(--text); font-weight: 500; }

/* ══ INSIGHT CLUSTER CARD ══ */
.insight-cluster {
  background: var(--bg-card); border: 1px solid var(--border);
  border-radius: var(--r-lg); padding: 14px 16px;
  display: flex; flex-direction: column; gap: 9px;
  box-shadow: var(--shadow); transition: border-color var(--t);
}
.insight-cluster:hover { border-color: var(--border-mid); }
.cluster-header { display: flex; align-items: center; gap: 9px; flex-wrap: wrap; }
.cluster-icon   { font-size: 16px; color: var(--accent); }
.cluster-theme  { font-family: var(--font-h); font-size: 13px; font-weight: 600; color: var(--text); flex: 1; }
.cluster-summary { font-size: 12px; color: var(--text-2); line-height: 1.65; }
.cluster-depts  { display: flex; flex-wrap: wrap; gap: 5px; }

.cluster-potential {
  display: flex; gap: 8px; align-items: flex-start;
  background: var(--accent-light);
  border-left: 2px solid var(--accent);
  border-radius: 0 6px 6px 0;
  padding: 8px 12px;
}
.potential-label {
  font-size: 10px; text-transform: uppercase; letter-spacing: 0.08em;
  color: var(--accent); white-space: nowrap; padding-top: 2px; font-weight: 600;
}
.potential-text { font-size: 12px; color: var(--text-2); line-height: 1.55; }

/* ══ DOMINANT THEME BOX ══ */
.dominant-theme-box {
  background: var(--green-light); border: 1px solid var(--green-border);
  border-radius: var(--r-lg); padding: 14px 18px;
  display: flex; flex-direction: column; gap: 5px;
}
.dominant-label { font-size: 10px; text-transform: uppercase; letter-spacing: 0.08em; color: var(--green); font-weight: 600; }
.dominant-value { font-family: var(--font-h); font-size: 15px; font-weight: 600; color: var(--text); }

/* ══ AI THINKING ══ */
.ai-thinking {
  display: flex; flex-direction: column; align-items: center;
  gap: 12px; padding: 40px 24px; text-align: center;
}
.thinking-dots { display: flex; gap: 6px; }
.thinking-dot {
  width: 6px; height: 6px; border-radius: 50%; background: var(--accent);
  animation: thinking 1.4s ease infinite;
}
.thinking-dot:nth-child(2) { animation-delay: 0.2s; }
.thinking-dot:nth-child(3) { animation-delay: 0.4s; }
.thinking-label { font-family: var(--font-h); font-size: 13px; font-weight: 600; color: var(--text); }
.thinking-sub   { font-size: 11px; color: var(--text-3); }

/* ══ WAITING STATE ══ */
.waiting-state { display: flex; flex-direction: column; align-items: center; gap: 12px; padding: 40px 0; text-align: center; }
.waiting-icon  { font-size: 30px; color: var(--accent); }
.waiting-label { font-family: var(--font-h); font-size: 13px; font-weight: 600; color: var(--text); }
.waiting-sub   { font-size: 12px; color: var(--text-2); }
```

Screenshot home screen after saving.

---

## ════════════════════════════════════

## PROMPT BLOCK 4 — COMPONENT STYLES (phases.css)

## ════════════════════════════════════

Replace the ENTIRE contents of src/components/phases.css with this:

```css
/* ══ PHASE 2 — OBJECTIVES ══ */
.objective-grid { display: grid; grid-template-columns: 1fr 1fr; gap: 8px; }
@media (max-width: 380px) { .objective-grid { grid-template-columns: 1fr; } }

.objective-card {
  background: var(--bg-card); border: 1px solid var(--border);
  border-radius: var(--r-md); padding: 12px 14px;
  text-align: left; cursor: pointer; transition: all var(--t);
  display: grid; grid-template-columns: 22px 1fr 14px;
  grid-template-rows: auto auto; column-gap: 9px;
}
.objective-card:hover { border-color: var(--border-mid); background: var(--bg-hover); }
.objective-card.selected {
  border-color: var(--accent); background: var(--accent-light);
  box-shadow: var(--shadow-focus);
}
.obj-icon  { grid-row: 1/3; align-self: center; font-size: 16px; color: var(--accent); }
.obj-label { font-family: var(--font-h); font-size: 12px; font-weight: 600; color: var(--text); display: block; }
.obj-desc  { font-size: 11px; color: var(--text-3); display: block; line-height: 1.4; }
.obj-check { grid-row: 1; color: var(--accent); font-size: 11px; align-self: start; margin-top: 2px; }
.selected-count { font-size: 11px; color: var(--text-3); text-align: right; margin-top: 6px; }

/* ══ PHASE 2 — GROWTH ══ */
.growth-list { display: flex; flex-direction: column; gap: 6px; }
.growth-item {
  display: flex; align-items: center; gap: 12px;
  background: var(--bg-card); border: 1px solid var(--border);
  border-radius: var(--r-md); padding: 11px 16px;
  text-align: left; cursor: pointer; transition: all var(--t);
}
.growth-item:hover { border-color: var(--border-mid); background: var(--bg-hover); }
.growth-item.selected {
  border-color: var(--green); background: var(--green-light);
}
.growth-check { font-size: 14px; color: var(--text-3); width: 16px; flex-shrink: 0; transition: color var(--t); }
.growth-item.selected .growth-check { color: var(--green); }
.growth-label { font-size: 13px; color: var(--text); font-family: var(--font-h); font-weight: 500; }

/* ══ PHASE 2 — SUMMARY ══ */
.summary-card {
  background: var(--bg-subtle); border: 1px solid var(--border);
  border-radius: var(--r-lg); padding: 14px 16px;
}
.summary-title { font-size: 10px; text-transform: uppercase; letter-spacing: 0.08em; color: var(--text-3); font-weight: 600; margin-bottom: 8px; }
.summary-chips { display: flex; flex-wrap: wrap; gap: 5px; }

/* ══ PHASE 3 — PROBLEMS ══ */
.problems-list { display: flex; flex-direction: column; gap: 14px; }
.problem-card {
  background: var(--bg-card); border: 1px solid var(--border);
  border-radius: var(--r-lg); padding: 16px 18px;
  display: flex; flex-direction: column; gap: 12px;
  box-shadow: var(--shadow);
}
.problem-card-header { display: flex; align-items: center; justify-content: space-between; }
.problem-num { font-size: 10px; text-transform: uppercase; letter-spacing: 0.08em; color: var(--accent); font-weight: 600; }
.remove-btn {
  background: none; border: 1px solid var(--border); border-radius: var(--r-sm);
  color: var(--text-3); cursor: pointer; padding: 2px 8px; font-size: 11px;
  transition: all var(--t); font-family: var(--font-h);
}
.remove-btn:hover { border-color: var(--red-border); color: var(--red); background: var(--red-light); }

.tag-row   { display: flex; flex-direction: column; gap: 7px; }
.tag-label { font-size: 11px; color: var(--text-3); font-weight: 500; }
.tag-group { display: flex; flex-wrap: wrap; gap: 5px; }
.tag-btn {
  font-size: 11px; padding: 3px 10px; border-radius: 20px;
  border: 1px solid var(--border); color: var(--text-2);
  background: var(--bg-subtle); cursor: pointer;
  font-family: var(--font-h); font-weight: 500;
  transition: all var(--t);
}
.tag-btn:hover  { border-color: var(--accent-mid); color: var(--accent); }
.tag-btn.selected { border-color: var(--accent); color: var(--accent); background: var(--accent-light); }

.severity-row  { display: flex; flex-direction: column; gap: 7px; }
.severity-track { display: flex; align-items: center; gap: 6px; }
.severity-btn {
  width: 30px; height: 30px; border-radius: var(--r-sm);
  border: 1px solid var(--border); background: var(--bg-subtle);
  color: var(--text-2); cursor: pointer;
  font-family: var(--font-h); font-size: 12px; font-weight: 600;
  transition: all var(--t);
}
.severity-btn:hover  { border-color: var(--border-mid); }
.severity-btn.selected { background: var(--accent-light); border-color: var(--accent); color: var(--accent); }
.severity-desc { font-size: 11px; margin-left: 4px; color: var(--text-3); transition: color var(--t); }

.add-problem-btn {
  width: 100%; padding: 12px;
  background: transparent; border: 1px dashed var(--border-mid);
  border-radius: var(--r-lg); color: var(--text-3);
  cursor: pointer; font-family: var(--font-h); font-size: 12px; font-weight: 500;
  transition: all var(--t); margin-top: 2px;
}
.add-problem-btn:hover { border-color: var(--accent); color: var(--accent); background: var(--accent-light); }

.severity-bar-row   { display: flex; align-items: center; gap: 9px; margin-top: 4px; }
.severity-bar-label { font-size: 10px; color: var(--text-3); text-transform: uppercase; letter-spacing: 0.08em; white-space: nowrap; font-weight: 600; }
.severity-bar-track { flex: 1; height: 4px; background: var(--border); border-radius: 2px; }
.severity-bar-fill  { height: 100%; background: var(--accent); border-radius: 2px; transition: width 0.4s ease; }
.severity-bar-val   { font-size: 11px; color: var(--accent); font-family: var(--font-h); font-weight: 600; white-space: nowrap; }

.live-problems-box { background: var(--bg-subtle); border: 1px solid var(--border); border-radius: var(--r-md); padding: 12px 16px; }
.live-problems-title { font-size: 12px; color: var(--text-2); display: flex; align-items: center; gap: 7px; }

/* ══ ACTIVITY A — DATA AUDIT ══ */
.dataset-grid { display: flex; flex-direction: column; gap: 6px; }
.dataset-card {
  display: flex; align-items: center; gap: 12px;
  background: var(--bg-card); border: 1px solid var(--border);
  border-radius: var(--r-md); padding: 11px 16px;
  text-align: left; cursor: pointer; transition: all var(--t);
}
.dataset-card:hover   { border-color: var(--border-mid); background: var(--bg-hover); }
.dataset-card.selected{ border-color: var(--accent); background: var(--accent-light); box-shadow: var(--shadow-focus); }
.ds-check { font-size: 14px; color: var(--text-3); width: 16px; flex-shrink: 0; transition: color var(--t); }
.dataset-card.selected .ds-check { color: var(--accent); }
.ds-info  { display: flex; flex-direction: column; gap: 2px; }
.ds-label { font-family: var(--font-h); font-size: 13px; font-weight: 500; color: var(--text); }
.ds-example { font-size: 11px; color: var(--text-3); }

.ds-progress-row { display: flex; flex-wrap: wrap; gap: 6px; margin-bottom: 6px; }
.ds-pill {
  font-size: 11px; padding: 4px 11px; border-radius: 20px;
  border: 1px solid var(--border); color: var(--text-2);
  background: var(--bg-subtle); cursor: pointer;
  font-family: var(--font-h); font-weight: 500; transition: all var(--t);
}
.ds-pill.active { border-color: var(--accent); color: var(--accent); background: var(--accent-light); }
.ds-pill.done   { border-color: var(--green);  color: var(--green);  background: var(--green-light); }

.dimension-list { display: flex; flex-direction: column; gap: 12px; }
.dimension-card {
  background: var(--bg-card); border: 1px solid var(--border);
  border-radius: var(--r-lg); padding: 14px 16px;
  display: flex; flex-direction: column; gap: 10px;
  box-shadow: var(--shadow);
}
.dim-header { display: flex; justify-content: space-between; align-items: baseline; }
.dim-label  { font-family: var(--font-h); font-size: 13px; font-weight: 600; color: var(--text); }
.dim-desc   { font-size: 11px; color: var(--text-3); }
.dim-options{ display: grid; grid-template-columns: 1fr 1fr; gap: 6px; }
@media (max-width: 400px) { .dim-options { grid-template-columns: 1fr; } }
.dim-option {
  display: flex; align-items: center; gap: 9px;
  background: var(--bg-subtle); border: 1px solid var(--border);
  border-radius: var(--r-sm); padding: 9px 12px;
  text-align: left; cursor: pointer; transition: all var(--t);
}
.dim-option:hover    { border-color: var(--border-mid); background: var(--bg-hover); }
.dim-option.selected { border-color: var(--accent); background: var(--accent-light); box-shadow: var(--shadow-focus); }
.dim-opt-num {
  width: 18px; height: 18px; border-radius: 50%;
  border: 1px solid var(--border-mid);
  font-size: 10px; font-weight: 600; display: flex; align-items: center; justify-content: center;
  flex-shrink: 0; color: var(--text-3); font-family: var(--font-h); transition: all var(--t);
}
.dim-option.selected .dim-opt-num { border-color: var(--accent); color: var(--accent); background: var(--accent-light); }
.dim-opt-text { font-size: 12px; color: var(--text-2); line-height: 1.4; }

.readiness-map { display: flex; flex-direction: column; gap: 11px; }
.readiness-row { display: flex; align-items: center; gap: 11px; }
.readiness-ds-name { font-size: 12px; font-family: var(--font-h); font-weight: 500; color: var(--text); min-width: 130px; }
.readiness-bar-track { flex: 1; height: 6px; background: var(--border); border-radius: 3px; }
.readiness-bar-fill  { height: 100%; border-radius: 3px; transition: width 0.6s ease; }
.readiness-badge {
  font-size: 10px; padding: 3px 9px; border-radius: 20px; border: 1px solid;
  font-family: var(--font-h); font-weight: 500; white-space: nowrap;
}

/* ══ ACTIVITY B — CONFIDENCE ══ */
.confidence-spectrum { display: flex; flex-direction: column; gap: 10px; }
.spectrum-label { font-size: 11px; text-transform: uppercase; letter-spacing: 0.08em; color: var(--text-3); font-weight: 600; }
.spectrum-track { display: flex; gap: 6px; flex-wrap: wrap; }
.spectrum-btn {
  flex: 1; min-width: 70px;
  background: var(--bg-card); border: 1px solid var(--border);
  border-radius: var(--r-md); padding: 12px 8px;
  cursor: pointer; transition: all var(--t);
  display: flex; flex-direction: column; align-items: center; gap: 5px;
  box-shadow: var(--shadow);
}
.spectrum-btn:hover { border-color: var(--border-mid); background: var(--bg-hover); }
.spec-num   { font-family: var(--font-h); font-size: 20px; font-weight: 600; color: var(--text-3); transition: color var(--t); }
.spec-label { font-size: 10px; font-weight: 600; text-transform: uppercase; letter-spacing: 0.05em; color: var(--text-3); text-align: center; }
.spectrum-desc {
  padding: 10px 14px; border-left: 2px solid var(--accent);
  background: var(--accent-light); border-radius: 0 6px 6px 0;
  font-size: 12px; color: var(--text-2); line-height: 1.5;
}

.concerns-section { display: flex; flex-direction: column; gap: 8px; }
.section-label { font-size: 11px; text-transform: uppercase; letter-spacing: 0.08em; color: var(--text-3); font-weight: 600; }
.concerns-grid { display: grid; grid-template-columns: 1fr 1fr; gap: 6px; }
@media (max-width: 400px) { .concerns-grid { grid-template-columns: 1fr; } }
.concern-card {
  background: var(--bg-card); border: 1px solid var(--border);
  border-radius: var(--r-md); padding: 11px 13px;
  text-align: left; cursor: pointer; transition: all var(--t);
  display: flex; flex-direction: column; gap: 3px;
  box-shadow: var(--shadow);
}
.concern-card:hover   { border-color: var(--border-mid); background: var(--bg-hover); }
.concern-card.selected{ border-color: var(--amber-border); background: var(--amber-light); }
.concern-icon  { font-size: 14px; color: var(--text-3); }
.concern-card.selected .concern-icon { color: var(--amber); }
.concern-label { font-family: var(--font-h); font-size: 12px; font-weight: 600; color: var(--text); }
.concern-desc  { font-size: 11px; color: var(--text-3); line-height: 1.4; }

.confidence-dist { background: var(--bg-card); border: 1px solid var(--border); border-radius: var(--r-lg); padding: 16px 18px; box-shadow: var(--shadow); }
.dist-title  { font-family: var(--font-h); font-size: 13px; font-weight: 600; color: var(--text); margin-bottom: 12px; }
.dist-bars   { display: flex; flex-direction: column; gap: 8px; }
.dist-row    { display: flex; align-items: center; gap: 9px; }
.dist-label  { font-size: 11px; font-weight: 500; min-width: 88px; }
.dist-bar-track { flex: 1; height: 5px; background: var(--border); border-radius: 3px; }
.dist-bar-fill  { height: 100%; border-radius: 3px; transition: width 0.6s ease; }
.dist-count  { font-size: 12px; font-family: var(--font-h); font-weight: 600; color: var(--text-2); min-width: 14px; text-align: right; }

.tone-adaptation-box {
  display: flex; gap: 12px; align-items: flex-start;
  background: var(--green-light); border: 1px solid var(--green-border);
  border-radius: var(--r-lg); padding: 14px 16px;
}
.tone-icon  { font-size: 18px; color: var(--green); flex-shrink: 0; }
.tone-title { font-family: var(--font-h); font-size: 13px; font-weight: 600; color: var(--green); margin-bottom: 3px; }
.tone-desc  { font-size: 12px; color: var(--text-2); line-height: 1.6; }

/* ══ ACTIVITY C — PROMPT ENGINEERING ══ */
.prompt-example-box {
  background: var(--accent-light);
  border: 1px solid var(--accent-mid);
  border-radius: var(--r-md);
  padding: 12px 16px;
  display: flex; flex-direction: column; gap: 5px;
}
.example-label { font-size: 10px; text-transform: uppercase; letter-spacing: 0.08em; color: var(--accent); font-weight: 600; }
.example-text  { font-size: 12px; color: var(--text-2); line-height: 1.7; font-style: italic; }

.score-grid { display: grid; grid-template-columns: 1fr 1fr; gap: 10px; }
@media (max-width: 400px) { .score-grid { grid-template-columns: 1fr; } }
.score-card {
  background: var(--bg-card); border: 1px solid var(--border);
  border-radius: var(--r-md); padding: 12px 14px;
  display: flex; flex-direction: column; gap: 7px;
  box-shadow: var(--shadow);
}
.score-header    { display: flex; justify-content: space-between; align-items: center; }
.score-dim-label { font-family: var(--font-h); font-size: 12px; font-weight: 600; color: var(--text); }
.score-val       { font-family: var(--font-h); font-size: 15px; font-weight: 600; }
.score-bar-track { height: 4px; background: var(--border); border-radius: 2px; }
.score-bar-fill  { height: 100%; border-radius: 2px; transition: width 0.5s ease; }
.score-dim-desc  { font-size: 11px; color: var(--text-3); }
.score-feedback  { font-size: 11px; color: var(--text-2); background: var(--bg-subtle); border-radius: var(--r-sm); padding: 5px 9px; line-height: 1.5; }

.total-score-box {
  display: flex; justify-content: space-between; align-items: center;
  background: var(--bg-card); border: 1px solid var(--border);
  border-radius: var(--r-md); padding: 14px 18px; box-shadow: var(--shadow);
}
.total-score-label { font-family: var(--font-h); font-size: 13px; font-weight: 600; color: var(--text); }
.total-score-val   { font-family: var(--font-h); font-size: 26px; font-weight: 600; }

.prompt-compare { display: flex; gap: 10px; align-items: flex-start; flex-wrap: wrap; }
.compare-col    { flex: 1; min-width: 160px; display: flex; flex-direction: column; gap: 6px; }
.compare-label  { font-size: 10px; text-transform: uppercase; letter-spacing: 0.08em; color: var(--text-3); font-weight: 600; }
.compare-box    { font-size: 12px; line-height: 1.65; padding: 12px 14px; border-radius: var(--r-md); border: 1px solid var(--border); color: var(--text-2); background: var(--bg-subtle); }
.compare-box.improved { border-color: var(--green-border); background: var(--green-light); color: var(--text); }
.compare-arrow  { font-size: 18px; color: var(--text-3); align-self: center; flex-shrink: 0; padding-top: 22px; }

.sim-prompt-box {
  background: var(--bg-subtle); border: 1px solid var(--border);
  border-radius: var(--r-md); padding: 12px 16px;
  display: flex; flex-direction: column; gap: 5px;
}
.sim-prompt-label { font-size: 10px; text-transform: uppercase; letter-spacing: 0.08em; color: var(--text-3); font-weight: 600; }
.sim-prompt-text  { font-size: 12px; color: var(--text-2); line-height: 1.6; }

.sim-output-box {
  background: var(--bg-card); border: 1px solid var(--accent-mid);
  border-radius: var(--r-lg); overflow: hidden; box-shadow: var(--shadow);
}
.sim-output-header {
  display: flex; align-items: center; gap: 9px;
  background: var(--accent-light); padding: 10px 16px;
  border-bottom: 1px solid var(--accent-mid);
}
.sim-output-icon  { color: var(--accent); font-size: 14px; }
.sim-output-label { font-family: var(--font-h); font-size: 12px; font-weight: 600; color: var(--accent); }
.sim-output-content {
  padding: 16px; font-size: 12px; color: var(--text);
  line-height: 1.8; white-space: pre-wrap; font-family: var(--font-b);
  max-height: 300px; overflow-y: auto;
}

.sim-insight-box {
  display: flex; gap: 9px; align-items: flex-start;
  background: var(--green-light); border: 1px solid var(--green-border);
  border-radius: var(--r-md); padding: 10px 14px;
}
.sim-insight-label { font-size: 10px; text-transform: uppercase; letter-spacing: 0.08em; color: var(--green); white-space: nowrap; padding-top: 2px; font-weight: 600; }
.sim-insight-text  { font-size: 12px; color: var(--text-2); line-height: 1.6; }
```

Screenshot after saving — open Phase 2 and verify objective cards look clean.

---

## ════════════════════════════════════

## PROMPT BLOCK 5 — VERIFY ALL SCREENS

## ════════════════════════════════════

Run the app and navigate through every screen.
Take a screenshot of each and confirm:

1. HOME: White background, Inter font, clean role cards with subtle shadow
2. PHASE 0: Clean form on white card, grey page background visible
3. PHASE 1: Session code in blue Inter 600, profile form clean
4. PHASE 2 Step 1: Objective cards — white default, blue-tinted selected
5. PHASE 2 Step 3: Summary card with chips on grey bg
6. PHASE 2 Results: Insight cluster cards white with blue left accent
7. PHASE 3: Problem cards clean white, tag pills minimal
8. ACTIVITY A: Dataset toggles, dimension 2x2 grid clean
9. ACTIVITY B: Confidence spectrum buttons, distribution bars coloured
10. ACTIVITY C: Score grid cards, green comparison box, blue output box

For every screen confirm:

* Background is --bg-page (#f5f6f8) grey, cards are white
* All borders are 1px solid #e4e7ed
* Selected state uses blue border + shadow-focus ring
* Buttons: primary is solid blue, secondary has white bg + border
* No dark backgrounds anywhere except code snippets
* Fonts are Inter (headings) + DM Mono (code/mono only)

Fix any inconsistencies found before confirming done.

---

## ════════════════════════════════════

## CRITICAL RULES FOR LIGHT THEME

## ════════════════════════════════════

1. Page bg is #f5f6f8 — NOT pure white. Cards are #ffffff.
   This creates depth without shadows on every element.
2. Borders are 1px — NOT 0.5px. On white, 0.5px is invisible
   on most monitors.
3. Selected state = blue border (#0066ff) + 3px ring at 10% opacity.
   Never just a background tint alone.
4. Blue accent ONLY for interactive elements and AI output cards.
   Never use blue as a decorative colour.
5. --text-3 (#9aa3b2) is for labels/metadata ONLY.
   Body copy minimum is --text-2 (#4a5568).
6. All transitions 0.15s ease. Nothing slower.
7. Input background is --bg-card (#ffffff), not --bg-subtle.
   The white input on a grey page creates the natural affordance.
8. Card shadow: 0 1px 3px rgba(0,0,0,0.07) + 0.5px border trick.
   This is what makes cards look "lifted" not "floating".
