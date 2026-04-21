# ============================================================================
# api/main.py — FastAPI application entry point
# Databricks Apps deployment version
# ============================================================================

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
import os

from api.routers import inquiries, units, workflows, properties, dashboard, audit

app = FastAPI(
    title="MAF Leasing Agent API",
    description="Agentic AI Leasing · MAF Properties · ReKnew × Monetize360",
    version="0.1.0",
)

# ── CORS ─────────────────────────────────────────────────────────────────────
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ── API Routers ───────────────────────────────────────────────────────────────
app.include_router(inquiries.router,  prefix="/inquiries",  tags=["Inquiries"])
app.include_router(units.router,      prefix="/units",      tags=["Units"])
app.include_router(workflows.router,  prefix="/workflows",  tags=["Workflows"])
app.include_router(properties.router, prefix="/properties", tags=["Properties"])
app.include_router(audit.router,      prefix="/audit",      tags=["Audit"])
app.include_router(dashboard.router,  prefix="/dashboard",  tags=["Dashboard"])

# ── Health check ──────────────────────────────────────────────────────────────
@app.get("/health", tags=["Health"])
def health():
    return {"status": "ok", "service": "MAF Leasing Agent API"}

# ── Serve React frontend (must be LAST — catch-all route) ────────────────────
frontend_dist = os.path.join(os.path.dirname(__file__), "..", "frontend", "dist")

if os.path.exists(frontend_dist):
    app.mount("/assets", StaticFiles(directory=os.path.join(frontend_dist, "assets")), name="assets")

@app.get("/{full_path:path}", include_in_schema=False)
async def serve_react(full_path: str):
    index = os.path.join(frontend_dist, "index.html")
    if os.path.exists(index):
        return FileResponse(index)
    return {"error": "Frontend not built. Run: cd frontend && npm run build"}