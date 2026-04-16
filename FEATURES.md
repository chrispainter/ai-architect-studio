# AI Architect Studio — Features & Requirements

Living specification of what the product does, what shipped when, and what's planned next.

**Product vision:** A web application where a product manager enters a product brief and six specialized AI agents collaborate to produce a complete set of PM deliverables — PRDs, architecture decision records, user stories, UX designs, infrastructure plans, and security audits — that PMs would otherwise spend weeks producing by hand.

**Target user:** Product managers (IC through Director) who need to move from idea to shippable plan fast. Secondary users: founders drafting technical briefs for contractors; engineering leads pressure-testing requirements.

---

## Status Legend
- ✅ Shipped (live in production)
- 🚧 In progress
- 📋 Planned (on roadmap)
- 💡 Backlog (not yet committed)

---

## Phase 1 — Foundation ✅
*Shipped 2026-04-15. Live at https://product.intakeengine.ai*

The infrastructure layer that all subsequent phases build on: authentication, multi-tenancy, real-time updates, and production deployment.

### F1.1 — User Authentication ✅
**As a** product manager
**I want to** create an account and log in with email + password
**So that** my projects are private and persist across sessions

**Acceptance criteria:**
- User can register with email, password, and full name
- Duplicate email registration returns 400 with clear error
- Login returns JWT bearer token valid for 60 minutes
- Invalid credentials return 401 without leaking which field is wrong
- `GET /api/v1/auth/me` returns current user when bearer token is valid
- Passwords stored as bcrypt hashes (cost factor 12)
- JWT `sub` claim is stringified user id (JWT spec compliance)

**How it works:**
- `python-jose` + `passlib[bcrypt]` on the backend (`backend/auth.py`)
- React `AuthContext` manages token in localStorage and attaches it via axios interceptor
- `ProtectedRoute` component redirects unauthenticated users to `/login`

---

### F1.2 — Project Ownership & Isolation ✅
**As a** product manager
**I want** every project I create to belong only to me
**So that** my work is private from other users of the system

**Acceptance criteria:**
- Every `projects` row carries a `user_id` FK
- `GET /api/v1/projects/` returns only the authenticated user's projects
- `GET/PUT/DELETE /api/v1/projects/{id}` returns 404 if the project belongs to another user (not 403 — prevents enumeration)
- All downstream endpoints (requirements, knowledge base, outputs, runs) inherit the ownership check

**How it works:** Every CRUD function in `backend/crud.py` takes `user_id` and filters accordingly.

---

### F1.3 — Project Lifecycle (CRUD) ✅
**As a** product manager
**I want to** create, view, update, and delete projects
**So that** I can manage a portfolio of product ideas

**Acceptance criteria:**
- Create: title (required), description, optional GitHub URL
- Read: full project with requirements, knowledge base, agent outputs, and run history
- Update: title/description/status/github_url
- Delete: cascade deletes requirements, KB, outputs, runs

---

### F1.4 — Requirements & Knowledge Base ✅
**As a** product manager
**I want to** attach structured requirements and per-agent guidelines to a project
**So that** each AI agent produces output aligned with my specific standards

**Acceptance criteria:**
- Multiple `requirements` (free-text) per project
- Single `knowledge_base` per project with 6 fields (one per agent): pm_guidelines, architect_guidelines, systems_guidelines, ai_guidelines, ux_guidelines, security_standards
- Knowledge base content is injected into each agent's backstory at run time

---

### F1.5 — Multi-Agent Crew Execution ✅
**As a** product manager
**I want to** kick off a run where six AI agents collaborate on my project
**So that** I get a complete set of deliverables without writing them myself

**Acceptance criteria:**
- `POST /api/v1/projects/{id}/runs` creates a `CrewRun` row with status=queued and queues a background task
- Only one active run (queued or running) per project at a time (400 if duplicate)
- Run transitions: queued → running → completed (or failed with error_message)
- Six agents execute sequentially: PM → Architect → Systems Engineer → AI Specialist → UX Designer → CISO
- Each agent's output is persisted to `agent_outputs` table with agent name and timestamp
- Uses Gemini 3.1 Pro Preview as the LLM backend

