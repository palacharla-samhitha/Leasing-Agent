# AI Leasing Agent


# Agent flow:

Inquiry intake → Unit matching → HoT draft
↓ [Gate 1: Leasing executive]
Document verification → [Gate 2: LCM validation]
↓
Lease generation → [Gate 3: Final approval]
↓
Tenant delivery + e-sign → EJARI filing

**Final output:** Signed lease + EJARI certificate → handoff to Agent 02 (Tenant Onboarding)

---

## What the Agent Handles

| Step | Agent action |
|------|-------------|
| 1 | Receives inquiry, classifies by type / size / priority |
| 2 | Queries Yardi, shortlists matching units |
| 3 | Auto-generates Heads of Terms (rent, fit-out period, duration) |
| 4 | Requests and checks tenant documents (trade license, VAT cert, Emirates ID, PoA) |
| 5 | Triggers Kofax doc generation, runs consistency check against Yardi |
| 6 | Delivers lease via Partner Connect, collects e-signature, files EJARI |

## What the Agent Does NOT Handle

Negotiation, relationship management, tenant mix strategy, non-standard clauses,
and crisis situations remain with humans. Agents don't close deals — they lift the
formal work. Humans close deals.

---

## Human Gates

Three mandatory approval checkpoints are built into every deal:

| Gate | Owner | Decision |
|------|-------|----------|
| G1 | Leasing executive | Reviews shortlisted units, edits terms, approves or overrides HoT |
| G2 | LCM | Reviews document package, confirms PoA validity, approves |
| G3 | Senior manager | Reviews full lease pack, confirms yield, approves send |

---

## Key Leasing Nuances the Agent Is Aware Of

- **Rent is not one number** — base rent + turnover rent + service charge + marketing levy + deposits, each calculated differently
- **Lease start ≠ rent commencement** — fit-out period (2–4 months) sits between them; incorrect dates break invoicing
- **Tenant entity ≠ brand name** — the legal signatory's authority must be verified, not just the brand's reputation
- **Unit availability has 6 states** — vacant, under refurbishment, expiring soon, reserved informally, signed but unoccupied, held strategically
- **Renewal = potential new negotiation** — RERA rent index governs permissible increases; as complex as an original deal

---

## Tech Stack

- **Agent framework:** Azure AI Foundry (agent hosting) + Azure OpenAI GPT-4o
- **Data:** Databricks Lakehouse — Delta Lake (Bronze/Silver/Gold), Unity Catalog, MLflow tracing
- **Integrations:** Yardi Voyager (unit/lease data), Kofax (doc generation), EJARI portal API
- **Channels:** Partner Connect portal, WhatsApp Business API
- **Monitoring:** MLflow — every agent action traced; alerts on gate timeouts and EJARI failures

---

## Getting Started
```bash
git clone https://github.com/reknew/ai-leasing-agent.git
cd ai-leasing-agent

```

---

## POC vs Production

| Area | POC (now) | Production (Nov 2026) |
|------|-----------|----------------------|
| Data | Dummy units, fictional tenants | Live Yardi data |
| Yardi | Read-only mock | Full read-write API — **biggest technical risk, confirm in discovery workshop** |
| Kofax | Template simulation | Live doc generation |
| EJARI | Simulated filing | Live government API — legally binding |
| Geography | Dubai only | UAE, Oman, Egypt, Bahrain, KSA |
| Auth | Open | Azure AD + Purview + PDPL-compliant access controls |

## Commands to run data

python tools\test_tools.py