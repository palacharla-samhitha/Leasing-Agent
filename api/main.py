# ============================================================================
# api/main.py — FastAPI application entry point
# Run locally:
#   uvicorn api.main:app --reload --port 8000
#   http://localhost:8000/docs       ← Swagger UR:
# ============================================================================

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from api.routers import inquiries,units,workflows,properties,dashboard

app = FastAPI(
    title="MAF Leasing Agent API",
    description="Agentic AI Leasing · MAF Properties · ReKnew × Monetize360",
    version="0.1.0",
)

# ── CORS (allows Streamlit on localhost:8501 to call this API) ────────────────
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:8501", "http://localhost:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ── Routers ───────────────────────────────────────────────────────────────────
app.include_router(inquiries.router, prefix="/inquiries", tags=["Inquiries"])
app.include_router(units.router,     prefix="/units",     tags=["Units"])
app.include_router(workflows.router,  prefix="/workflows",  tags=["Workflows"])
app.include_router(properties.router, prefix="/properties", tags=["Properties"])
# app.include_router(audit.router, prefix="/audit", tags=["Audit"])
app.include_router(dashboard.router, prefix="/dashboard", tags=["Dashboard"])

# Health check
@app.get("/health", tags=["Health"])
def health():
    return {"status": "ok", "service": "MAF Leasing Agent API"}