**Agent roles:**
| Agent | Produces |
|-------|----------|
| Product Manager | Product brief, feature breakdown, success criteria |
| Architect | System design, component diagram, tech stack decisions |
| Systems Engineer | Infrastructure plan, deployment strategy, cost estimate |
| AI Specialist | AI feature specs, model choices, data pipeline |
| UX Designer | Information architecture, user flows, component list |
| CISO | Security threats, compliance checklist, mitigations |

---

### F1.6 — Real-time Crew Output Streaming ✅
**As a** product manager
**I want to** watch agent outputs appear live while the crew runs
**So that** I don't have to refresh and can catch issues early

**Acceptance criteria:**
- WebSocket endpoint `/ws/runs/{run_id}` broadcasts agent output events in real time
- Frontend `LiveTeamView` connects on page load and renders updates without polling
- Connection survives reconnect; broadcast only to clients watching that specific run
- Replaces the previous 5-second polling loop

**How it works:** `backend/websocket.py` ConnectionManager singleton keyed by run_id; `crew_runner.py` calls `manager.broadcast(run_id, event)` after each agent completes.

---

### F1.7 — Run History ✅
**As a** product manager
**I want to** see every past run of a project with status and timing
**So that** I can compare outputs over time or re-reference prior analyses

**Acceptance criteria:**
- `GET /api/v1/projects/{id}/runs` returns all runs for a project, newest first
- Each run record includes: id, status, started_at, completed_at, error_message, trigger_source
- Individual run details at `GET /api/v1/runs/{id}` with ownership check

---

### F1.8 — Production Deployment ✅
**As the** product owner
**I want** the app to run on my Hostinger VPS with HTTPS
**So that** I can share it with prospects and use it myself from anywhere

**Acceptance criteria:**
- Dockerized: 3 containers (postgres, fastapi, nginx+react) via `docker-compose.prod.yml`
- HTTPS via Traefik reverse proxy with Let's Encrypt auto-issued cert
- Custom domain: https://product.intakeengine.ai
- PostgreSQL data persists across container restarts (Docker volume)
- Secrets in `.env` file, not committed to git
- Dual-host routing temporarily includes studio.buildflows.cloud for migration safety

**Deployment:** See `project_ai_architect_studio.md` in Claude memory or `docker-compose.prod.yml` on VPS.

---

### F1.9 — API Versioning ✅
**As a** future maintainer
**I want** all new endpoints to live under `/api/v1/`
**So that** breaking changes can ship as `/api/v2/` without disrupting existing clients

**Acceptance criteria:**
- All authenticated endpoints under `/api/v1/`
- Legacy `/projects/*` routes preserved without auth for backward compat (removal planned in Phase 5)

---

### F1.10 — Glassmorphism Dark UI ✅
**As a** user
**I want** a visually polished interface
**So that** the tool feels modern and trustworthy (especially when showing it to prospective consulting clients)

**Acceptance criteria:**
- Dark theme with glass-like card surfaces, subtle blur, cyan/purple accents
- Consistent styling across login, dashboard, project detail, live view
- Responsive on laptop screens (mobile optimization deferred)

---

## Phase 2 — Stitch MCP Integration 📋
*Planned. Headline differentiator — UX agent produces real visual designs, not text.*

### F2.1 — Stitch MCP Adapter 📋
Wire CrewAI's `MCPServerAdapter` to Google's Stitch MCP server (stdio transport) so the UX Designer agent can generate actual UI designs.

### F2.2 — Visual Design Generation 📋
UX Designer agent creates a Stitch project, generates key screens from the PM's feature breakdown + architect's component list, and extracts a design system (fonts, colors, spacing).

### F2.3 — Design Preview in UI 📋
New `DesignPreview` component renders Stitch-generated HTML in a sandboxed iframe with a mobile/desktop toggle and screenshot fallback.

### F2.4 — Design Persistence 📋
New `stitch_designs` table stores stitch_project_id, screen names, HTML URLs, screenshots, theme JSON, device type.

**Acceptance:** Run a crew → UX agent creates a Stitch project → key screens render in the app preview → design system doc exported alongside.

---

## Phase 3 — Artifacts & Export 📋
*Planned. Makes every agent output a first-class, exportable PM deliverable.*

### F3.1 — Structured Artifact Model 📋
New `artifacts` table with typed outputs: PRD, user_story_map, ADR, wireframe, security_report, infra_plan.

