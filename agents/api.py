"""
FastAPI REST API Server for Cxr Multimodal Report Grounder.
"""
from pathlib import Path
from fastapi import FastAPI, HTTPException
from fastapi.responses import RedirectResponse
from fastapi.staticfiles import StaticFiles
from fastapi.responses import PlainTextResponse
from pydantic import BaseModel
from .base import AuditLogger, PHIGuard, SecurityException
from .models import SystemTaskPayload
from .supervisor import SystemSupervisor
from .metrics import GLOBAL_METRICS

supervisor = SystemSupervisor(model_provider="mock")

app = FastAPI(
    title="Cxr Multimodal Report Grounder API",
    description="Enterprise Distributed Component Platform (Clinical & Biomedical AI)",
    version="3.0.0-ENTERPRISE",
)


app.mount("/web", StaticFiles(directory=Path(__file__).resolve().parents[1] / "web", html=True), name="web")


@app.get("/", include_in_schema=False)
def home():
    return RedirectResponse(url="/web/")


class ChatRequest(BaseModel):
    query: str


@app.get("/health")
def health():
    return {"status": "HEALTHY", "service": "cxr-multimodal-report-grounder", "domain": "Clinical & Biomedical AI", "standard": "CAP / CLSI / ISO Standards", "version": "3.0.0-ENTERPRISE"}


@app.get("/metrics", response_class=PlainTextResponse)
def metrics():
    """Prometheus-compatible metrics endpoint."""
    return GLOBAL_METRICS.export_prometheus_text()


@app.post("/api/audit")
def api_audit(payload: SystemTaskPayload):
    try:
        dossier = supervisor.process_task(payload)
    except SecurityException:
        raise HTTPException(status_code=422, detail="Input contains a prohibited identifier.") from None
    return dossier.to_dict()


@app.post("/api/chat")
def api_chat(req: ChatRequest):
    try:
        ans = supervisor.query_supervisory_chat(req.query)
        return {"response": ans}
    except SecurityException:
        raise HTTPException(status_code=422, detail="Input contains a prohibited identifier.") from None


@app.get("/api/audit/logs")
def api_audit_logs():
    return {"audit_trail": AuditLogger.get_trail(), "verified": AuditLogger.verify_integrity()}
