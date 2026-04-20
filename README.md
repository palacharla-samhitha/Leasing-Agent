# MAF Properties — AI Leasing Agent
**ReKnew × Monetize360 × MAF Properties · Confidential · April 2026**

Agentic AI system that re-engineers the commercial leasing lifecycle — from tenant inquiry through unit matching, Heads of Terms drafting, document verification, lease generation, and EJARI filing.

---

## Agent Flow

```
Inquiry intake → Unit matching → HoT draft
        ↓ [Gate 1: Leasing Executive]
Document request → Document verification
        ↓ [Gate 2: LCM Validation]
Lease generation → Consistency checks
        ↓ [Gate 3: Senior Manager Approval]
EJARI filing → Deal closed → Handoff to Agent 02
```

**Final output:** Signed lease + EJARI certificate → handoff to Agent 02 (Tenant Onboarding)

---

## What the Agent Handles

| Step | Agent action |
|------|-------------|
| 1 | Receives inquiry, classifies by type / size / priority, scores lead |
| 2 | Queries Yardi, scores and shortlists matching units |
| 3 | Auto-generates Heads of Terms (rent, fit-out period, duration, escalation) |
| 4 | Requests and checks tenant documents (trade license, VAT cert, Emirates ID, PoA) |
| 5 | Generates lease document, runs 7 Kofax consistency checks |
| 6 | Files EJARI registration, generates certificate, closes deal |

## What the Agent Does NOT Handle

Negotiation, relationship management, tenant mix strategy, non-standard clauses,
and crisis situations remain with humans. Agents lift the formal work — humans close deals.

---

## Human Gates

| Gate | Owner | Decision |
|------|-------|----------|
| G1 | Leasing executive | Reviews shortlisted units, edits HoT terms, approves or overrides |
| G2 | LCM | Reviews document package, confirms PoA validity, approves |
| G3 | Senior manager | Reviews full lease pack, confirms yield, approves send |

---

## Tech Stack

### Backend
- **Agent framework:** LangGraph (StateGraph + human interrupt gates)
- **LLM:** Groq (llama-3.1-8b-instant) with per-node fallbacks
- **API:** FastAPI — REST endpoints for all agent operations
- **Database:** PostgreSQL (psycopg2) — Yardi-aligned schema
- **Integrations:** Yardi Voyager (mock), EJARI portal (simulated), Kofax (template)

### Frontend
- **Framework:** React + Vite
- **Styling:** Tailwind CSS
- **Routing:** React Router
- **HTTP:** Axios

### Phase 2 Additions
- Audit trail — every agent action, LLM call, gate decision logged to `audit_events`
- Per-node LLM fallbacks — workflow never crashes on LLM failure
- FastAPI backend — replaces Streamlit as production backend
- React frontend — full leasing UI for admin and customer roles

---

## Project Structure

```
Leasing-Agent/
├── agent/
│   ├── graph.py          # LangGraph graph definition + gate routing
│   ├── nodes.py          # All agent nodes + audit hooks + fallbacks
│   ├── fallbacks.py      # Per-node rule-based fallback functions
│   ├── prompts.py        # System prompts for each node
│   └── state.py          # LeasingAgentState TypedDict
├── api/
│   ├── main.py           # FastAPI app entry point
│   └── routers/
│       ├── inquiries.py  # GET/POST/PATCH/DELETE /inquiries
│       ├── units.py      # GET /units
│       ├── workflows.py  # POST /workflows/start, GET /state, POST /resume
│       ├── properties.py # GET /properties
│       ├── audit.py      # GET /audit/events, /inquiry, /thread
│       └── dashboard.py  # GET /dashboard/summary, /pipeline, /units
├── frontend/
│   └── src/
│       ├── pages/        # Dashboard, Inquiries, WorkflowView, Units,
│       │                 # Properties, Audit, InquiryForm, Login
│       ├── components/   # Sidebar, TopBar
│       ├── context/      # AuthContext (role-based access)
│       └── api/          # Axios client
├── tools/
│   ├── yardi.py          # Unit/lease/inquiry DB access layer
│   ├── scoring.py        # Lead score + match score calculations
│   ├── documents.py      # Document checklist + verification
│   ├── ejari.py          # EJARI registration simulation
│   └── verification.py   # Kofax consistency checks (CC-01 to CC-07)
├── utils/
│   ├── audit.py          # write_audit_event() + convenience wrappers
│   └── pdf_generator.py  # EJARI certificate PDF generation
├── db.py                 # PostgreSQL connection pool
├── app.py                # Streamlit UI (Phase 1 — kept for reference)
├── db_schema_sql.sql     # Phase 1 database schema
├── mock_data_sql.sql     # Seed data (4 properties, 8 units, 4 inquiries)
└── migration_audit_events.sql  # Phase 2 migration — audit_events table
```