### F3.2 — Rewritten Agent Tasks 📋
Each of the 6 agents explicitly produces 1–3 named artifact types (e.g. PM → PRD + User Story Map + Acceptance Criteria).

### F3.3 — PDF Export 📋
Per-artifact and "Export All" (ZIP of PDFs + source markdown) via `weasyprint`.

### F3.4 — Artifact Viewer 📋
Frontend component that renders markdown with export buttons (PDF, MD, clipboard).

---

## Phase 4 — n8n Bidirectional Integration 📋
*Planned. Connects the tool to Chris's n8n instance at buildflows.cloud for workflow automation.*

### F4.1 — Outbound Webhooks 📋
POSTs to configured n8n webhook URL on events: run_started, run_completed, agent_output.

### F4.2 — Inbound Triggers 📋
`POST /api/v1/webhooks/n8n/{project_id}/trigger` (shared-secret auth) lets n8n kick off crew runs from external events (Jira epic created, Google Form submitted, scheduled review).

### F4.3 — Per-Project Webhook Config 📋
`n8n_webhook_configs` table + UI panel for configuring webhook URLs, subscribed events, and trigger paths.

### F4.4 — Tabbed Project Detail UI 📋
`ProjectDetails` becomes tabbed: Requirements | Knowledge Base | Integrations | Run History.

**Use cases:** Slack summaries, Notion page creation from PRDs, scheduled weekly reviews, feeding analytics into agent context.

---

## Phase 5 — Production Hardening 📋
*Planned. Battle-proof the deployment before using it for paid consulting engagements.*

### F5.1 — Rate Limiting 📋
Per-user request limits on expensive endpoints (especially run creation).

### F5.2 — Automated Backups 📋
Daily PostgreSQL dumps to offsite storage.

### F5.3 — Retry Logic 📋
Exponential backoff in `crew_runner` for transient LLM failures.

### F5.4 — Observability 📋
Structured logging, health checks, basic metrics.

### F5.5 — Remove Legacy Routes 📋
Drop unauthenticated `/projects/*` routes; all clients migrated to `/api/v1/`.

---

## Deferred / Backlog 💡

- **OAuth SSO** — Google/GitHub login (currently email+password only)
- **Team accounts** — invite collaborators to a project
- **Template library** — start a project from a pre-filled template (SaaS MVP, mobile app, internal tool)
- **Agent output editing** — PM can edit agent output in-place and regenerate downstream artifacts
- **Usage-based pricing** — if this ever becomes a paid product
- **Mobile-responsive UI** — currently laptop-first
- **Rate-limited public demo mode** — for BTP Consulting landing page lead gen

---

## Architecture at a Glance

```
┌────────────────────────────────────────────────────────┐
│  https://product.intakeengine.ai  (Traefik + LE cert)  │
└──────────────────┬─────────────────────────────────────┘
                   │
       ┌───────────┴────────────┐
       │  frontend (nginx)      │  ← React 19 + Vite build
       │  - serves static SPA   │
       │  - proxies /api → be   │
       │  - proxies /ws → be    │
       └───────────┬────────────┘
                   │
       ┌───────────┴────────────┐
       │  backend (FastAPI)     │  ← Python 3.12
       │  - JWT auth            │
       │  - /api/v1/* endpoints │
       │  - /ws/runs/{id}       │
       │  - CrewAI orchestration│
       └───────────┬────────────┘
                   │
       ┌───────────┴────────────┐
       │  db (PostgreSQL 16)    │  ← Docker volume
       │  users, projects,      │
       │  runs, outputs, etc    │
       └────────────────────────┘

       External:
       - Google Gemini API (LLM)
       - GitHub API (optional codebase ingestion)
       - [Phase 2] Google Stitch MCP (UI generation)
       - [Phase 4] n8n @ buildflows.cloud (webhooks)
```

---

## Ownership & Maintenance

- **Product Owner:** Chris Painter (chris@gobehindtheproduct.com)
- **Repo:** https://github.com/chrispainter/ai-architect-studio
- **Infrastructure:** Hostinger VPS 187.124.236.12 (shared with n8n)
- **Primary URL:** https://product.intakeengine.ai
- **Purpose:** Dual — internal PM tool for Chris + showcase product for BTP Consulting prospects
