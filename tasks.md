# AI Consulting Copilot — Frontend Build Tasks

## Project

React + Vite app, dark theme, 360px max-width (Google Meet side panel)
Design system: Syne + DM Mono fonts, #080c10 bg, #00c2ff accent

## Task List

- [ ] 
- [ ] 
- [ ] 
- [ ] 
- [ ] 
- [ ] 
- [ ] 
- [ ] 
- [ ] 
- [ ] 
- [ ] 
- [ ] 
- [ ] 
- [ ] 

```

---

## Step 2 — Opening Prompt to Antigravity Agent

Paste this as your **first message** to the Antigravity agent. Make sure Antigravity is in Planning mode so it creates an implementation plan and task list before jumping into code. 
```

I am building a React + Vite frontend for an AI consulting workshop platform
called "AI Consulting Copilot". This will eventually run as a Google Meet
add-on side panel, so max width is 360px. It must also work on mobile.

Read the tasks.md file in this project for the full build plan.

Before writing any code, produce an implementation plan covering:

1. Folder structure you will create
2. Which files you will build in which order
3. How state will be managed between phases
4. How the API calls will be structured

Then wait for my approval before starting.

```

---

## Step 3 — Design System Prompt (send after approving the plan)
```

Start with Task 1 and Task 2.

Create the Vite + React project structure and the global CSS design system.

Design system spec:

- Fonts: Syne (headings, 600/700/800) + DM Mono (body/mono, 300/400/500)
  Load both from Google Fonts in index.html
- CSS variables to define in :root:
  --bg: #080c10
  --bg-card: #0e1520
  --bg-hover: #141e2e
  --border: #1e2d42
  --accent: #00c2ff
  --accent-dim: #004d66
  --green: #00e5a0
  --amber: #ffb340
  --text: #e8f0f8
  --text-dim: #6a8099
  --font-head: 'Syne', sans-serif
  --font-mono: 'DM Mono', monospace
  --radius: 12px
  --radius-sm: 8px
  --transition: 0.18s ease
- Body background: #080c10 with top radial glow:
  radial-gradient(ellipse 60% 50% at 50% 0%, rgba(0,194,255,0.07), transparent 70%)
- Global utility classes:
  .badge — uppercase pill, 10px, accent border + blue bg tint
  .btn, .btn-primary, .btn-ghost — see spec
  .input — dark bg, accent focus border + glow
  .fade-up — opacity 0 + translateY(16px) → 1 + 0, 0.4s
  .pulse — opacity 1 → 0.4 → 1, 2s infinite
  .spinner — 16px spin circle, accent top border
- Shared .phase-shell layout:
  Full-height flex column with:
  .phase-header (logo left + phase indicator right with pulse dot)
  .step-track (horizontal numbered steps, active=accent, done=green)
  .live-bar (green dot + participant count text)
  .phase-body (scrollable, max-width 540px centered, padding 40px 28px)
  .phase-footer (sticky bottom, border-top, space-between)

After creating these files, open the browser preview and take a screenshot
to confirm fonts and colours are loading correctly.

```

---

## Step 4 — Screen by Screen Prompts

After design system is confirmed, send these **one at a time**:

**Home Screen:**
```

Build Task 3 and Task 4 — App.jsx phase router and App.css home screen.

Home screen layout:

- Full height dark bg with radial blue glow at top
- Logo: "◈ AI Copilot" in #00c2ff with glow filter
- Hero: badge "Workshop Platform" + H1 "AI Consulting Copilot" in gradient text
  (linear-gradient 135deg, #e8f0f8 30%, #00c2ff 100%), Syne 800, 56px
- Subtitle in --text-dim
- Two role cards side by side (min-width 220px):
  HOST card: icon "⬡", label, desc, "→" arrow
  PARTICIPANT card: icon "◎", label, desc, "→" arrow
  Cards: bg-card, border, radius 12px, hover = translateY(-2px) + blue glow
- Version text at bottom "v1.0 — AI Discovery Platform"

Phase state managed with useState. Phases: HOME, SETUP, ONBOARDING,
CONTEXT, PROBLEMS, ACTIVITY_A, ACTIVITY_B, ACTIVITY_C

Open browser, screenshot the result.

```

**Phase 0:**
```

Build Task 5 — Phase0_Setup.jsx

Host session configuration form using .phase-shell layout.
Phase indicator: "Phase 0 — Setup"
Badge: "Host Configuration"
H2: "Set up your workshop session"

Form fields:

- Your Name (text input)
- Company / Organisation (text input)
- Industry (select, 11 options: Technology & Software, Financial Services & Banking,
  Healthcare & Life Sciences, Retail & E-commerce, Manufacturing & Supply Chain,
  Professional Services & Consulting, Real Estate & Property, Education & Training,
  Logistics & Transportation, Media & Entertainment, Other)
- Two columns: Expected Participants (number) + Session Duration (select:
  60min Quick Discovery, 90min Standard Workshop, 120min Deep Dive)

Footer: "← Back" ghost + "Launch Session →" primary (disabled until all fields filled)

On submit: POST to ${VITE_API_URL}/session/create with JSON body.
Show spinner while loading. On success call onComplete(data).

Screenshot after building.

```

**Phase 1:**
```

Build Task 6 — Phase1_Onboarding.jsx

Two sub-screens:

SUB-SCREEN A (participants only): Session code entry

- Centered input, font-size 28px, letter-spacing 0.2em, text-align center, uppercase
- On submit: GET ${VITE_API_URL}/session/${code} to validate
- Shows error if not found

SUB-SCREEN B: Profile form (host and participant)

- Session code box at top: accent border card, code in Syne 800 36px #00c2ff,
  key-value rows for company/industry/duration
- Full Name input
- Two columns: Role (select, 9 options) + Department (text)
- Top challenge textarea (3 rows)
- AI Confidence Level: 5 vertical buttons
  Each: level number (Syne 800 20px) + label + description
  Levels: 1 Skeptical, 2 Curious, 3 Informed, 4 Practitioner, 5 Expert
  Selected: accent border + rgba(0,194,255,0.06) bg

On submit: POST to /participant/join

Screenshot after building.

```

**Phases 2 & 3, Activities A/B/C:**
```

Build Task 7 — Phase2_Context.jsx

3 steps + results, using step-track component.

STEP 1 — Objectives (2-column grid of 8 toggle cards):
  Each card: icon glyph + label bold + desc dim + checkmark
  Icons and labels:
    ◆ Revenue Growth | ◈ Operational Efficiency | ◎ Customer Experience
    ⬡ Product Innovation | ◉ Talent & Productivity | ▣ Risk & Compliance
    ◇ Data & Insights | ⬢ Scaling Operations
  Selected: accent border + blue tint bg

STEP 2 — Growth Priorities (8 full-width toggles):
  Each: circle "○"/"✓" + label. Selected: green border + green tint

STEP 3 — Challenges:
  Textarea 6 rows + character count below
  Summary card: selected objectives as blue .chip, growth as green .chip-green

RESULTS — Objective Map:
  2-4 insight cluster cards:
    Header: icon + theme + signals badge
    Summary text in --text-dim
    AI Potential strip: 2px left accent border + "AI Opportunity →" label
  Dominant theme box: green border, green label, Syne 800 18px value

On submit: POST /phase/context
WebSocket ws://[base]/ws/[code] — listen for objective_map event

Screenshot each step.

```

```

Build Tasks 8-12 — Phase3_Problems, ActivityA, ActivityB, ActivityC, phases.css

[Paste the full phases.css content from the existing project files]
[Paste Phase3_Problems.jsx]
[Paste ActivityA_DataAudit.jsx]
[Paste ActivityB_Confidence.jsx]
[Paste ActivityC_PromptEngineering.jsx]

Wire these into App.jsx flow after Phase2.
Test full navigation flow in browser.
Take screenshot of each screen.

```

---

## Step 5 — Final Wiring Prompt
```

Build Task 13 and 14 — API wiring and full flow test.

Create frontend/.env with:
  VITE_API_URL=http://localhost:8000

Update vite.config.js with these server headers:
  "ngrok-skip-browser-warning": "true"
  "X-Frame-Options": "ALLOWALL"

The API helper in App.jsx should:

- Read base URL from import.meta.env.VITE_API_URL
- Add headers: Content-Type: application/json + ngrok-skip-browser-warning: true
- Throw on non-OK responses

WebSocket base derived from API_BASE replacing http with ws.

Now test the complete flow end to end in the browser:
  HOME → Host → Phase 0 (fill form) → Phase 1 (fill profile)
  → Phase 2 (select objectives, submit) → Phase 3 (add problems)
  → Activity A → Activity B → Activity C

Take a screenshot at each phase transition and confirm no console errors.