---

## Setup

### Prerequisites
- Python 3.11+
- Node.js 18+
- PostgreSQL 14+

### 1. Clone and install Python dependencies
```bash
git clone https://github.com/palacharla-samhitha/Leasing-Agent.git
cd Leasing-Agent
python -m venv venv
source venv/Scripts/activate  # Windows: venv\Scripts\activate
pip install -r requirements.txt
```

### 2. Configure environment
Create a `.env` file in the project root:
```env
GROQ_API_KEY=your_groq_api_key
DB_HOST=localhost
DB_PORT=5432
DB_NAME=leasing_agent
DB_USER=postgres
DB_PASSWORD=your_password
```

### 3. Set up the database
```bash
# Create database
psql -U postgres -c "CREATE DATABASE leasing_agent;"

# Run schema + seed data + Phase 2 migration (in order)
psql -U postgres -d leasing_agent -f db_schema_sql.sql
psql -U postgres -d leasing_agent -f mock_data_sql.sql
psql -U postgres -d leasing_agent -f migration_audit_events.sql
```

### 4. Install frontend dependencies
```bash
cd frontend
npm install
cd ..
```

---

## Running the Application

### Start the FastAPI backend
```bash
# From project root, with venv activated
uvicorn api.main:app --reload --port 8000
```
API docs available at: `http://localhost:8000/docs`

### Start the React frontend
```bash
cd frontend
npm run dev
```
Frontend available at: `http://localhost:5173`

### (Optional) Run the Streamlit UI — Phase 1 reference
```bash
streamlit run app.py
```

---

## Roles

| Role | Access |
|------|--------|
| MAF Admin | Dashboard, Inquiries, Workflow, Units, Properties, Audit Trail |
| Guest / Customer | Properties Explorer, Unit Explorer, Submit Inquiry form |

Login at `http://localhost:5173` — select role via toggle (no auth in POC).

---

## API Endpoints

| Router | Prefix | Key endpoints |
|--------|--------|---------------|
| Inquiries | `/inquiries` | CRUD for all inquiries |
| Units | `/units` | List + filter all units |
| Workflows | `/workflows` | Start, poll state, resume at gates |
| Properties | `/properties` | List + detail with units |
| Audit | `/audit` | Event log, inquiry timeline, thread history |
| Dashboard | `/dashboard` | Summary, pipeline, vacancy by property |
| Health | `/health` | Service status |

---

## Key Leasing Nuances

- **Rent is not one number** — base rent + service charge + marketing levy + turnover rent + deposits
- **Lease start ≠ rent commencement** — fit-out period sits between them; incorrect dates break invoicing
- **Tenant entity ≠ brand name** — legal signatory authority must be verified
- **Unit availability has 6 states** — vacant, expiring soon, reserved informally, signed unoccupied, held strategically
- **EJARI is Dubai-only** — only applicable to Dubai properties (ejari_applicable = TRUE)

---

## POC vs Production

| Area | POC (now) | Production (Nov 2026) |
|------|-----------|----------------------|
| Data | Mock units, fictional tenants | Live Yardi data |
| LLM | Groq Llama (free tier) | Claude Sonnet / GPT-4o with routing |
| Yardi | Read-only mock | Full read-write API |
| EJARI | Simulated filing | Live DLD government API |
| Checkpointer | MemorySaver (in-memory) | PostgresSaver (persistent) |
| Auth | Role toggle (no auth) | Azure AD + PDPL-compliant |
| Geography | 4 UAE malls | 29 malls across 8 countries |
| Hosting | Local | Azure App Service + Azure PostgreSQL |

---

## Running Tests
```bash
python tools/test_tools.py
```